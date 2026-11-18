import pymysql
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import usuario_logado
from app.database import get_cursor
from app.templating import flash, templates

router = APIRouter(prefix="/clientes", tags=["Clientes"], dependencies=[Depends(usuario_logado)])

TIPOS = ["PROPRIETARIO", "INTERESSADO", "AMBOS"]


def so_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def render_form(request: Request, cliente: dict, status_code: int = 200):
    return templates.TemplateResponse(
        request, "clientes/form.html", {"cliente": cliente, "tipos": TIPOS}, status_code=status_code
    )


def validar(request: Request, dados: dict) -> bool:
    if len(dados["cpf"]) != 11:
        flash(request, "O CPF deve ter 11 dígitos.", "danger")
        return False
    if dados["tipo"] not in TIPOS:
        flash(request, "Tipo de cliente inválido.", "danger")
        return False
    return True


# ---------- LISTAR / PESQUISAR (SELECT) ----------
@router.get("")
def listar(request: Request, q: str = ""):
    sql = "SELECT id, nome, cpf, telefone, email, tipo FROM clientes"
    params = None
    if q.strip():
        sql += " WHERE nome LIKE %s OR cpf LIKE %s"
        termo_cpf = so_digitos(q) or q.strip()
        params = (f"%{q.strip()}%", f"%{termo_cpf}%")
    sql += " ORDER BY nome"

    with get_cursor() as cur:
        cur.execute(sql, params)
        clientes = cur.fetchall()

    return templates.TemplateResponse(request, "clientes/lista.html", {"clientes": clientes, "q": q})


# ---------- CADASTRAR (INSERT) ----------
@router.get("/novo")
def novo(request: Request):
    return render_form(request, {})


@router.post("/novo")
def criar(
    request: Request,
    nome: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(...),
    email: str = Form(""),
    tipo: str = Form(...),
):
    dados = {
        "nome": nome.strip(),
        "cpf": so_digitos(cpf),
        "telefone": telefone.strip(),
        "email": email.strip() or None,
        "tipo": tipo,
    }
    if not validar(request, dados):
        return render_form(request, dados, 400)

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO clientes (nome, cpf, telefone, email, tipo) VALUES (%s, %s, %s, %s, %s)",
                (dados["nome"], dados["cpf"], dados["telefone"], dados["email"], dados["tipo"]),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Já existe um cliente cadastrado com esse CPF.", "danger")
        return render_form(request, dados, 400)

    flash(request, f"Cliente {dados['nome']} cadastrado com sucesso!")
    return RedirectResponse("/clientes", status_code=303)


# ---------- EDITAR (UPDATE) ----------
@router.get("/{cliente_id}/editar")
def editar(request: Request, cliente_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT id, nome, cpf, telefone, email, tipo FROM clientes WHERE id = %s", (cliente_id,))
        cliente = cur.fetchone()

    if not cliente:
        flash(request, "Cliente não encontrado.", "warning")
        return RedirectResponse("/clientes", status_code=303)

    return render_form(request, cliente)


@router.post("/{cliente_id}/editar")
def atualizar(
    request: Request,
    cliente_id: int,
    nome: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(...),
    email: str = Form(""),
    tipo: str = Form(...),
):
    dados = {
        "id": cliente_id,
        "nome": nome.strip(),
        "cpf": so_digitos(cpf),
        "telefone": telefone.strip(),
        "email": email.strip() or None,
        "tipo": tipo,
    }
    if not validar(request, dados):
        return render_form(request, dados, 400)

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """UPDATE clientes
                   SET nome = %s, cpf = %s, telefone = %s, email = %s, tipo = %s
                   WHERE id = %s""",
                (dados["nome"], dados["cpf"], dados["telefone"], dados["email"], dados["tipo"], cliente_id),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Já existe outro cliente com esse CPF.", "danger")
        return render_form(request, dados, 400)

    flash(request, "Cliente atualizado com sucesso!")
    return RedirectResponse("/clientes", status_code=303)


# ---------- EXCLUIR (DELETE) ----------
@router.post("/{cliente_id}/excluir")
def excluir(request: Request, cliente_id: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        flash(request, "Cliente excluído com sucesso.")
    except pymysql.err.IntegrityError:
        flash(request, "Não é possível excluir: este cliente possui imóveis ou contratos vinculados.", "danger")

    return RedirectResponse("/clientes", status_code=303)
