"""
Unidade da DIMAP (SPEC user_admin/001) e sua hierarquia (SPEC user_admin/003): o tipo carrega o
nível de subordinação, as vedas nominais de tipo-filho e a marca de tipo-raiz; a unidade referencia
o tipo e, opcionalmente, uma unidade superior. Também carrega a cor de identidade visual (SPEC
user_admin/005).
"""

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from services.domain.titularidade import NIVEL_MAXIMO, NIVEL_MINIMO

from .titularidade import cargo_titulariza

# Só para a anotação: em runtime este app não conhece `user_admin`, que é quem o conhece.
if TYPE_CHECKING:
    from apps.user_admin.models import Perfil

ERRO_NIVEL_NAO_SUBORDINA = "A unidade pai precisa ser de um tipo de nível superior."
ERRO_TIPO_FILHO_VEDADO = "A unidade pai não admite filhas deste tipo."
ERRO_TIPO_EXIGE_PAI = "Unidades deste tipo precisam ter uma unidade superior."
ERRO_ALTA_ADM_COM_MINIMO = (
    "Tipo que exige alta administração não tem nível mínimo de titular."
)
ERRO_MINIMO_TITULAR_OBRIGATORIO = (
    "Tipo fora da alta administração exige nível mínimo de titular."
)
ERRO_TIPO_INCOMPATIVEL_COM_TITULAR = (
    "O titular atual não satisfaz o mínimo de cargo deste tipo."
)


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
    # A exigência é declarada; sem ela, o tipo novo herdaria calado a regra mais restritiva.
    exige_alta_administracao = models.BooleanField(default=False)
    nivel_minimo_titular = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(NIVEL_MINIMO),
            MaxValueValidator(NIVEL_MAXIMO),
        ],
    )

    class Meta:
        verbose_name = "Tipo de unidade"
        verbose_name_plural = "Tipos de unidade"
        constraints = [
            # Uma coluna exclui a outra — o mesmo pareamento de alta_administracao × nivel em
            # CargoComissao, e a mesma constraint espelhada no clean().
            models.CheckConstraint(
                condition=(
                    Q(
                        exige_alta_administracao=True,
                        nivel_minimo_titular__isnull=True,
                    )
                    | Q(
                        exige_alta_administracao=False,
                        nivel_minimo_titular__gte=NIVEL_MINIMO,
                        nivel_minimo_titular__lte=NIVEL_MAXIMO,
                    )
                ),
                name="tipo_unidade_minimo_conforme_alta_administracao",
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        if self.exige_alta_administracao and self.nivel_minimo_titular is not None:
            raise ValidationError({"nivel_minimo_titular": ERRO_ALTA_ADM_COM_MINIMO})
        if not self.exige_alta_administracao and self.nivel_minimo_titular is None:
            raise ValidationError(
                {"nivel_minimo_titular": ERRO_MINIMO_TITULAR_OBRIGATORIO}
            )


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

    # A vaga é a ausência do vínculo, e quem responde por ela é a unidade. Derivado, não coluna:
    # gravar duplicaria as linhas de Perfil. Precedente: Perfil.esta_impedido.
    @property
    def titular(self) -> "Perfil | None":
        return self.perfis.filter(e_titular=True).first()

    def clean(self) -> None:
        self._checar_titular()
        self._checar_hierarquia()

    def _checar_titular(self) -> None:
        # O outro lado da mesma adequação: mudar o tipo quebra o que o cargo do titular satisfazia.
        if self.pk is None or not hasattr(self, "tipo"):
            return
        titular = self.titular
        if titular is None:
            return
        if not cargo_titulariza(
            titular.cargo_comissao,
            exige_alta_administracao=self.tipo.exige_alta_administracao,
            nivel_minimo=self.tipo.nivel_minimo_titular,
        ):
            raise ValidationError({"tipo": ERRO_TIPO_INCOMPATIVEL_COM_TITULAR})

    def _checar_hierarquia(self) -> None:
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
