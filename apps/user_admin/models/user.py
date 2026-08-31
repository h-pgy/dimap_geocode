"""
Perfil do servidor da DIMAP (SPEC user_admin/001): autentica pelo RF (não por `username`),
com cargo base e unidade obrigatórios e cargo em comissão opcional. Nome e sobrenome em campos
separados, foto opcional e a cor da unidade vinculada expostos via `cor_unidade` (SPEC
user_admin/006). E-mail e a marca de senha provisória entram na SPEC criacao_usuarios/004.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.unidades.models import Unidade, cargo_titulariza

from .cargos import CargoBase, CargoComissao
from .periodo import q_vigente_em

ERRO_TITULAR_SEM_CARGO_COMPATIVEL = "O titular precisa de cargo em comissão de chefia compatível com o porte da unidade."
ERRO_UNIDADE_EXTINTA = "A unidade está extinta e não recebe lotação."


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
        # O default do Django nomeia o model ("Perfil com este RF já existe"), e quem cadastra pensa
        # em servidor.
        error_messages={"unique": "Já existe servidor cadastrado com este RF."},
    )
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=150)
    foto = models.ImageField(
        upload_to="perfis/fotos/",
        null=True,
        blank=True,
    )
    # Em branco para o cadastro anterior à criação por tela (SPEC criacao_usuarios/004); a
    # unicidade vale só sobre os preenchidos, na constraint abaixo.
    email = models.EmailField(blank=True)
    # A senha em vigor é a temporária emitida no cadastro, que vale uma vez; quem lê a marca para
    # exigir a troca e derrubá-la é a SPEC de login.
    senha_provisoria = models.BooleanField(default=False)
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
    # SPEC user_admin/027: o dia do ato que tirou a pessoa do quadro. Nula é servidor no quadro, e é
    # o que a reintegração devolve.
    exonerado_em = models.DateField(null=True, blank=True)

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
            # No molde de TipoImpedimento.sigla: vários sem e-mail convivem, dois com o mesmo não.
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="email_unico_quando_preenchido",
                # Constraint com `condition` não herda nem o code nem a mensagem: sem o code
                # `unique` o Django joga a violação em `__all__` e a tela não sabe qual controle
                # realçar; sem a mensagem, quem lê recebe o nome da constraint.
                violation_error_code="unique",
                violation_error_message="Já existe servidor cadastrado com este e-mail.",
            ),
            # SPEC user_admin/027: os dois campos dizem a mesma coisa e são gravados pelo mesmo
            # ato. A regra é da linha, então é do banco.
            models.CheckConstraint(
                condition=Q(is_active=True, exonerado_em__isnull=True)
                | Q(is_active=False, exonerado_em__isnull=False),
                name="perfil_exonerado_tem_data",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.rf} — {self.nome}"

    def clean(self) -> None:
        # Antes da conferência de titularidade, porque ela retorna cedo para quem não é titular —
        # e a lotação em extinta é recusada para todo mundo.
        if hasattr(self, "unidade") and self.unidade.extinta_em is not None:
            raise ValidationError({"unidade": ERRO_UNIDADE_EXTINTA})
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
        return self.impedimentos.filter(q_vigente_em(timezone.localdate())).exists()

    # is_active já existe desde a SPEC 001 e não tinha outro uso: exonerado é quem não é mais
    # servidor da DIMAP, e isso é exatamente o que conta inativa significa — inclusive não entrar.
    @property
    def exonerado(self) -> bool:
        return not self.is_active

    # Derivado, e de exatamente duas causas: coluna própria seria um terceiro valor capaz de
    # discordar das duas, e é essa discordância que a SPEC 015 existe para tornar impossível.
    @property
    def em_exercicio(self) -> bool:
        return not self.exonerado and not self.esta_impedido

    # Deriva da Unidade (SPEC user_admin/005); não duplica a cor no perfil.
    @property
    def cor_unidade(self) -> str:
        return self.unidade.cor

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.sobrenome}"
