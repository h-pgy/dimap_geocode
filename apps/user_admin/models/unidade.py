"""
Unidade da DIMAP (SPEC user_admin/001) e sua hierarquia (SPEC user_admin/003): o tipo carrega o
nível de subordinação, as vedas nominais de tipo-filho e a marca de tipo-raiz; a unidade referencia
o tipo e, opcionalmente, uma unidade superior.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

ERRO_NIVEL_NAO_SUBORDINA = "A unidade pai precisa ser de um tipo de nível superior."
ERRO_TIPO_FILHO_VEDADO = "A unidade pai não admite filhas deste tipo."
ERRO_TIPO_EXIGE_PAI = "Unidades deste tipo precisam ter uma unidade superior."


class TipoUnidade(models.Model):
    nome = models.CharField(
        max_length=60,
        unique=True,
    )
    # Nível maior = mais abrangente; empate significa que nenhum dos dois contém o outro.
    nivel = models.PositiveSmallIntegerField()
    # Desligado por padrão: encabeçar árvore é exceção declarada no seed, não default silencioso.
    pode_ser_raiz = models.BooleanField(default=False)
    # Exceção ao nível: coordenadoria segue superior à divisão, mas pode recusá-la como filha.
    tipos_filhos_vedados = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="vedado_como_filho_em",
        blank=True,
    )

    class Meta:
        verbose_name = "Tipo de unidade"
        verbose_name_plural = "Tipos de unidade"

    def __str__(self) -> str:
        return self.nome


class Unidade(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )
    tipo = models.ForeignKey(
        TipoUnidade,
        on_delete=models.PROTECT,
        related_name="unidades",
    )
    pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="filhas",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"
        constraints = [
            models.CheckConstraint(
                condition=~Q(pai=F("id")),
                name="unidade_nao_e_pai_de_si_mesma",
            ),
        ]

    def __str__(self) -> str:
        return self.sigla

    def clean(self) -> None:
        # Sem tipo não há regra a aplicar; quem acusa a ausência é o clean_fields.
        if not hasattr(self, "tipo"):
            return
        if self.pai is None:
            if not self.tipo.pode_ser_raiz:
                raise ValidationError({"pai": ERRO_TIPO_EXIGE_PAI})
            return
        # Nível e vedas vivem no tipo: as regras cruzam tabela e nenhuma CheckConstraint as alcança.
        tipo_pai = self.pai.tipo
        if self.tipo.nivel >= tipo_pai.nivel:
            raise ValidationError({"pai": ERRO_NIVEL_NAO_SUBORDINA})
        if tipo_pai.tipos_filhos_vedados.filter(pk=self.tipo.pk).exists():
            raise ValidationError({"pai": ERRO_TIPO_FILHO_VEDADO})
