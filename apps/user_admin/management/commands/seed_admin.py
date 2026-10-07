from argparse import ArgumentParser

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from pydantic import ValidationError as PydanticValidationError

from apps.user_admin.seeds import ConfiguracaoAdmin, DesfechoAdmin, carregar_seed_admin

ADMIN_RF: str = settings.ADMIN_RF
ADMIN_EMAIL: str = settings.ADMIN_EMAIL
EMAIL_ENVIO_HABILITADO: bool = settings.EMAIL_ENVIO_HABILITADO

MENSAGENS: dict[DesfechoAdmin, str] = {
    DesfechoAdmin.CRIADO: (
        "nenhum admin encontrado: admin criado com o RF {rf}. Para entrar, informe o RF na tela "
        "de login e peça a senha de uso único."
    ),
    DesfechoAdmin.DISPENSADO: "admin já existe: criação pulada.",
    DesfechoAdmin.SEM_EMAIL: (
        "ERRO: nenhum admin encontrado e admin NÃO criado. Defina ADMIN_EMAIL e suba de novo."
    ),
    DesfechoAdmin.RF_OCUPADO: (
        "ERRO: nenhum admin encontrado e admin NÃO criado: o RF {rf} já pertence a um "
        "servidor. Mude ADMIN_RF ou use criar_superusuario."
    ),
}
# Erro para quem lê o log, não para o processo: `CommandError` faria o `set -e` do entrypoint
# derrubar a subida.
ERROS = frozenset({DesfechoAdmin.SEM_EMAIL, DesfechoAdmin.RF_OCUPADO})
# Em estilo de erro de propósito: é o que separa um deploy de produção de um administrador cuja
# senha qualquer visitante consegue ver.
ALERTA_SENHA_EM_TELA = (
    "\n"
    "############################################################################\n"
    "#  ATENÇÃO: ADMIN CRIADO COM O ENVIO DE E-MAIL DESLIGADO.                  #\n"
    "#  A SENHA DE USO ÚNICO APARECE NA TELA PARA QUEM INFORMAR O RF DO ADMIN.  #\n"
    "#  SE ISTO É PRODUÇÃO, LIGUE EMAIL_ENVIO_HABILITADO E FAÇA O PRIMEIRO      #\n"
    "#  ACESSO AGORA.                                                           #\n"
    "############################################################################\n"
)


class Command(BaseCommand):
    help = "Cria o admin inicial (data/seed/admin.json) quando o sistema não tem nenhum."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a criação completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        config = ConfiguracaoAdmin(
            rf=ADMIN_RF,
            email=ADMIN_EMAIL,
            envio_de_email_habilitado=EMAIL_ENVIO_HABILITADO,
        )
        try:
            resultado = carregar_seed_admin(config, dry_run=bool(options["dry_run"]))
        # ObjectDoesNotExist: unidade ou cargo fora do banco. ValidationError do Django: e-mail em
        # uso. ValidationError do Pydantic: ADMIN_RF ou ADMIN_EMAIL fora do formato.
        except (ObjectDoesNotExist, ValidationError, PydanticValidationError) as exc:
            raise CommandError(f"falha na criação do admin inicial: {exc}") from exc
        mensagem = MENSAGENS[resultado.desfecho].format(rf=ADMIN_RF)
        if resultado.desfecho in ERROS:
            self.stderr.write(self.style.ERROR(mensagem))
            return
        self.stdout.write(self.style.SUCCESS(mensagem))
        if resultado.senha_sai_em_tela:
            self.stderr.write(self.style.ERROR(ALERTA_SENHA_EM_TELA))
