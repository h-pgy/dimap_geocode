from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from .models import MarcacaoConfig, PaletaDocumento, TemaConfig, TipografiaDocumento


class DocumentoSettingsLike(Protocol):
    DOCUMENTO_LOGO_HORIZONTAL: Path
    DOCUMENTO_LOGO_VERTICAL: Path
    DOCUMENTO_UNIDADE: tuple[str, ...] | None
    DOCUMENTO_ENDERECO: tuple[str, ...] | None
    DOCUMENTO_COR_TINTA: str | None
    DOCUMENTO_COR_TINTA_SECUNDARIA: str | None
    DOCUMENTO_COR_TRACO_TABELA: str | None
    DOCUMENTO_COR_FUNDO_CABECALHO_TABELA: str | None
    DOCUMENTO_FONTE: str | None
    DOCUMENTO_FONTE_NEGRITO: str | None
    DOCUMENTO_CORPO_TITULO_PT: float | None
    DOCUMENTO_CORPO_SUBTITULO_PT: tuple[float, float, float] | None
    DOCUMENTO_CORPO_PARAGRAFO_PT: float | None
    DOCUMENTO_CORPO_PARAGRAFO_RECUADO_PT: float | None
    DOCUMENTO_CORPO_CELULA_PT: float | None
    DOCUMENTO_CORPO_CABECALHO_MARCA_PT: float | None
    DOCUMENTO_CORPO_RODAPE_MARCA_PT: float | None
    DOCUMENTO_FATOR_ENTRELINHA: float | None
    DOCUMENTO_ENTRELINHA_MARCA_MM: float | None


def _definidos[M: BaseModel](modelo: type[M], valores: Mapping[str, object]) -> M:
    # Só o que o ambiente DEFINIU é repassado: campo ausente deixa o default do model valer.
    # Passar `None` adiante sobrescreveria o padrão com vazio e obrigaria cada valor a existir
    # aqui também — duas cópias livres para divergir.
    return modelo(**{chave: valor for chave, valor in valores.items() if valor is not None})


def build_marcacao_config(source: DocumentoSettingsLike) -> MarcacaoConfig:
    valores: dict[str, object] = {
        "logo_horizontal": source.DOCUMENTO_LOGO_HORIZONTAL,
        "logo_vertical": source.DOCUMENTO_LOGO_VERTICAL,
    }
    valores.update(
        {
            chave: valor
            for chave, valor in (
                ("unidade", source.DOCUMENTO_UNIDADE),
                ("endereco", source.DOCUMENTO_ENDERECO),
            )
            if valor is not None
        }
    )
    return MarcacaoConfig.model_validate(valores)


def build_tema_config(source: DocumentoSettingsLike) -> TemaConfig:
    return TemaConfig(
        paleta=_definidos(
            PaletaDocumento,
            {
                "tinta": source.DOCUMENTO_COR_TINTA,
                "tinta_secundaria": source.DOCUMENTO_COR_TINTA_SECUNDARIA,
                "traco_tabela": source.DOCUMENTO_COR_TRACO_TABELA,
                "fundo_cabecalho_tabela": source.DOCUMENTO_COR_FUNDO_CABECALHO_TABELA,
            },
        ),
        tipografia=_definidos(
            TipografiaDocumento,
            {
                "fonte": source.DOCUMENTO_FONTE,
                "fonte_negrito": source.DOCUMENTO_FONTE_NEGRITO,
                "corpo_titulo_pt": source.DOCUMENTO_CORPO_TITULO_PT,
                "corpo_subtitulo_pt": source.DOCUMENTO_CORPO_SUBTITULO_PT,
                "corpo_paragrafo_pt": source.DOCUMENTO_CORPO_PARAGRAFO_PT,
                "corpo_paragrafo_recuado_pt": source.DOCUMENTO_CORPO_PARAGRAFO_RECUADO_PT,
                "corpo_celula_pt": source.DOCUMENTO_CORPO_CELULA_PT,
                "corpo_cabecalho_marca_pt": source.DOCUMENTO_CORPO_CABECALHO_MARCA_PT,
                "corpo_rodape_marca_pt": source.DOCUMENTO_CORPO_RODAPE_MARCA_PT,
                "fator_entrelinha": source.DOCUMENTO_FATOR_ENTRELINHA,
                "entrelinha_marca_mm": source.DOCUMENTO_ENTRELINHA_MARCA_MM,
            },
        ),
    )
