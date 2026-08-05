"""
Perfil do servidor da DIMAP (SPEC user_admin/001): autentica pelo RF (não por `username`),
com cargo base e unidade obrigatórios e cargo em comissão opcional. Nome e sobrenome em campos
separados, foto opcional e a cor da unidade vinculada expostos via `cor_unidade` (SPEC
user_admin/006).
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .cargos import CargoBase, CargoComissao
from .unidade import Unidade


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

    objects = PerfilManager()

    USERNAME_FIELD = "rf"
    REQUIRED_FIELDS = ["nome", "sobrenome"]

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self) -> str:
        return f"{self.rf} — {self.nome}"

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
