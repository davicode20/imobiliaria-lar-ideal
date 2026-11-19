from datetime import date

import pymysql
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import usuario_logado
from app.database import get_cursor
from app.routers.imoveis import para_decimal
from app.templating import flash, templates

router = APIRouter(prefix="/contratos", tags=["Contratos"], dependencies=[Depends(usuario_logado)])

TIPOS = ["LOCACAO", "VENDA"]
STATUS = ["ATIVO", "ENCERRADO", "CANCELADO"]

# Cada tipo de contrato só combina com uma finalidade de imóvel
FINALIDADE_DO_TIPO = {"LOCACAO": "ALUGUEL", "VENDA": "VENDA"}


def status_do_imovel(tipo: str, status: str) -> str:
    """Regra de negócio: qual deve ser o status do imóvel conforme o contrato.

    - Locação ativa  -> ALUGADO        - Venda ativa ou concluída -> VENDIDO
    - Locação encerrada ou qualquer contrato cancelado -> volta a DISPONIVEL
    """
    if status == "CANCELADO":
        return "DISPONIVEL"
    if tipo == "VENDA":
        return "VENDIDO"
    return "ALUGADO" if status == "ATIVO" else "DISPONIVEL"


def para_data(texto: str):
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def buscar_opcoes(contrato: dict):
    with get_cursor() as cur:
        # Imóveis disponíveis + o imóvel do próprio contrato (na edição)
        cur.execute(
            """SELECT i.id, i.titulo, i.finalidade, i.valor, i.status, c.nome AS proprietario
               FROM imoveis i
               INNER JOIN clientes c ON c.id = i.proprietario_id
               WHERE i.status = 'DISPONIVEL' OR i.id = %s
               ORDER BY i.titulo""",
            (contrato.get("imovel_id") or 0,),
        )
        imoveis = cur.fetchall()
        cur.execute(
            """SELECT id, nome, tipo FROM clientes
               WHERE tipo IN ('INTERESSADO', 'AMBOS') OR id = %s
               ORDER BY nome""",
            (contrato.get("cliente_id") or 0,),
        )
        clientes = cur.fetchall()
    return imoveis, clientes


def render_form(request: Request, contrato: dict, status_code: int = 200):
    imoveis, clientes = buscar_opcoes(contrato)
    return templates.TemplateResponse(
        request,
        "contratos/form.html",
        {"contrato": contrato, "imoveis": imoveis, "clientes": clientes, "tipos": TIPOS, "status_lista": STATUS},
        status_code=status_code,
    )


def montar_dados(imovel_id, cliente_id, tipo, data_inicio, data_fim, valor, status):
    return {
        "imovel_id": imovel_id,
        "cliente_id": cliente_id,
        "tipo": tipo,
        "data_inicio": para_data(data_inicio),
        # Venda não tem data de término
        "data_fim": None if tipo == "VENDA" else para_data(data_fim),
        "valor": para_decimal(valor),
        "status": status,
    }


def validar(request: Request, cur, d: dict, contrato_id: int = 0) -> bool:
    erros = []
    if d["tipo"] not in TIPOS:
        erros.append("Tipo de contrato inválido.")
    if d["status"] not in STATUS:
        erros.append("Status inválido.")
    if d["data_inicio"] is None:
        erros.append("Informe a data de início.")
    if d["tipo"] == "LOCACAO" and d["data_fim"] is None:
        erros.append("Contrato de locação precisa de data de término.")
    if d["data_inicio"] and d["data_fim"] and d["data_fim"] < d["data_inicio"]:
        erros.append("A data de término não pode ser anterior à data de início.")
    if d["valor"] is None or d["valor"] <= 0:
        erros.append("Informe um valor válido (maior que zero).")

    cur.execute("SELECT id, titulo, finalidade, proprietario_id FROM imoveis WHERE id = %s", (d["imovel_id"],))
    imovel = cur.fetchone()
    if not imovel:
        erros.append("Imóvel não encontrado.")
    else:
        if FINALIDADE_DO_TIPO.get(d["tipo"]) != imovel["finalidade"]:
            erros.append(
                f"O imóvel \"{imovel['titulo']}\" é para {imovel['finalidade']}; "
                f"não combina com um contrato de {d['tipo']}."
            )
        if imovel["proprietario_id"] == d["cliente_id"]:
            erros.append("O cliente do contrato não pode ser o próprio proprietário do imóvel.")

        # Não pode haver dois contratos "ocupando" o mesmo imóvel
        if d["status"] != "CANCELADO":
            cur.execute(
                """SELECT COUNT(*) AS n FROM contratos
                   WHERE imovel_id = %s AND id <> %s
                     AND (status = 'ATIVO' OR (tipo = 'VENDA' AND status = 'ENCERRADO'))""",
                (d["imovel_id"], contrato_id),
            )
            if cur.fetchone()["n"]:
                erros.append("Este imóvel já possui um contrato ativo ou já foi vendido.")

    for e in erros:
        flash(request, e, "danger")
    return not erros


