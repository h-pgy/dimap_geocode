"""
A persistência do documento emitido (SPEC documentos_oficiais/008), ao lado do model, como
`registro_execucao.py` faz para o rastro do ato. A view chama; a regra não mora aqui.
"""

from apps.competencias.models import ExecucaoAcao
from services.domain.documento_selado import EnvelopeAto, RegistroDocumento
from services.utils.assinatura import DocumentoSelado

from .models import DocumentoEmitido


def guardar_documento(
    selado: DocumentoSelado,
    ato: EnvelopeAto,
    execucao: ExecucaoAcao | None,
) -> DocumentoEmitido:
    return DocumentoEmitido.objects.create(
        codigo=ato.codigo,
        arquivo=selado.pdf,
        envelope=selado.envelope,
        campos_publicos=list(ato.campos_publicos),
        execucao=execucao,
        emitido_em=ato.emitido_em,
    )


def buscar_registro(codigo: str) -> RegistroDocumento | None:
    # `only`: a conferência precisa do envelope e da data, não do PDF inteiro — que é o que faz
    # esta consulta rodar em toda conferência sem carregar megabytes do banco.
    linha = (
        DocumentoEmitido.objects.filter(codigo=codigo)
        .only("codigo", "emitido_em", "envelope")
        .first()
    )
    if linha is None:
        return None
    return RegistroDocumento(
        codigo=linha.codigo,
        emitido_em=linha.emitido_em,
        envelope=linha.envelope,
    )
