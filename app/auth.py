import hashlib

from fastapi import Request


class NaoAutenticado(Exception):
    pass


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def usuario_logado(request: Request) -> dict:
    usuario = request.session.get("usuario")
    if not usuario:
        raise NaoAutenticado()
    return usuario
