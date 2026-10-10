from collections.abc import Mapping

from pydantic import BaseModel


def definidos[M: BaseModel](modelo: type[M], valores: Mapping[str, object]) -> M:
    # Só o que o ambiente DEFINIU é repassado: campo ausente deixa o default do model valer.
    # Passar `None` adiante sobrescreveria o padrão com vazio e obrigaria cada valor a existir
    # aqui também — duas cópias livres para divergir.
    return modelo(**{chave: valor for chave, valor in valores.items() if valor is not None})
