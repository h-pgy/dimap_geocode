class ClienteGeocodificacaoError(Exception):
    """Raiz: para fora de um cliente de provedor não sai exceção do requests nem do utilitário HTTP."""


class TransporteError(ClienteGeocodificacaoError):
    """Rede ou HTTP falharam — status de erro do provedor incluído — depois de esgotada a política de retry."""


class RespostaInvalidaError(ClienteGeocodificacaoError):
    """O corpo não é o contrato espelhado nos models do provedor."""
