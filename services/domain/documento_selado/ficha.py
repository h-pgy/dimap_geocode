from typing import Any

from services.utils.assinatura import ResultadoConferencia, extrair_publicos

from .models import EnvelopeAto, FichaDoAto


def codigo_alegado(resultado: ResultadoConferencia) -> str | None:
    """O resultado do selo INTEIRO, e não o dicionário do envelope solto: é o DTO que atravessa a
    fronteira. O envelope de um arquivo forjado põe o que quiser em `codigo` — inclusive nada, ou um
    número. A rota é aberta: o que não for texto não é código, e não vira consulta ao acervo."""
    envelope = resultado.envelope
    if envelope is None:
        return None
    codigo = envelope.get("codigo")
    return codigo if isinstance(codigo, str) else None


class LerFichaDoAto:
    """Callable: o envelope GUARDADO → a ficha. `model_validate` sem defesa porque a entrada é o que
    esta aplicação escreveu na emissão, e não o que chegou pelo formulário."""

    def __call__(self, envelope: dict[str, Any]) -> FichaDoAto:
        ato = EnvelopeAto.model_validate(envelope)
        return FichaDoAto(
            codigo=ato.codigo,
            # O autor inteiro: cargo de comissão e substituição fazem parte de quem assinou.
            autor=ato.autor,
            assinado_em=ato.emitido_em,
            # A selagem achatou os extras junto do núcleo, então o nome declarado público acha o
            # valor no dicionário inteiro — e não só nos campos do `EnvelopeAto`.
            publicos=extrair_publicos(envelope),
        )


ler_ficha_do_ato = LerFichaDoAto()
