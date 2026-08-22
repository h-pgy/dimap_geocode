# Cliente de e-mail não tem Tailwind, daisyUI, var() nem folha confiável: cada declaração viaja
# colada ao elemento. Chave = peça; valor = o atributo style inteiro, com o token de origem anotado.
TEMA_EMAIL: dict[str, str] = {
    "fundo": "background:#E3EFF5;padding:32px 12px;",  # base-200 — a água clara
    # O gelo fosco vira placa sólida: blur não existe em e-mail.
    # Roboto costuma ser bloqueada como webfont; o stack cai para Arial.
    "placa": (
        "background:#FFFFFF;border:1px solid #CFE2EB;border-radius:16px;"
        "font-family:Roboto,'Helvetica Neue',Arial,sans-serif;"
    ),
    "faixa": "background:#0096C7;border-radius:16px 16px 0 0;padding:20px 28px;",  # agua-600
    "corpo": "padding:28px;",
    "titulo": "margin:0 0 16px;color:#5E412F;font-size:24px;font-weight:700;",  # madeira-700
    "subtitulo": "margin:24px 0 8px;color:#1B263B;font-size:18px;font-weight:700;",  # rocha-900
    "paragrafo": "margin:0 0 12px;color:#1B263B;font-size:15px;line-height:1.6;",  # rocha-900
    # O .card-well sem a sombra interna, que o cliente ignora.
    "poco": "background:#F2F8FB;border:1px solid #CFE2EB;border-radius:12px;padding:16px;",
    "overline": "color:#415A77;font-size:11px;text-transform:uppercase;letter-spacing:.14em;",  # rocha-700
    "valor": "color:#0077B6;font-size:17px;",  # agua-700
    # Peça própria, e não composição com "valor": um elemento só tem UM atributo style.
    "valor_mono": "color:#0077B6;font-size:17px;font-family:'Roboto Mono',Consolas,monospace;",
    "celula_cabecalho": (
        "padding:8px 12px;border-bottom:1px solid #CFE2EB;color:#415A77;"
        "font-size:11px;text-transform:uppercase;letter-spacing:.14em;text-align:left;"
    ),
    "celula": "padding:8px 12px;border-bottom:1px solid #E3EFF5;color:#1B263B;font-size:14px;",
    # Sem cor: a imagem só precisa não estourar os 600px da placa nem ganhar borda do cliente.
    "imagem": "display:block;max-width:100%;border:0;",
    # O .btn-onsen sem gradiente: fundo chapado agua-400, tinta agua-800.
    "botao": (
        "display:inline-block;background:#48CAE4;color:#023E8A;border-radius:8px;"
        "font-weight:700;text-decoration:none;padding:12px 24px;"
    ),
    "divisor": "border:0;border-top:1px solid #CFE2EB;margin:24px 0;",  # base-300
    # A fileira, colada ao rótulo do poço acima dela.
    "otp_fileira": "margin-top:10px;",
    # A caixa: o poço do sistema com a tinta do valor monoespaçado, em largura fixa para as caixas
    # saírem todas iguais — dígito estreito e dígito largo ocupam o mesmo espaço.
    "otp_caixa": (
        # Branco sobre o poço (que é base-100): a caixa precisa se destacar do fundo em que está.
        "width:40px;background:#FFFFFF;border:1px solid #CFE2EB;border-radius:8px;"  # base-300
        "padding:10px 0;color:#0077B6;font-size:22px;font-weight:700;"  # agua-700
        "font-family:'Roboto Mono',Consolas,monospace;text-align:center;"
    ),
    # A faixa é o único lugar do e-mail com tinta clara sobre fundo escuro.
    "marca_selo": (
        "background:#FFFFFF;border-radius:8px;color:#0096C7;font-size:18px;"
        "font-weight:900;text-align:center;height:32px;"
    ),
    "marca_nome": "padding-left:12px;color:#FFFFFF;font-size:15px;font-weight:700;",
    "rodape": "padding:0 28px 24px;color:#5B7290;font-size:13px;",  # rocha-600
}
