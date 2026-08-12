"""
Perfil do servidor da DIMAP (SPEC user_admin/001): autentica pelo RF (não por `username`),
com cargo base e unidade obrigatórios e cargo em comissão opcional. Nome e sobrenome em campos
separados, foto opcional e a cor da unidade vinculada expostos via `cor_unidade` (SPEC
user_admin/006).
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .cargos import CargoBase, CargoComissao
from .titularidade import cargo_titulariza
from .unidade import Unidade

ERRO_TITULAR_SEM_CARGO_COMPATIVEL = "O titular precisa de cargo em comissão de chefia compatível com o porte da unidade."


class PerfilManager(BaseUserManager["Perfil"]):
    # Encanamento exigido pelo contrib.auth (createsuperuser); nenhuma regra de negócio aqui
    # (§3.2) — é a única coisa que vive no manager.
    use_in_migrations = True

    def create_user(
        self,
        rf: str,
        nome: str,
        sobrenome: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "Perfil":
        if not rf:
            raise ValueError("O RF é obrigatório.")
        perfil = self.model(rf=rf, nome=nome, sobrenome=sobrenome, **extra_fields)
        perfil.set_password(password)
        perfil.save(using=self._db)
        return perfil

    def create_superuser(
        self,
        rf: str,
        nome: str,
        sobrenome: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "Perfil":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(rf, nome, sobrenome, password, **extra_fields)


class Perfil(AbstractBaseUser, PermissionsMixin):
    rf = models.CharField(
        max_length=20,
        unique=True,
    )
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=150)
    foto = models.ImageField(
        upload_to="perfis/fotos/",
        null=True,
        blank=True,
    )
    cargo_base = models.ForeignKey(
        CargoBase,
        on_delete=models.PROTECT,
        related_name="perfis",
    )
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="perfis",
    )
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="perfis",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    e_titular = models.BooleanField(default=False)

    objects = PerfilManager()

    USERNAME_FIELD = "rf"
    REQUIRED_FIELDS = ["nome", "sobrenome"]

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"
        constraints = [
            # A unicidade é do vínculo: um titular por unidade, exercendo ou não. Quem cobre o
            # afastado é substituto (SPEC 015), não um segundo marcado.
            models.UniqueConstraint(
                fields=["unidade"],
                condition=Q(e_titular=True),
                name="unidade_tem_um_titular",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.rf} — {self.nome}"

    def clean(self) -> None:
        # Cruza perfil → cargo e perfil → unidade → tipo: nenhuma CheckConstraint alcança.
        if not self.e_titular or not hasattr(self, "unidade"):
            return
        tipo = self.unidade.tipo
        if not cargo_titulariza(
            self.cargo_comissao,
            exige_alta_administracao=tipo.exige_alta_administracao,
            nivel_minimo=tipo.nivel_minimo_titular,
        ):
            raise ValidationError({"e_titular": ERRO_TITULAR_SEM_CARGO_COMPATIVEL})

    @property
    def esta_impedido(self) -> bool:
        hoje = timezone.localdate()
        return self.impedimentos.filter(
            Q(data_fim__isnull=True) | Q(data_fim__gte=hoje),
            data_inicio__lte=hoje,
        ).exists()

    # Deriva da Unidade (SPEC user_admin/005); não duplica a cor no perfil.
    @property
    def cor_unidade(self) -> str:
        return self.unidade.cor
