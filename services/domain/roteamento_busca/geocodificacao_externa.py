from .endereco import EnderecoIdentifier
from .models import GeocodificacaoExternaParse


class GeocodificacaoExternaIdentifier:
    def __init__(self, endereco: EnderecoIdentifier | None = None) -> None:
        self._endereco = endereco or EnderecoIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> GeocodificacaoExternaParse | None:
        # a regra do endereço por nome já deixa de fora codlog, sem número e "s/n"
        if self._endereco(texto, finished_typing) is None:
            return None
        return GeocodificacaoExternaParse(texto=texto.strip())
