from argparse import ArgumentParser
from getpass import getpass

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError
from pydantic import SecretStr

from apps.user_admin.schemas import NovoSuperusuario
from apps.user_admin.superusuario import criar_superusuario

UNIDADE_PADRAO = "DIMAP"
CARGO_BASE_PADRAO = "AFTM"
CARGO_COMISSAO_PADRAO = "Diretor de Divisão"


class Command(BaseCommand):
    help = "Cria um superusuário com lotação, cargos e, opcionalmente, titularidade da unidade."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--rf", required=True)
        parser.add_argument("--nome", required=True)
        parser.add_argument("--sobrenome", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--unidade", default=UNIDADE_PADRAO, help="sigla da unidade de lotação.")
        parser.add_argument("--cargo-base", default=CARGO_BASE_PADRAO, help="sigla do cargo base.")
        parser.add_argument("--cargo-comissao", default=CARGO_COMISSAO_PADRAO, help="nome do cargo em comissão.")
        parser.add_argument("--titular", action="store_true", help="marca como titular da unidade.")

    def handle(self, *args: object, **options: object) -> None:
        # A senha nunca vem por argumento: linha de comando fica no histórico do shell.
        senha = SecretStr(getpass("Senha: "))
        try:
            perfil = criar_superusuario(_dto(options), senha)
        except (ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(f"superusuário não criado: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"superusuário {perfil.rf} criado."))


def _dto(options: dict[str, object]) -> NovoSuperusuario:
    return NovoSuperusuario.model_validate(
        {
            "rf": options["rf"],
            "nome": options["nome"],
            "sobrenome": options["sobrenome"],
            "email": options["email"],
            "unidade_sigla": options["unidade"],
            "cargo_base_sigla": options["cargo_base"],
            "cargo_comissao_nome": options["cargo_comissao"],
            "e_titular": options["titular"],
        }
    )
