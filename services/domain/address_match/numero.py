import re

MARCADOR_NUMERO = r"(?:n(?:[º°o]|ro|[uú]m(?:ero)?)?\.?|#)"
SO_MARCADOR = re.compile(rf"^{MARCADOR_NUMERO}$", re.IGNORECASE)
NUMERO_IMOVEL = re.compile(rf"{MARCADOR_NUMERO}?\s*(\d+)", re.IGNORECASE)

# Cadastro fiscal: 's/n', 'S/N', 'sn', 's.n.', 's/nº', 'sem número' — todas as grafias de
# "sem número" aceitas antes da normalização (a canonicalização em si é feita à parte,
# em services.utils.normalization, sobre o texto já normalizado).
SEM_NUMERO = re.compile(r"^(?:s[./]?n[º°o.]?|sem\s+n[uú]mero)$", re.IGNORECASE)
# Ramo numérico espelha NUMERO_IMOVEL: match de PREFIXO, SEM âncora/fullmatch — só acrescenta
# o sufixo de unidade ao grupo. É o prefixo que garante o SUPERCONJUNTO do estrito: todo token
# que parse_numero_imovel aceita ("10.", "10 apto 5", "10, casa 2", "1.578") este também
# aceita. Com fullmatch, esses tokens seriam rejeitados e — como este leitor é o critério de
# split dos localizadores — a entrada deixaria de gerar QUALQUER candidato de endereço
# (regressão sobre o comportamento atual).
NUMERO_PORTA = re.compile(rf"{MARCADOR_NUMERO}?\s*(\d+[\w\-]*)", re.IGNORECASE)


def parse_numero_imovel(token: str) -> int | None:
    """Extrai o número de imóvel de um token, tolerando marcadores e sufixos de unidade."""
    m = NUMERO_IMOVEL.match(token.strip())
    return int(m.group(1)) if m else None


def eh_so_marcador(token: str) -> bool:
    """True se o token for exclusivamente um marcador de número (ex.: 'nº', 'nro')."""
    return SO_MARCADOR.fullmatch(token.strip()) is not None


def parse_numero_porta(token: str) -> str | None:
    """Número de porta do cadastro fiscal: '10', '10A', '10-A', 's/n', 'sem número'.

    Devolve o número BRUTO validado — dígitos + sufixo de unidade, sem o marcador
    ('nº 10A' -> '10A'; '10 apto 5' -> '10'); grafia de "sem número" volta como digitada.
    Sem normalizar: a chave de match (chave_numero_porta) é aplicada depois, no parse.
    Superconjunto de parse_numero_imovel: tudo que o estrito aceita, este aceita.
    """
    limpo = token.strip()
    if SEM_NUMERO.fullmatch(limpo):
        return limpo
    m = NUMERO_PORTA.match(limpo)
    return m.group(1) if m else None
