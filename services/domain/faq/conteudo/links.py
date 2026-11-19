from urllib.parse import urlsplit, urlunsplit

from .models import LinkDoSistema, LinkExterno


def resolver_destino(
    url: str, dominios_do_sistema: frozenset[str]
) -> LinkDoSistema | LinkExterno:
    partes = urlsplit(url.strip())
    if not partes.scheme and not partes.netloc:
        return LinkDoSistema(caminho=partes.geturl())
    if partes.hostname in dominios_do_sistema:
        # O domínio é do ambiente, não do link: sobra o caminho, que vale em qualquer ambiente.
        return LinkDoSistema(
            caminho=urlunsplit(
                ("", "", partes.path or "/", partes.query, partes.fragment)
            ),
        )
    return LinkExterno(url=url.strip())  # type: ignore[arg-type]


def destino_gravado(valor: str) -> LinkDoSistema | LinkExterno:
    # O gravado já diz o tipo: o do sistema foi reduzido ao caminho na entrada.
    if valor.startswith("/"):
        return LinkDoSistema(caminho=valor)
    return LinkExterno(url=valor)  # type: ignore[arg-type]
