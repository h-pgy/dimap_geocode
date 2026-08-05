"""
Unidade da DIMAP (SPEC user_admin/001) e sua hierarquia (SPEC user_admin/003): o tipo carrega o
nível de subordinação, as vedas nominais de tipo-filho e a marca de tipo-raiz; a unidade referencia
o tipo e, opcionalmente, uma unidade superior. Também carrega a cor de identidade visual (SPEC
user_admin/005).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

ERRO_NIVEL_NAO_SUBORDINA = "A unidade pai precisa ser de um tipo de nível superior."
ERRO_TIPO_FILHO_VEDADO = "A unidade pai não admite filhas deste tipo."
ERRO_TIPO_EXIGE_PAI = "Unidades deste tipo precisam ter uma unidade superior."


class CorUnidade(models.TextChoices):
    # Tons a partir daqui passam o piso de contraste 4,5:1 contra a tinta base-100 (#F2F8FB) —
    # ver SPEC user_admin/005. A resolução slug → hex mora na borda do app, não no domínio.
    AGUA_700 = "agua-700", "Água 700"
    AGUA_800 = "agua-800", "Água 800"
    ROCHA_700 = "rocha-700", "Rocha 700"
    ROCHA_900 = "rocha-900", "Rocha 900"
    MADEIRA_600 = "madeira-600", "Madeira 600"
    MADEIRA_700 = "madeira-700", "Madeira 700"
    SAKURA_600 = "sakura-600", "Sakura 600"
    SAKURA_700 = "sakura-700", "Sakura 700"


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
    # Repetir cor entre unidades é aceito: a cor é pista de identidade, não chave.
    cor = models.CharField(
        max_length=20,
        choices=CorUnidade,
        default=CorUnidade.AGUA_700,
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

    # Valor inicial oferecido ao formulário de cadastro; a unidade grava a cor que escolher.
    @property
    def cor_sugerida(self) -> str:
        return self.pai.cor if self.pai else CorUnidade.AGUA_700
