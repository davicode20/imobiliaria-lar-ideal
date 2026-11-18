import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NaoAutenticado, hash_senha, usuario_logado
from app.database import get_cursor
from app.routers import clientes, contratos, imoveis, usuarios
from app.templating import flash, templates

load_dotenv()

app = FastAPI(title="Imobiliária Lar Ideal")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "troque-esta-chave"))
app.include_router(clientes.router)
app.include_router(imoveis.router)
app.include_router(contratos.router)
app.include_router(usuarios.router)


@app.exception_handler(NaoAutenticado)
async def redirecionar_para_login(request: Request, exc: NaoAutenticado):
    return RedirectResponse("/login", status_code=303)


@app.get("/login")
def login_form(request: Request):
    if request.session.get("usuario"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nome, usuario FROM usuarios WHERE usuario = %s AND senha_hash = %s",
            (usuario.strip(), hash_senha(senha)),
        )
        user = cur.fetchone()

    if not user:
        flash(request, "Usuário ou senha inválidos.", "danger")
        return templates.TemplateResponse(
            request, "login.html", {"usuario_digitado": usuario}, status_code=401
        )

    request.session["usuario"] = user
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/")
def painel(request: Request, usuario: dict = Depends(usuario_logado)):
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM clientes)                              AS total_clientes,
                (SELECT COUNT(*) FROM imoveis)                               AS total_imoveis,
                (SELECT COUNT(*) FROM imoveis WHERE status = 'DISPONIVEL')   AS imoveis_disponiveis,
                (SELECT COUNT(*) FROM contratos WHERE status = 'ATIVO')      AS contratos_ativos,
                (SELECT COALESCE(SUM(valor), 0) FROM contratos
                  WHERE tipo = 'LOCACAO' AND status = 'ATIVO')               AS receita_aluguel
        """)
        resumo = cur.fetchone()

        cur.execute("""
            SELECT c.id, c.tipo, c.valor, c.data_inicio, c.status,
                   i.titulo  AS imovel,
                   prop.nome AS proprietario,
                   cli.nome  AS cliente
            FROM contratos c
            INNER JOIN imoveis  i    ON i.id    = c.imovel_id
            INNER JOIN clientes prop ON prop.id = i.proprietario_id
            INNER JOIN clientes cli  ON cli.id  = c.cliente_id
            ORDER BY c.data_inicio DESC
            LIMIT 5
        """)
        ultimos_contratos = cur.fetchall()

        # GROUP BY: quantos imóveis existem em cada status
        cur.execute("""
            SELECT status, COUNT(*) AS total
            FROM imoveis
            GROUP BY status
        """)
        por_status = {linha["status"]: linha["total"] for linha in cur.fetchall()}

        cur.execute("""
            SELECT i.id, i.titulo, i.finalidade, i.bairro, i.valor, c.nome AS proprietario
            FROM imoveis i
            INNER JOIN clientes c ON c.id = i.proprietario_id
            WHERE i.status = 'DISPONIVEL'
            ORDER BY i.valor
        """)
        disponiveis = cur.fetchall()

    return templates.TemplateResponse(
        request,
        "index.html",
        {"resumo": resumo, "ultimos_contratos": ultimos_contratos, "por_status": por_status, "disponiveis": disponiveis},
    )
