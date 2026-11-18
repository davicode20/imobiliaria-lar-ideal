from decimal import Decimal, InvalidOperation

import pymysql
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import usuario_logado
from app.database import get_cursor
from app.templating import flash, templates

router = APIRouter(prefix="/imoveis", tags=["Imóveis"], dependencies=[Depends(usuario_logado)])

TIPOS = ["CASA", "APARTAMENTO", "TERRENO", "SALA_COMERCIAL"]
FINALIDADES = ["VENDA", "ALUGUEL"]
STATUS = ["DISPONIVEL", "ALUGADO", "VENDIDO"]


def para_decimal(texto: str):
    """Aceita '1800', '1800.50', '1.800,50' ou '1800,50'."""
    texto = (texto or "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def buscar_proprietarios(proprietario_atual=None):
    """Clientes que podem ser donos de imóvel (+ o dono atual, caso o tipo dele tenha mudado)."""
    with get_cursor() as cur:
        cur.execute(
            """SELECT id, nome FROM clientes
               WHERE tipo IN ('PROPRIETARIO', 'AMBOS') OR id = %s
               ORDER BY nome""",
            (proprietario_atual or 0,),
        )
        return cur.fetchall()


def render_form(request: Request, imovel: dict, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "imoveis/form.html",
        {
            "imovel": imovel,
            "proprietarios": buscar_proprietarios(imovel.get("proprietario_id")),
            "tipos": TIPOS,
            "finalidades": FINALIDADES,
            "status_lista": STATUS,
        },
        status_code=status_code,
    )


def montar_dados(proprietario_id, titulo, tipo, finalidade, endereco, bairro, cidade, area_m2, quartos, valor, status):
    return {
        "proprietario_id": proprietario_id,
        "titulo": titulo.strip(),
        "tipo": tipo,
        "finalidade": finalidade,
        "endereco": endereco.strip(),
        "bairro": bairro.strip(),
        "cidade": cidade.strip() or "Palmas",
        "area_m2": para_decimal(area_m2),
        "quartos": quartos,
        "valor": para_decimal(valor),
        "status": status,
    }


def validar(request: Request, d: dict) -> bool:
    erros = []
    if d["tipo"] not in TIPOS:
        erros.append("Tipo de imóvel inválido.")
    if d["finalidade"] not in FINALIDADES:
        erros.append("Finalidade inválida.")
    if d["status"] not in STATUS:
        erros.append("Status inválido.")
    if d["area_m2"] is None or d["area_m2"] <= 0:
        erros.append("Informe uma área válida (maior que zero).")
    if d["valor"] is None or d["valor"] <= 0:
        erros.append("Informe um valor válido (maior que zero).")
    if d["quartos"] < 0 or d["quartos"] > 255:
        erros.append("Quantidade de quartos inválida.")
    for e in erros:
        flash(request, e, "danger")
    return not erros


# ---------- LISTAR / PESQUISAR (SELECT + JOIN) ----------
@router.get("")
def listar(request: Request, q: str = "", finalidade: str = "", status: str = "", tipo: str = ""):
    sql = """
        SELECT i.id, i.titulo, i.tipo, i.finalidade, i.bairro, i.cidade,
               i.area_m2, i.quartos, i.valor, i.status,
               c.nome AS proprietario
        FROM imoveis i
        INNER JOIN clientes c ON c.id = i.proprietario_id
        WHERE 1 = 1
    """
    params = []
    if q.strip():
        sql += " AND (i.titulo LIKE %s OR i.bairro LIKE %s OR c.nome LIKE %s)"
        termo = f"%{q.strip()}%"
        params += [termo, termo, termo]
    if finalidade in FINALIDADES:
        sql += " AND i.finalidade = %s"
        params.append(finalidade)
    if status in STATUS:
        sql += " AND i.status = %s"
        params.append(status)
    if tipo in TIPOS:
        sql += " AND i.tipo = %s"
        params.append(tipo)
    sql += " ORDER BY i.titulo"

    with get_cursor() as cur:
        cur.execute(sql, params)
        imoveis = cur.fetchall()

    filtros = {"q": q, "finalidade": finalidade, "status": status, "tipo": tipo}
    return templates.TemplateResponse(
        request,
        "imoveis/lista.html",
        {
            "imoveis": imoveis,
            "filtros": filtros,
            "filtrando": any(filtros.values()),
            "tipos": TIPOS,
            "finalidades": FINALIDADES,
            "status_lista": STATUS,
        },
    )


# ---------- CADASTRAR (INSERT) ----------
@router.get("/novo")
def novo(request: Request):
    return render_form(request, {"cidade": "Palmas", "status": "DISPONIVEL", "quartos": 0})


@router.post("/novo")
def criar(
    request: Request,
    proprietario_id: int = Form(...),
    titulo: str = Form(...),
    tipo: str = Form(...),
    finalidade: str = Form(...),
    endereco: str = Form(...),
    bairro: str = Form(...),
    cidade: str = Form("Palmas"),
    area_m2: str = Form(...),
    quartos: int = Form(0),
    valor: str = Form(...),
    status: str = Form("DISPONIVEL"),
):
    d = montar_dados(proprietario_id, titulo, tipo, finalidade, endereco, bairro, cidade, area_m2, quartos, valor, status)
    if not validar(request, d):
        return render_form(request, d, 400)

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO imoveis
                   (proprietario_id, titulo, tipo, finalidade, endereco, bairro, cidade, area_m2, quartos, valor, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (d["proprietario_id"], d["titulo"], d["tipo"], d["finalidade"], d["endereco"], d["bairro"],
                 d["cidade"], d["area_m2"], d["quartos"], d["valor"], d["status"]),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Proprietário inválido.", "danger")
        return render_form(request, d, 400)

    flash(request, f"Imóvel \"{d['titulo']}\" cadastrado com sucesso!")
    return RedirectResponse("/imoveis", status_code=303)


# ---------- EDITAR (UPDATE) ----------
@router.get("/{imovel_id}/editar")
def editar(request: Request, imovel_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM imoveis WHERE id = %s", (imovel_id,))
        imovel = cur.fetchone()

    if not imovel:
        flash(request, "Imóvel não encontrado.", "warning")
        return RedirectResponse("/imoveis", status_code=303)

    return render_form(request, imovel)


@router.post("/{imovel_id}/editar")
def atualizar(
    request: Request,
    imovel_id: int,
    proprietario_id: int = Form(...),
    titulo: str = Form(...),
    tipo: str = Form(...),
    finalidade: str = Form(...),
    endereco: str = Form(...),
    bairro: str = Form(...),
    cidade: str = Form("Palmas"),
    area_m2: str = Form(...),
    quartos: int = Form(0),
    valor: str = Form(...),
    status: str = Form("DISPONIVEL"),
):
    d = montar_dados(proprietario_id, titulo, tipo, finalidade, endereco, bairro, cidade, area_m2, quartos, valor, status)
    d["id"] = imovel_id
    if not validar(request, d):
        return render_form(request, d, 400)

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """UPDATE imoveis
                   SET proprietario_id = %s, titulo = %s, tipo = %s, finalidade = %s, endereco = %s,
                       bairro = %s, cidade = %s, area_m2 = %s, quartos = %s, valor = %s, status = %s
                   WHERE id = %s""",
                (d["proprietario_id"], d["titulo"], d["tipo"], d["finalidade"], d["endereco"], d["bairro"],
                 d["cidade"], d["area_m2"], d["quartos"], d["valor"], d["status"], imovel_id),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Proprietário inválido.", "danger")
        return render_form(request, d, 400)

    flash(request, "Imóvel atualizado com sucesso!")
    return RedirectResponse("/imoveis", status_code=303)


# ---------- EXCLUIR (DELETE) ----------
@router.post("/{imovel_id}/excluir")
def excluir(request: Request, imovel_id: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM imoveis WHERE id = %s", (imovel_id,))
        flash(request, "Imóvel excluído com sucesso.")
    except pymysql.err.IntegrityError:
        flash(request, "Não é possível excluir: este imóvel possui contratos vinculados (chave estrangeira).", "danger")

    return RedirectResponse("/imoveis", status_code=303)
