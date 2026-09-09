"""
O acervo (SPEC documentos_oficiais/008): a linha índice do documento emitido. Só persistência —
a regra de quem pode conferir o quê mora em services/domain/documento_selado/.
"""

from django.db import models

from services.domain.documento_selado.constants import TAMANHO_CODIGO


class DocumentoEmitido(models.Model):
    codigo = models.CharField(max_length=TAMANHO_CODIGO, unique=True, editable=False)
    # `BinaryField` é `bytea`: o PDF vive na linha. Na escala do sistema — dezenas de usuários — um
    # arquivo, uma linha e uma transação valem mais que um storage a operar (SPEC, Caveats).
    arquivo = models.BinaryField(editable=False)
    # O envelope também está DENTRO do arquivo. Esta cópia é índice consultável e fonte da ficha,
    # nunca a fonte da conferência (SPEC, Caveats).
    envelope = models.JSONField(editable=False)
    campos_publicos = models.JSONField(default=list, editable=False)
    # Nulo enquanto houver emissão que não venha de ação inscrita — a amostra, por exemplo.
    execucao = models.ForeignKey(
        "competencias.ExecucaoAcao",
        on_delete=models.PROTECT,
        related_name="documentos",
        null=True,
        blank=True,
    )
    emitido_em = models.DateTimeField(editable=False)

    class Meta:
        verbose_name = "Documento emitido"
        verbose_name_plural = "Documentos emitidos"
        # A conferência entra sempre pelo código, e a listagem futura, pela data.
        indexes = [models.Index(fields=["-emitido_em"])]

    def __str__(self) -> str:
        return self.codigo
