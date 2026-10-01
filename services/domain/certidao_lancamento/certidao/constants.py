from ..models import SentidoDespacho, TipoDespacho

# O texto é o modelo de declaração da DIMAP, transcrito: nenhuma frase é redigida pelo sistema.
TITULO = (
    "Declaração de Existência/Inexistência de Lançamento Fiscal e Inscrição no Cadastro "
    "Imobiliário Fiscal – IPTU"
)
# A abertura sai do sentido, e o corpo, do tipo: "DEFERIDA" não se escreve em cada texto.
ABERTURA_DO_DESPACHO: dict[SentidoDespacho, str] = {
    SentidoDespacho.DEFERIDO: "Solicitação DEFERIDA.",
    SentidoDespacho.INDEFERIDO: "Solicitação INDEFERIDA.",
}
BASE_DESPACHO = "Com base nas informações presentes no processo, declara-se que"
CORPO_DO_DESPACHO: dict[TipoDespacho, str] = {
    TipoDespacho.POSSUI_LANCAMENTO: (
        "o imóvel possui lançamento do Imposto Predial e Territorial Urbano – IPTU – pelo contribuinte "
        "número {sql}."
    ),
    TipoDespacho.LANCAMENTO_EM_MAIOR_AREA: (
        "o imóvel possui lançamento do Imposto Predial e Territorial Urbano – IPTU, em maior área, pelo "
        "contribuinte número {sql}."
    ),
    TipoDespacho.LANCAMENTO_PARCIAL: (
        "o imóvel possui lançamento parcial do Imposto Predial e Territorial Urbano – IPTU pelo "
        "contribuinte número {sql}."
    ),
    TipoDespacho.IMOVEL_NAO_LOCALIZADO: (
        "não foi possível a localização do imóvel, já que as informações constantes no processo não são "
        "suficientes para a sua identificação inequívoca."
    ),
    TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO: (
        "não é possível atender ao pedido, pois equivale a Pedido de Acesso à Informação, nos termos do "
        "Decreto nº 53.623/2012."
    ),
}
RESSALVA_PADRAO = (
    "Ressalta-se que a análise tem como base somente a situação factual do imóvel. Assim sendo, o "
    "presente despacho não se destina a confirmar a correspondência do imóvel com o título aquisitivo "
    "ou documento equivalente, bem como sua regularidade."
)
VALIDADE = (
    "As informações prestadas nos termos deste despacho serão válidas por 90 (noventa) dias, a contar "
    "da data de intimação do solicitante, conforme definido no artigo 3º da Ordem Interna SF/SUREM "
    "nº 07, de 29 de Outubro de 2018."
)
LARGURA_PLANTA_MM = 150.0
