class ProvedorIndisponivelError(Exception):
    """O provedor não respondeu dentro do contrato: rede, cota, acesso negado ou corpo inesperado."""


class SemResultadoAceitoError(Exception):
    """O provedor respondeu, mas nenhum resultado cabe na política."""


class ProvedorDesconhecidoError(Exception):
    """O ambiente nomeia um provedor que não está inscrito na factory."""
