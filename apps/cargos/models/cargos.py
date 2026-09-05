"""
Cargos do servidor da DIMAP (SPEC user_admin/001): o cargo base (catálogo simples) e o cargo
em comissão, que carrega sua natureza chefia × assessoramento e o padrão remuneratório
derivado (sigla + nível em algarismo romano).
"""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from services.domain.titularidade import NIVEL_MAXIMO, NIVEL_MINIMO

ROTULO_CHEFIA = "Chefia"
ROTULO_ASSESSORAMENTO = "Assessoramento"
ERRO_ALTA_ADM_SEM_CHEFIA = "Alta administração só se aplica a cargo de chefia."
ERRO_ALTA_ADM_COM_NIVEL = "Cargo da alta administração não tem nível."
ERRO_NIVEL_OBRIGATORIO = "Cargo em comissão fora da alta administração exige nível."
# Faixa fechada em 1..6: tabela em vez de algoritmo de conversão para romano.
ALGARISMOS_ROMANOS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
}
SEPARADOR_PADRAO = "-"


class CargoBase(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )
    # O dia do ato que o retirou da nomeação (SPEC user_admin/030), mesma forma de
    # `CargoComissao.extinto_em`: nula é cargo vigente, e é o que a reativação devolve.
    extinto_em = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Cargo base"
        verbose_name_plural = "Cargos base"

    def __str__(self) -> str:
        return self.sigla

    @property
    def extinto(self) -> bool:
        return self.extinto_em is not None


class CargoComissao(models.Model):
    sigla = models.CharField(max_length=20)
    nivel = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(NIVEL_MINIMO),
            MaxValueValidator(NIVEL_MAXIMO),
        ],
    )
    e_chefia = models.BooleanField()
    alta_administracao = models.BooleanField(default=False)
    # O padrão colide entre cargos (CDA-II serve diretor de divisão e assessor II); o nome é
    # o que identifica.
    nome = models.CharField(
        max_length=200,
        unique=True,
    )
    # O dia do ato que o retirou da nomeação (SPEC user_admin/029). Nula é cargo vigente, e é o
    # que a reativação devolve — mesma forma de `Unidade.extinta_em` e `Perfil.exonerado_em`.
    extinto_em = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Cargo em comissão"
        verbose_name_plural = "Cargos em comissão"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        alta_administracao=True,
                        nivel__isnull=True,
                    )
                    | Q(
                        alta_administracao=False,
                        nivel__gte=NIVEL_MINIMO,
                        nivel__lte=NIVEL_MAXIMO,
                    )
                ),
                name="cargo_comissao_nivel_conforme_alta_administracao",
            ),
            models.CheckConstraint(
                condition=Q(alta_administracao=False) | Q(e_chefia=True),
                name="cargo_comissao_alta_administracao_e_chefia",
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    @property
    def natureza(self) -> str:
        return ROTULO_CHEFIA if self.e_chefia else ROTULO_ASSESSORAMENTO

    @property
    def extinto(self) -> bool:
        return self.extinto_em is not None

    @property
    def padrao(self) -> str:
        if self.nivel is None:
            return self.sigla
        return f"{self.sigla}{SEPARADOR_PADRAO}{ALGARISMOS_ROMANOS[self.nivel]}"

    def clean(self) -> None:
        # Espelha as constraints: sem isso o erro só apareceria como IntegrityError no save.
        if self.alta_administracao and not self.e_chefia:
            raise ValidationError({"alta_administracao": ERRO_ALTA_ADM_SEM_CHEFIA})
        if self.alta_administracao and self.nivel is not None:
            raise ValidationError({"nivel": ERRO_ALTA_ADM_COM_NIVEL})
        if not self.alta_administracao and self.nivel is None:
            raise ValidationError({"nivel": ERRO_NIVEL_OBRIGATORIO})
