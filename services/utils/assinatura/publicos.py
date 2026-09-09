from typing import Any


def extrair_publicos(envelope: dict[str, Any]) -> dict[str, Any]:
    declarados = envelope.get("campos_publicos", [])
    # `campos_publicos` também vem do arquivo: o que não for lista de nomes não declara nada.
    if not isinstance(declarados, list):
        return {}
    return {
        chave: envelope[chave]
        for chave in declarados
        if isinstance(chave, str) and chave in envelope
    }
