import re

OUTPUT_FILENAME: str = "itbi_guias_pagas.parquet"

# O dicionário único de saída, na ordem do parquet. Chave = cabeçalho legível da planilha; o
# casamento normaliza os dois lados (§6.1), porque a fonte tem acento, parênteses e caixa
# instável entre anos. Grafia divergente num ano aparece em `colunas_desconhecidas_por_ano`.
MAPA_COLUNAS: dict[str, str] = {
    "N° do Cadastro (SQL)": "sql_num",
    "Nome do Logradouro": "logradouro_nome",
    "Número": "numero_porta",
    "Complemento": "complemento_endereco",
    "Referência": "referencia_endereco",
    "CEP": "cep",
    "Natureza de Transação": "natureza_transacao",
    "Valor de Transação (declarado pelo contribuinte)": "valor_transacao_declarado",
    "Data de Transação": "data_transacao",
    "Valor Venal de Referência": "valor_venal_de_referencia",
    "Proporção Transmitida (%)": "percentual_transmitido",
    "Valor Venal de Referência (proporcional)": "valor_venal_de_referencia_proporcional",
    "Base de Cálculo adotada": "valor_adotado_base_de_calculo",
    "Tipo de Financiamento": "financiamento_tipo",
    "Valor Financiado": "financiamento_valor",
    "Cartório de Registro": "cartorio",
    "Matrícula do Imóvel": "matricula",
    "Situação do SQL": "sql_situacao",
    "Área do Terreno (m2)": "area_terreno",
    "Testada (m)": "testada",
    "Fração Ideal": "fracao_ideal",
    "Área Construída (m2)": "area_construida",
    "Uso (IPTU)": "uso",
    "Descrição do uso (IPTU)": "uso_desc",
    "Padrão (IPTU)": "padrao_construtivo",
    "Descrição do padrão (IPTU)": "padrao_construtivo_desc",
    "ACC (IPTU)": "ano_construcao_corrigido",
}

# O que NÃO é texto. Conversão SEMPRE com errors="raise": com coerce, valor que o parser
# não entendeu viraria nulo e ficaria indistinguível de célula vazia.
COLUNAS_NUMERICAS: tuple[str, ...] = (
    "valor_transacao_declarado",
    "valor_venal_de_referencia",
    "percentual_transmitido",
    "valor_venal_de_referencia_proporcional",
    "valor_adotado_base_de_calculo",
    "financiamento_valor",
    "area_terreno",
    "testada",
    "fracao_ideal",
    "area_construida",
    "ano_construcao_corrigido",
)
COLUNAS_DATA: tuple[str, ...] = ("data_transacao",)

# O que sobra é texto — e é declarado, não deixado ao acaso: a mesma coluna vem número num ano
# e texto em outro (o número de porta "O4073" de 2006), e sem o cast o pyarrow infere int64 pelas
# primeiras linhas e derruba o ano na escrita do parquet.
COLUNAS_TEXTO: tuple[str, ...] = tuple(
    saida
    for saida in MAPA_COLUNAS.values()
    if saida not in COLUNAS_NUMERICAS and saida not in COLUNAS_DATA
)

# Acima disto o ano cai inteiro: perder muita linha não é linha ruim, é esquema que mudou.
TETO_LINHAS_DESCARTADAS: float = 0.05
LIMITE_DESCARTES_REPORTADOS: int = 20
# O índice do pandas conta a partir de 0 e o cabeçalho ocupa a linha 1 da planilha.
OFFSET_LINHA_EXCEL: int = 2

COLUNA_ANO: str = "ano"
COLUNA_MES: str = "mes"
COLUNA_FINANCIAMENTO_TIPO: str = "financiamento_tipo"
COLUNA_IS_FINANCIAMENTO: str = "is_financiamento"

MESES: tuple[str, ...] = (
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
)
# Sobre o texto JÁ normalizado: normalize_text colapsa "-", "_" e "/" num espaço.
# O ano capturado aqui só reconhece a aba — a coluna `ano` vem sempre do portal.
PADRAO_ABA = re.compile(rf"^({'|'.join(MESES)}) (\d{{4}})$")

# Duas pastas: o que o portal entregou, e o último resultado BOM de cada ano.
PASTA_ORIGINAIS: str = "itbi_originais"
PASTA_PARSEADOS: str = "itbi_parseados"

# O nome do arquivo é o contrato entre as etapas: cada uma grava o ano nele e a seguinte
# lê o ano de lá — e por isso não precisa conhecer nem o portal nem a etapa anterior.
NOME_XLSX: str = "itbi_{ano}.xlsx"
NOME_PARQUET: str = "itbi_{ano}.parquet"
PADRAO_NOME_XLSX = re.compile(r"^itbi_(\d{4})\.xlsx$")
PADRAO_NOME_PARQUET = re.compile(r"^itbi_(\d{4})\.parquet$")