# ---------- LISTAR / PESQUISAR (SELECT + JOIN de 4 tabelas) ----------
@router.get("")
def listar(request: Request, q: str = "", tipo: str = "", status: str = ""):
    sql = """
        SELECT c.id, c.tipo, c.data_inicio, c.data_fim, c.valor, c.status,
               i.titulo  AS imovel,
               prop.nome AS proprietario,
               cli.nome  AS cliente
        FROM contratos c
        INNER JOIN imoveis  i    ON i.id    = c.imovel_id
        INNER JOIN clientes prop ON prop.id = i.proprietario_id
        INNER JOIN clientes cli  ON cli.id  = c.cliente_id
        WHERE 1 = 1
    """
    params = []
    if q.strip():
        sql += " AND (i.titulo LIKE %s OR prop.nome LIKE %s OR cli.nome LIKE %s)"
        termo = f"%{q.strip()}%"
        params += [termo, termo, termo]
    if tipo in TIPOS:
        sql += " AND c.tipo = %s"
        params.append(tipo)
    if status in STATUS:
        sql += " AND c.status = %s"
        params.append(status)
    sql += " ORDER BY c.data_inicio DESC"

    with get_cursor() as cur:
        cur.execute(sql, params)
        contratos = cur.fetchall()

    filtros = {"q": q, "tipo": tipo, "status": status}
    return templates.TemplateResponse(
        request,
        "contratos/lista.html",
        {"contratos": contratos, "filtros": filtros, "filtrando": any(filtros.values()),
         "tipos": TIPOS, "status_lista": STATUS},
    )


# ---------- CADASTRAR (INSERT + UPDATE do imóvel na mesma transação) ----------
@router.get("/novo")
def novo(request: Request, imovel_id: int = 0):
    contrato = {"status": "ATIVO", "tipo": "LOCACAO", "data_inicio": date.today()}
    if imovel_id:
        # Veio do botão "Criar contrato" na lista de imóveis: já preenche tipo e valor
        with get_cursor() as cur:
            cur.execute("SELECT id, finalidade, valor FROM imoveis WHERE id = %s AND status = 'DISPONIVEL'", (imovel_id,))
            imovel = cur.fetchone()
        if imovel:
            contrato.update(imovel_id=imovel["id"], valor=imovel["valor"],
                            tipo="VENDA" if imovel["finalidade"] == "VENDA" else "LOCACAO")
    return render_form(request, contrato)


