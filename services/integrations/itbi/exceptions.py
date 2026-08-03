class ItbiIntegrationError(Exception):
    """Raiz dos erros da integração: para fora deste pacote não sai exceção de `requests`."""


class ItbiPaginaError(ItbiIntegrationError):
    """Levantada quando a página do portal não pôde ser lida."""


class ItbiEstruturaInesperadaError(ItbiIntegrationError):
    """Levantada quando a página não tem a estrutura esperada — o portal mudou."""


class ItbiDownloadError(ItbiIntegrationError):
    """Levantada quando a planilha de um ano não pôde ser baixada."""
