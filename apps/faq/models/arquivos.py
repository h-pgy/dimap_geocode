from django.db import models
from django.db.models import Q

from services.utils.extracao_texto import OrigemTexto, TipoDocumento


class Anexo(models.Model):
    titulo = models.CharField(max_length=160)
    nome_arquivo = models.CharField(max_length=255)
    tipo = models.CharField(
        max_length=4, choices=[(t.value, t.value) for t in TipoDocumento]
    )
    # Mesmo padrão do acervo de documentos emitidos: o arquivo vive na linha.
    arquivo = models.BinaryField()
    hash_conteudo = models.CharField(max_length=64, unique=True)
    tamanho_bytes = models.PositiveIntegerField()
    texto = models.TextField()
    origem_texto = models.CharField(
        max_length=16, choices=[(o.value, o.value) for o in OrigemTexto]
    )
    enviado_por = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # "Não existe anexo sem texto" também no banco, não só no extrator.
            models.CheckConstraint(condition=~Q(texto=""), name="faq_anexo_com_texto"),
        ]
