VERSAO_ENVELOPE = 1
# O que a ação não pode sobrescrever. Um extra chamado `autor` faria o documento mentir sobre quem
# praticou o ato — e mentiria com selo válido, porque o selo cobre o que estiver escrito.
CHAVES_RESERVADAS = frozenset(
    {"versao", "codigo", "acao", "operacao", "autor", "alvo", "emitido_em", "campos_publicos"}
)
# 12 caracteres num alfabeto de 32 dão ~60 bits: a rota de conferência é aberta (SPEC 008), e código
# adivinhável permitiria varrer o acervo inteiro.
TAMANHO_CODIGO = 12
# Base32 sem as letras que se confundem com dígito na leitura de um papel: I, L, O e U fora.
ALFABETO_CODIGO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Rota de UMA letra: cada caractere a mais no endereço engorda a matriz do QR, e o quadro compacto
# não tem milímetro sobrando.
ROTA_CONFERENCIA = "d"
# "eletronicamente", e não "digitalmente": assinatura digital tem sentido técnico próprio no Brasil
# (certificado ICP-Brasil), e o selo daqui não é isso.
CHAMADA_SELO = "Assinado eletronicamente"
MESES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
