from services.utils.http import HttpRetryPolicy

URL_PAGINA_ITBI: str = "https://prefeitura.sp.gov.br/web/fazenda/w/acesso_a_informacao/31501"

# A varredura é DENTRO desta seção: a página tem outras listas de publicação, e o <li> vizinho
# tem a mesma cara. Sem `id` nem HTML semântico, é o único âncora que o CMS oferece.
SELETOR_SECAO: str = "section.psp-agencies-content"

SUFIXO_PLANILHA: str = ".xlsx"

# A política é da ITBI (valores); o laço que a obedece é de services/utils/http.
RETRY_ITBI: HttpRetryPolicy = HttpRetryPolicy(
    request_timeout_seconds=60.0,  # são arquivos, não JSON de página
    status_para_retry=(429, 500, 502, 503, 504),
)

# Identificar o cliente é cortesia com um portal público — e alguns CMS recusam UA vazio.
USER_AGENT_ITBI: str = "DIMAP GeoCoder (uso interno PMSP)"

TAMANHO_CHUNK: int = 1024 * 256
