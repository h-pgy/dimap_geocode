from django.conf import settings
from django.contrib.gis.db import models

# o ponto é guardado na projeção em que é servido: sem reprojeção na leitura
SRID_PONTO: int = settings.MAP_OUTPUT_CRS


class GeocodificacaoGuardada(models.Model):
    chave = models.TextField()
    consulta = models.TextField()
    # quem encontrou: dado da linha, não critério da busca
    provedor = models.CharField(max_length=20)
    consultado_em = models.DateTimeField()
    ponto = models.PointField(srid=SRID_PONTO)
    endereco_formatado = models.TextField()
    # nulo = o provedor não informou; vazio seria outra resposta
    logradouro = models.TextField(null=True)
    numero = models.TextField(null=True)
    bairro = models.TextField(null=True)
    municipio = models.TextField(null=True)
    uf = models.TextField(null=True)
    cep = models.TextField(null=True)
    precisao = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Geocodificação guardada"
        verbose_name_plural = "Geocodificações guardadas"
        constraints = [
            # a unicidade já é o índice da busca: a chave é o que `buscar` filtra
            models.UniqueConstraint(
                fields=["chave"],
                name="geocodificacao_guardada_unica",
            ),
        ]

    def __str__(self) -> str:
        return self.consulta
