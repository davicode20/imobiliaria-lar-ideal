from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def flash(request: Request, mensagem: str, tipo: str = "success") -> None:
    request.session.setdefault("flash", []).append({"mensagem": mensagem, "tipo": tipo})


def moeda(valor) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def data_br(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "—"


def cpf_formatado(cpf: str) -> str:
    if not cpf or len(cpf) != 11:
        return cpf or ""
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


ROTULOS = {
    "PROPRIETARIO": "Proprietário", "INTERESSADO": "Interessado", "AMBOS": "Ambos",
    "CASA": "Casa", "APARTAMENTO": "Apartamento", "TERRENO": "Terreno", "SALA_COMERCIAL": "Sala comercial",
    "VENDA": "Venda", "ALUGUEL": "Aluguel", "LOCACAO": "Locação",
    "DISPONIVEL": "Disponível", "ALUGADO": "Alugado", "VENDIDO": "Vendido",
    "ATIVO": "Ativo", "ENCERRADO": "Encerrado", "CANCELADO": "Cancelado",
}

CORES = {
    "DISPONIVEL": "success", "ALUGADO": "warning", "VENDIDO": "secondary",
    "ATIVO": "success", "ENCERRADO": "secondary", "CANCELADO": "danger",
    "PROPRIETARIO": "primary", "INTERESSADO": "info", "AMBOS": "dark",
}


def rotulo(valor) -> str:
    """Converte o valor do ENUM do banco em texto amigável (SALA_COMERCIAL -> Sala comercial)."""
    return ROTULOS.get(valor, valor or "")


def cor(valor) -> str:
    """Cor do badge do Bootstrap para cada status/tipo."""
    return CORES.get(valor, "light")


templates.env.filters["moeda"] = moeda
templates.env.filters["rotulo"] = rotulo
templates.env.filters["cor"] = cor
templates.env.filters["data_br"] = data_br
templates.env.filters["cpf"] = cpf_formatado
