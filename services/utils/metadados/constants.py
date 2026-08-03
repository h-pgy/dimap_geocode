METADADOS_FILENAME = "metadados_dados.json"

# Constante única do formato: escrita E leitura passam por aqui. O JSON é lido por gente (é o
# primeiro lugar onde se olha quando "a busca está desatualizada") e, na fase 2, pelo Catalog —
# um literal solto do outro lado viraria ValueError longe da causa.
FORMATO_DATA = "%d-%m-%Y %H:%M:%S"

# O traceback existe para responder "por que não atualizou" sem o log do container; a cauda basta.
LIMITE_TRACEBACK = 4000
