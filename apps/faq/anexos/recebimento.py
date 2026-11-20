from hashlib import sha256
from pathlib import Path

from django.conf import settings
from pydantic import BaseModel, Field, computed_field

from apps.faq.models import Anexo as AnexoModel
from services.domain.faq import Editor
from services.utils.extracao_texto import (
    ExtracaoConfig,
    ExtracaoImpossivel,
    ExtratorTexto,
    OrigemTexto,
    TextoExtraido,
    TipoDocumento,
)

FAQ_ANEXO_TAMANHO_MAXIMO_BYTES: int = settings.FAQ_ANEXO_TAMANHO_MAXIMO_BYTES
FAQ_ANEXO_PAGINAS_MAXIMAS_OCR: int = settings.FAQ_ANEXO_PAGINAS_MAXIMAS_OCR
FAQ_ANEXO_PRAZO_OCR_S: float = settings.FAQ_ANEXO_PRAZO_OCR_S
FAQ_ANEXO_IDIOMA_OCR: str = settings.FAQ_ANEXO_IDIOMA_OCR
FAQ_ANEXO_DPI_OCR: int = settings.FAQ_ANEXO_DPI_OCR
TAMANHO_TITULO = 160


class EnvioAnexo(BaseModel):
    nome_arquivo: str = Field(min_length=1, max_length=255)
    conteudo: bytes = Field(min_length=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def titulo(self) -> str:
        return Path(self.nome_arquivo).stem[:TAMANHO_TITULO]


class AnexoNovo(BaseModel):
    """Arquivo já extraído e ainda não gravado."""

    envio: EnvioAnexo
    hash_conteudo: str
    tipo: TipoDocumento
    texto: TextoExtraido


class AnexosPreparados(BaseModel):
    # Mesmo hash de um anexo já gravado: só se liga.
    existentes: list[int] = []
    novos: list[AnexoNovo] = []


class ConferenciaAnexo(BaseModel):
    """O veredito de um arquivo escolhido, antes de qualquer gravação."""

    nome_arquivo: str
    tamanho_bytes: int
    tipo: TipoDocumento | None = None
    recusa: str | None = None
    origem: OrigemTexto | None = None

    @property
    def eh_aceito(self) -> bool:
        return self.recusa is None

    @property
    def eh_ocr(self) -> bool:
        return self.origem is OrigemTexto.OCR


def extracao_config() -> ExtracaoConfig:
    return ExtracaoConfig(
        tamanho_maximo_bytes=FAQ_ANEXO_TAMANHO_MAXIMO_BYTES,
        paginas_maximas_ocr=FAQ_ANEXO_PAGINAS_MAXIMAS_OCR,
        prazo_ocr_s=FAQ_ANEXO_PRAZO_OCR_S,
        idioma_ocr=FAQ_ANEXO_IDIOMA_OCR,
        dpi_ocr=FAQ_ANEXO_DPI_OCR,
    )


def conferir_anexos(envios: list[EnvioAnexo]) -> list[ConferenciaAnexo]:
    config = extracao_config()
    extrair_texto = ExtratorTexto(config)
    return [_conferir(extrair_texto, envio) for envio in envios]


def preparar_anexos(envios: list[EnvioAnexo]) -> AnexosPreparados:
    config = extracao_config()
    extrair_texto = ExtratorTexto(config)
    preparados = AnexosPreparados()
    for envio in envios:
        hash_conteudo = sha256(envio.conteudo).hexdigest()
        existente = (
            AnexoModel.objects.filter(hash_conteudo=hash_conteudo)
            .values_list("pk", flat=True)
            .first()
        )
        if existente is not None:
            # Título e texto do primeiro envio prevalecem.
            preparados.existentes.append(existente)
            continue
        try:
            tipo, texto = extrair_texto(envio.conteudo)
        except ExtracaoImpossivel as erro:
            # Com vários arquivos no mesmo salvar, a mensagem precisa dizer qual foi recusado.
            raise ExtracaoImpossivel(f"{envio.nome_arquivo}: {erro}") from erro
        preparados.novos.append(
            AnexoNovo(envio=envio, hash_conteudo=hash_conteudo, tipo=tipo, texto=texto)
        )
    return preparados


def gravar_anexos(preparados: AnexosPreparados, editor: Editor) -> list[int]:
    ids = list(preparados.existentes)
    for novo in preparados.novos:
        # O mesmo arquivo duas vezes no envio, ou gravado por outro salvar entre a preparação e a
        # transação, vira o mesmo anexo em vez de violar o unique do hash.
        registro, _ = AnexoModel.objects.get_or_create(
            hash_conteudo=novo.hash_conteudo,
            defaults={
                "titulo": novo.envio.titulo,
                "nome_arquivo": novo.envio.nome_arquivo,
                "tipo": novo.tipo,
                "arquivo": novo.envio.conteudo,
                "tamanho_bytes": len(novo.envio.conteudo),
                "texto": novo.texto.conteudo,
                "origem_texto": novo.texto.origem,
                "enviado_por_id": editor.perfil_id,
            },
        )
        ids.append(registro.pk)
    return ids


def _conferir(extrair_texto: ExtratorTexto, envio: EnvioAnexo) -> ConferenciaAnexo:
    tamanho_bytes = len(envio.conteudo)
    try:
        tipo, origem = extrair_texto.conferir(envio.conteudo)
    except ExtracaoImpossivel as erro:
        return ConferenciaAnexo(
            nome_arquivo=envio.nome_arquivo,
            tamanho_bytes=tamanho_bytes,
            recusa=str(erro),
        )
    return ConferenciaAnexo(
        nome_arquivo=envio.nome_arquivo,
        tamanho_bytes=tamanho_bytes,
        tipo=tipo,
        origem=origem,
    )
