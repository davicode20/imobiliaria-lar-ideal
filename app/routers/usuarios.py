import pymysql
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import hash_senha, usuario_logado
from app.database import get_cursor
from app.templating import flash, templates

router = APIRouter(prefix="/usuarios", tags=["Usuários"], dependencies=[Depends(usuario_logado)])

SENHA_MINIMA = 6


def render_form(request: Request, registro: dict, status_code: int = 200):
    return templates.TemplateResponse(request, "usuarios/form.html", {"registro": registro}, status_code=status_code)


def validar_senha(request: Request, senha: str, confirmar: str) -> bool:
    if len(senha) < SENHA_MINIMA:
        flash(request, f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres.", "danger")
        return False
    if senha != confirmar:
        flash(request, "A confirmação não confere com a senha.", "danger")
        return False
    return True


# ---------- LISTAR / PESQUISAR (SELECT) ----------
@router.get("")
def listar(request: Request, q: str = ""):
    sql = "SELECT id, nome, usuario, criado_em FROM usuarios"
    params = None
    if q.strip():
        sql += " WHERE nome LIKE %s OR usuario LIKE %s"
        params = (f"%{q.strip()}%", f"%{q.strip()}%")
    sql += " ORDER BY nome"

    with get_cursor() as cur:
        cur.execute(sql, params)
        usuarios = cur.fetchall()

    return templates.TemplateResponse(request, "usuarios/lista.html", {"usuarios": usuarios, "q": q})


# ---------- CADASTRAR (INSERT) — senha gravada como hash SHA-256 ----------
@router.get("/novo")
def novo(request: Request):
    return render_form(request, {})


@router.post("/novo")
def criar(
    request: Request,
    nome: str = Form(...),
    usuario: str = Form(...),
    senha: str = Form(...),
    confirmar: str = Form(...),
):
    dados = {"nome": nome.strip(), "usuario": usuario.strip().lower()}
    if not validar_senha(request, senha, confirmar):
        return render_form(request, dados, 400)

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO usuarios (nome, usuario, senha_hash) VALUES (%s, %s, %s)",
                (dados["nome"], dados["usuario"], hash_senha(senha)),
            )
    except pymysql.err.IntegrityError:
        flash(request, f"O login \"{dados['usuario']}\" já está em uso.", "danger")
        return render_form(request, dados, 400)

    flash(request, f"Usuário {dados['usuario']} cadastrado com sucesso!")
    return RedirectResponse("/usuarios", status_code=303)


# ---------- EDITAR (UPDATE) — senha só muda se for preenchida ----------
@router.get("/{usuario_id}/editar")
def editar(request: Request, usuario_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT id, nome, usuario FROM usuarios WHERE id = %s", (usuario_id,))
        registro = cur.fetchone()

    if not registro:
        flash(request, "Usuário não encontrado.", "warning")
        return RedirectResponse("/usuarios", status_code=303)

    return render_form(request, registro)


@router.post("/{usuario_id}/editar")
def atualizar(
    request: Request,
    usuario_id: int,
    nome: str = Form(...),
    usuario: str = Form(...),
    senha: str = Form(""),
    confirmar: str = Form(""),
):
    dados = {"id": usuario_id, "nome": nome.strip(), "usuario": usuario.strip().lower()}
    if senha and not validar_senha(request, senha, confirmar):
        return render_form(request, dados, 400)

    try:
        with get_cursor(commit=True) as cur:
            if senha:
                cur.execute(
                    "UPDATE usuarios SET nome = %s, usuario = %s, senha_hash = %s WHERE id = %s",
                    (dados["nome"], dados["usuario"], hash_senha(senha), usuario_id),
                )
            else:
                cur.execute(
                    "UPDATE usuarios SET nome = %s, usuario = %s WHERE id = %s",
                    (dados["nome"], dados["usuario"], usuario_id),
                )
    except pymysql.err.IntegrityError:
        flash(request, f"O login \"{dados['usuario']}\" já está em uso.", "danger")
        return render_form(request, dados, 400)

    # Se o usuário editou a si mesmo, atualiza o nome mostrado na navbar
    logado = request.session.get("usuario", {})
    if logado.get("id") == usuario_id:
        request.session["usuario"] = {**logado, "nome": dados["nome"], "usuario": dados["usuario"]}

    flash(request, "Usuário atualizado com sucesso!")
    return RedirectResponse("/usuarios", status_code=303)


# ---------- EXCLUIR (DELETE) ----------
@router.post("/{usuario_id}/excluir")
def excluir(request: Request, usuario_id: int, logado: dict = Depends(usuario_logado)):
    if logado["id"] == usuario_id:
        flash(request, "Você não pode excluir o próprio usuário enquanto está logado.", "warning")
        return RedirectResponse("/usuarios", status_code=303)

    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    flash(request, "Usuário excluído com sucesso.")
    return RedirectResponse("/usuarios", status_code=303)
