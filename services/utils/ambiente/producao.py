from collections.abc import Callable

from pydantic import BaseModel, SecretStr

TAMANHO_MINIMO_SEGREDO = 50
CARACTERES_DISTINTOS_MINIMOS_SEGREDO = 5
TAMANHO_MINIMO_SENHA_BANCO = 16


class AmbienteProducaoInput(BaseModel):
    debug: bool
    secret_key: SecretStr
    assinatura_segredo: SecretStr
    postgres_password: SecretStr
    allowed_hosts: list[str]
    csrf_trusted_origins: list[str]
    email_envio_habilitado: bool
    enforce_prefeitura_email: bool


class Violacao(BaseModel):
    variavel: str
    motivo: str


class AmbienteProducaoOutput(BaseModel):
    violacoes: tuple[Violacao, ...]


type Regra = Callable[[AmbienteProducaoInput], Violacao | None]


class ChecarAmbienteProducao:
    def __call__(self, ambiente: AmbienteProducaoInput) -> AmbienteProducaoOutput:
        return self.pipeline(ambiente)

    def pipeline(self, ambiente: AmbienteProducaoInput) -> AmbienteProducaoOutput:
        regras: tuple[Regra, ...] = (
            self._debug,
            self._secret_key,
            self._assinatura_segredo,
            self._senha_banco,
            self._allowed_hosts,
            self._csrf_trusted_origins,
            self._envio_email,
            self._enforce_prefeitura_email,
        )
        violacoes = tuple(v for regra in regras if (v := regra(ambiente)) is not None)
        return AmbienteProducaoOutput(violacoes=violacoes)

    def _debug(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if not ambiente.debug:
            return None
        return Violacao(
            variavel="DJANGO_DEBUG",
            motivo="debug ligado expõe traceback e configuração a qualquer visitante.",
        )

    def _secret_key(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if not self._eh_segredo_fraco(ambiente.secret_key):
            return None
        return Violacao(
            variavel="DJANGO_SECRET_KEY",
            motivo=self._motivo_segredo_fraco(),
        )

    def _assinatura_segredo(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if not self._eh_segredo_fraco(ambiente.assinatura_segredo):
            return None
        return Violacao(
            variavel="ASSINATURA_SEGREDO",
            motivo=self._motivo_segredo_fraco(),
        )

    def _senha_banco(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if len(ambiente.postgres_password.get_secret_value()) >= TAMANHO_MINIMO_SENHA_BANCO:
            return None
        return Violacao(
            variavel="POSTGRES_PASSWORD",
            motivo=f"precisa de ao menos {TAMANHO_MINIMO_SENHA_BANCO} caracteres.",
        )

    def _allowed_hosts(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if "*" not in ambiente.allowed_hosts:
            return None
        return Violacao(
            variavel="DJANGO_ALLOWED_HOSTS",
            motivo="'*' aceita qualquer Host, e os links de e-mail e QR code são montados com ele.",
        )

    def _csrf_trusted_origins(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        inseguras = [
            origem
            for origem in ambiente.csrf_trusted_origins
            if "*" in origem or origem.startswith("http://")
        ]
        if not inseguras:
            return None
        return Violacao(
            variavel="DJANGO_CSRF_TRUSTED_ORIGINS",
            motivo=f"origens com curinga ou sem HTTPS: {', '.join(inseguras)}.",
        )

    def _envio_email(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if ambiente.email_envio_habilitado:
            return None
        return Violacao(
            variavel="EMAIL_ENVIO_HABILITADO",
            motivo="desligado, a senha de uso único aparece na tela de quem digitar o RF.",
        )

    def _enforce_prefeitura_email(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if ambiente.enforce_prefeitura_email:
            return None
        return Violacao(
            variavel="ENFORCE_PREFEITURA_EMAIL",
            motivo="desligado, o cadastro de servidor aceita e-mail fora dos domínios institucionais.",
        )

    def _eh_segredo_fraco(self, segredo: SecretStr) -> bool:
        # Os defaults de dev ficam abaixo do tamanho mínimo: a regra os pega sem conhecer cada um.
        valor = segredo.get_secret_value()
        return (
            len(valor) < TAMANHO_MINIMO_SEGREDO
            or len(set(valor)) < CARACTERES_DISTINTOS_MINIMOS_SEGREDO
        )

    def _motivo_segredo_fraco(self) -> str:
        return (
            f"precisa de ao menos {TAMANHO_MINIMO_SEGREDO} caracteres aleatórios "
            f"({CARACTERES_DISTINTOS_MINIMOS_SEGREDO} ou mais distintos)."
        )


checar_ambiente_producao = ChecarAmbienteProducao()
