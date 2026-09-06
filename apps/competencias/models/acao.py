"""
Projeção da ação no banco (SPEC autorizacao/002): fonte é o registro em código
(`apps.competencias.registro.REGISTRO`), não esta tabela — ela existe para dar FK de verdade à
atribuição e à concessão. Mantida em dia por `apps.competencias.sync.sincronizar_acoes`.
"""

from django.db import models

LIMITE_SLUG = 120
LIMITE_NOME = 120
LIMITE_NOME_CURTO = 60
LIMITE_TOOLTIP = 255


class Acao(models.Model):
    slug = models.CharField(max_length=LIMITE_SLUG, unique=True)
    nome = models.CharField(max_length=LIMITE_NOME)
    nome_curto = models.CharField(max_length=LIMITE_NOME_CURTO, blank=True)
    tooltip = models.CharField(max_length=LIMITE_TOOLTIP)
    # Ação some do código sem levar junto atribuições e concessões já concedidas.
    ativa = models.BooleanField(default=True)
    # Já liberada a quem dirige a unidade, sem concessão gravada; projetada para o avaliador saber
    # de quais slugs isso vale.
    estrutural = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ação"
        verbose_name_plural = "Ações"

    def __str__(self) -> str:
        return self.slug