@router.post("/novo")
def criar(
    request: Request,
    imovel_id: int = Form(...),
    cliente_id: int = Form(...),
    tipo: str = Form(...),
    data_inicio: str = Form(...),
    data_fim: str = Form(""),
    valor: str = Form(...),
    status: str = Form("ATIVO"),
):
    d = montar_dados(imovel_id, cliente_id, tipo, data_inicio, data_fim, valor, status)

    try:
        with get_cursor(commit=True) as cur:
            if not validar(request, cur, d):
                return render_form(request, d, 400)
            cur.execute(
                """INSERT INTO contratos (imovel_id, cliente_id, tipo, data_inicio, data_fim, valor, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (d["imovel_id"], d["cliente_id"], d["tipo"], d["data_inicio"], d["data_fim"], d["valor"], d["status"]),
            )
            cur.execute(
                "UPDATE imoveis SET status = %s WHERE id = %s",
                (status_do_imovel(d["tipo"], d["status"]), d["imovel_id"]),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Imóvel ou cliente inválido.", "danger")
        return render_form(request, d, 400)

    flash(request, "Contrato cadastrado com sucesso! O status do imóvel foi atualizado.")
    return RedirectResponse("/contratos", status_code=303)


# ---------- EDITAR (UPDATE) ----------
@router.get("/{contrato_id}/editar")
def editar(request: Request, contrato_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM contratos WHERE id = %s", (contrato_id,))
        contrato = cur.fetchone()

    if not contrato:
        flash(request, "Contrato não encontrado.", "warning")
        return RedirectResponse("/contratos", status_code=303)

    return render_form(request, contrato)


@router.post("/{contrato_id}/editar")
def atualizar(
    request: Request,
    contrato_id: int,
    imovel_id: int = Form(...),
    cliente_id: int = Form(...),
    tipo: str = Form(...),
    data_inicio: str = Form(...),
    data_fim: str = Form(""),
    valor: str = Form(...),
    status: str = Form("ATIVO"),
):
    d = montar_dados(imovel_id, cliente_id, tipo, data_inicio, data_fim, valor, status)
    d["id"] = contrato_id

    try:
        with get_cursor(commit=True) as cur:
            cur.execute("SELECT imovel_id FROM contratos WHERE id = %s", (contrato_id,))
            atual = cur.fetchone()
            if not atual:
                flash(request, "Contrato não encontrado.", "warning")
                return RedirectResponse("/contratos", status_code=303)

            if not validar(request, cur, d, contrato_id):
                return render_form(request, d, 400)

            cur.execute(
                """UPDATE contratos
                   SET imovel_id = %s, cliente_id = %s, tipo = %s, data_inicio = %s,
                       data_fim = %s, valor = %s, status = %s
                   WHERE id = %s""",
                (d["imovel_id"], d["cliente_id"], d["tipo"], d["data_inicio"], d["data_fim"],
                 d["valor"], d["status"], contrato_id),
            )
            # Se trocou de imóvel, o antigo fica livre de novo
            if atual["imovel_id"] != d["imovel_id"]:
                cur.execute("UPDATE imoveis SET status = 'DISPONIVEL' WHERE id = %s", (atual["imovel_id"],))
            cur.execute(
                "UPDATE imoveis SET status = %s WHERE id = %s",
                (status_do_imovel(d["tipo"], d["status"]), d["imovel_id"]),
            )
    except pymysql.err.IntegrityError:
        flash(request, "Imóvel ou cliente inválido.", "danger")
        return render_form(request, d, 400)

    flash(request, "Contrato atualizado com sucesso! O status do imóvel foi sincronizado.")
    return RedirectResponse("/contratos", status_code=303)


# ---------- EXCLUIR (DELETE) ----------
@router.post("/{contrato_id}/excluir")
def excluir(request: Request, contrato_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT imovel_id, tipo, status FROM contratos WHERE id = %s", (contrato_id,))
        contrato = cur.fetchone()
        if not contrato:
            flash(request, "Contrato não encontrado.", "warning")
            return RedirectResponse("/contratos", status_code=303)

        cur.execute("DELETE FROM contratos WHERE id = %s", (contrato_id,))
        # Contrato que "ocupava" o imóvel (Alugado/Vendido) apagado -> imóvel volta a ficar disponível
        if status_do_imovel(contrato["tipo"], contrato["status"]) != "DISPONIVEL":
            cur.execute("UPDATE imoveis SET status = 'DISPONIVEL' WHERE id = %s", (contrato["imovel_id"],))

    flash(request, "Contrato excluído com sucesso.")
    return RedirectResponse("/contratos", status_code=303)
