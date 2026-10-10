# O envelope inteiro cabe numa chave do dicionário `/Info` do PDF.
CHAVE_METADADO = "/DimapAssinatura"
CHAVE_TAG = "tag"
ALGORITMO = "HMAC-SHA256"
TAMANHO_TAG = 64
# Sorteado uma vez, e não `"0" * 64`: a marca é localizada por busca de bytes, e uma sequência de
# 64 caracteres iguais é o que um documento pode imprimir por acaso. Hexadecimal porque o `pypdf`
# grava dígito e letra `a-f` em claro, e escapa pontuação em octal.
PLACEHOLDER = "43d4cfd0b213cd911038ad8af66fdcb4a2bebee13fae37fa269e4b56dac7ca5f"
