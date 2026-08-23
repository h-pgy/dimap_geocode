"""
Os dois níveis da competência (SPEC autorizacao/002): `AtribuicaoUnidade` é o que a unidade faz;
`Concessao` é quem, dentro dela, exerce — pendurada na LINHA da atribuição, nunca na dupla solta
unidade × ação, para que conceder o que a unidade não tem seja integridade referencial, não
validação de aplicação.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.unidades.models import Unidade
from apps.user_admin.models import CargoBase, CargoComissao

from .acao import Acao

ERRO_CARGO_XOR = "A concessão nomeia exatamente um cargo: base ou em comissão, nunca os dois."


class AtribuicaoUnidade(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="atribuicoes")
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="atribuicoes")

    class Meta:
        verbose_name = "Atribuição de unidade"
        verbose_name_plural = "Atribuições de unidade"
        constraints = [
            models.UniqueConstraint(
                fields=["unidade", "acao"],
                name="atribuicao_unica_por_unidade_e_acao",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.unidade} — {self.acao}"


class Concessao(models.Model):
    atribuicao = models.ForeignKey(
        AtribuicaoUnidade,
        on_delete=models.CASCADE,
        related_name="concessoes",
    )
    # XOR entre os dois FKs abaixo: uma concessão nomeia cargo_base OU cargo_comissao —
    # exatamente um preenchido, nunca os dois, nunca nenhum. Ambos são anuláveis no schema
    # porque cada concessão só preenche um dos ramos; o "exatamente um" quem garante é a
    # CheckConstraint `concessao_exatamente_um_cargo` (abaixo), espelhada no `clean()`.
    cargo_base = models.ForeignKey(
        CargoBase,
        on_delete=models.PROTECT,
        related_name="concessoes",
        null=True,
        blank=True,
    )
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="concessoes",
        null=True,
        blank=True,
    )
    # Procedência, não log de ato (SPEC 004): sem isto ninguém sabe quem liberou o quê.
    concedida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="concessoes_feitas",
        null=True,
    )
    concedida_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Concessão"
        verbose_name_plural = "Concessões"
        constraints = [
            # XOR explícito: FK genérico esconderia qual cargo é qual, e dois campos com check
            # barram o estado inválido antes de ele existir.
            models.CheckConstraint(
                condition=(
                    Q(cargo_base__isnull=False, cargo_comissao__isnull=True)
                    | Q(cargo_base__isnull=True, cargo_comissao__isnull=False)
                ),
                name="concessao_exatamente_um_cargo",
            ),
            # Uma constraint por ramo do XOR: com uma constraint única sobre os três campos, o FK
            # nulo do outro ramo deixaria a duplicata passar (nulos não colidem no Postgres).
            models.UniqueConstraint(
                fields=["atribuicao", "cargo_base"],
                condition=Q(cargo_base__isnull=False),
                name="concessao_unica_por_cargo_base",
            ),
            models.UniqueConstraint(
                fields=["atribuicao", "cargo_comissao"],
                condition=Q(cargo_comissao__isnull=False),
                name="concessao_unica_por_cargo_comissao",
            ),
        ]

    def __str__(self) -> str:
        cargo = self.cargo_base or self.cargo_comissao
        return f"{self.atribuicao} → {cargo}"

    def clean(self) -> None:
        # Espelha a CheckConstraint: sem isso o erro só apareceria como IntegrityError no save.
        if (self.cargo_base is None) == (self.cargo_comissao is None):
            raise ValidationError(ERRO_CARGO_XOR)
