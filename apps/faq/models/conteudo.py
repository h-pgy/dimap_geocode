from django.db import models
from django.db.models import Q

from services.domain.faq import Situacao, Visibilidade


class Faq(models.Model):
    resposta_markdown = models.TextField()
    tema = models.ForeignKey("faq.Tema", on_delete=models.PROTECT, related_name="faqs")
    palavras_chave = models.ManyToManyField(
        "faq.PalavraChave",
        blank=True,
        related_name="faqs",
    )
    visibilidade = models.CharField(
        max_length=10,
        choices=[(v.value, v.value) for v in Visibilidade],
        default=Visibilidade.PUBLICA,
    )
    situacao = models.CharField(
        max_length=10,
        choices=[(s.value, s.value) for s in Situacao],
        default=Situacao.RASCUNHO,
    )
    autor = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    relacionadas = models.ManyToManyField("self", symmetrical=True, blank=True)
    # `atualizado_em` não serve: a seed (faq/008) também grava, e o `auto_now` a move sem editor.
    editado_por = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="faqs_editadas",
    )
    editado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class Pergunta(models.Model):
    # A FK diz "esta linha é de uma FAQ só"; o UNIQUE de `chave` diz "esta pergunta é de uma FAQ só".
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="perguntas")
    texto = models.CharField(max_length=300)
    # Guardada só para o UNIQUE: `normalize_text` não tem equivalente em SQL. Nula na FAQ excluída:
    # o UNIQUE não compara nulos, e a pergunta fica livre para outra FAQ (faq/002).
    chave = models.CharField(max_length=300, unique=True, null=True)
    eh_principal = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "faq",
                condition=Q(eh_principal=True),
                name="faq_uma_pergunta_principal",
            ),
        ]


class LinkReferencia(models.Model):
    faq = models.ForeignKey(Faq, on_delete=models.CASCADE, related_name="links")
    titulo = models.CharField(max_length=120)
    url = models.CharField(max_length=500)
    ordem = models.PositiveSmallIntegerField(default=0)
