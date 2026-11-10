# Deploy em produção — DIMAP GeoCoder

Levantamento feito sobre o código em `main` (commit `167a2c9`). Diz **o que falta no código**, **o
que a infraestrutura precisa ter**, **como configurar** e **como subir e manter** o sistema em
produção.

> **Resumo.** Hoje o projeto está pronto para **desenvolvimento**, não para produção. O
> `docker-compose.yml` monta o código por bind mount, roda `runserver` e compila o CSS em watch. Com
> `DJANGO_DEBUG=0`, do jeito que está, o sistema **sobe sem CSS, sem JS local e sem imagens**, porque
> nada serve os estáticos. Antes do primeiro deploy, os itens da **Parte 1** precisam virar código. Pelo
> §4 do CLAUDE.md, isso passa por uma SPEC (sugestão: `infraestrutura/006-deploy-producao`). A
> checagem das variáveis de ambiente perigosas é a SPEC `infraestrutura/005`.

---

## Parte 1 — O que falta no código (bloqueia o deploy)

Cada item diz o que existe hoje, por que bloqueia e o que fazer. Os trechos de código são **proposta
para a SPEC**, não implementação.

### 1.1 Servidor de aplicação

- **Hoje:** o `CMD` do `docker/Dockerfile.web` é `python manage.py runserver 0.0.0.0:8000`. O próprio
  Dockerfile avisa: *"troque por gunicorn/uvicorn no deploy"*. Nenhum servidor WSGI está nas
  dependências.
- **Fazer:**
  - `uv add gunicorn`.
  - Em produção, rodar o web com:
    ```bash
    gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --worker-class gthread \
        --workers 2 \
        --threads 4 \
        --timeout 150 \
        --access-logfile - \
        --error-logfile -
    ```
- **Por que esses números:**
  - **`gthread`**: as requests passam boa parte do tempo esperando o WFS e o WMS do GeoSampa. Threads
    atendem bem esse padrão sem multiplicar a memória.
  - **Poucos workers**: o `config/wsgi.py` aquece os catálogos (`aquecer_catalogos()`) **em cada
    processo**, e eles carregam os parquets em memória (o de endereços fiscais tem 37 MB comprimidos e
    ocupa bem mais como DataFrame). Cada worker é uma cópia. **Meça** com `docker stats` depois da
    subida antes de aumentar.
  - **`--timeout 150`**: o pior caso de uma chamada WFS é 30 s de timeout × 4 tentativas
    (`WFS_MAX_RETRIES=3`), mais as esperas entre elas. Ou se reduz `WFS_MAX_RETRIES` em produção, ou o
    timeout do gunicorn (e o `proxy_read_timeout` do nginx) precisa cobrir esse tempo.
  - **Sem `--preload`**: o aquecimento já acontece no import do `wsgi.py`. Com `--preload` ele rodaria
    no processo mestre e a memória seria compartilhada só em parte, porque a contagem de referências do
    Python suja as páginas copy-on-write. Não vale a complexidade.

### 1.2 Arquivos estáticos

- **Hoje:** não existe `STATIC_ROOT` e ninguém roda `collectstatic`. O Django só serve
  `STATICFILES_DIRS` com `DEBUG=1`. Com `DEBUG=0`, `output.css`, ícones, logotipos e ortofotos de
  fundo dão **404**.
- **Fazer**, por um dos dois caminhos abaixo.
  - **Opção A (recomendada, a mais simples): WhiteNoise.** O próprio processo Django serve os
    estáticos, sem volume compartilhado com o nginx.
    ```python
    # config/settings.py
    STATIC_ROOT = BASE_DIR / "staticfiles"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    # MIDDLEWARE: "whitenoise.middleware.WhiteNoiseMiddleware" logo depois do SecurityMiddleware
    ```
  - **Opção B: nginx serve `/static/`** a partir de um volume preenchido pelo `collectstatic`.
- **Atenção à ordem no entrypoint.** O `gerar_ortofotos_fundo` grava as imagens em
  `static/src/img/ortofotos_fundo/`, que está no `.gitignore` e por isso não vem na imagem. O
  `collectstatic` precisa rodar **depois** dele, senão as ortofotos ficam de fora. O
  `CompressedManifestStaticFilesStorage` também falha no `collectstatic` quando um CSS referencia
  arquivo inexistente. Rode `collectstatic` uma vez no build de teste para pegar isso cedo.
- **Persistência das ortofotos:** sem volume, cada container novo busca as ortofotos de novo no
  GeoSampa. Ou se monta um volume em `static/src/img/ortofotos_fundo/`, ou se geram as imagens no
  build da imagem (o build passa a depender do GeoSampa no ar).

### 1.3 Mídia (foto do perfil)

- **Hoje:** `Perfil.foto` é um `ImageField` (`upload_to="perfis/fotos/"`, `MEDIA_ROOT = BASE_DIR /
  "media"`). O `config/urls.py` só serve mídia com `DEBUG=1`. Em produção, as fotos não aparecem e,
  sem volume, **somem a cada recriação do container**.
- **Fazer:**
  - Usar um volume persistente em `/app/media`.
  - Servir `/media/` pelo nginx.
- **Decisão pendente:** servida pelo nginx, a foto fica **pública**: quem souber a URL a vê, sem
  login. Se isso não for aceitável, a foto precisa de uma rota Django protegida (por exemplo, o nginx
  com `X-Accel-Redirect`), e isso é escopo de SPEC.

### 1.4 Endurecimento do settings

O `config/settings.py` hoje tem defaults pensados para desenvolvimento:

| Item | Hoje | Risco | Fazer |
|---|---|---|---|
| `DJANGO_DEBUG` | default `True` | `.env` esquecido sobe em DEBUG e vaza traceback | default `False`, ou falhar no boot sem a variável |
| `DJANGO_SECRET_KEY` | default de dev | sessões forjáveis | falhar no boot com `DEBUG=0` e o valor default |
| `ASSINATURA_SEGREDO` | default de dev | selo de integridade forjável | idem |
| `DJANGO_ALLOWED_HOSTS` | default `["*"]` | host header poisoning; o `build_absolute_uri` usado no e-mail de acesso, na recuperação de senha e no QR das certidões confia no Host | definir no `.env` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | default `*.ngrok*.app` | origem de túnel de dev confiável em produção | definir no `.env` com a origem real |
| HTTPS atrás de proxy | ausente | `request.is_secure()` falso: links `http://` nos e-mails e no QR code | `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` |
| Cookies | ausente | cookie de sessão trafegando sem `Secure` | `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True` |
| HSTS | ausente | — | `SECURE_HSTS_SECONDS` (comece baixo, ex. `3600`, e suba depois) |
| `LOGGING` | ausente | com `DEBUG=0`, o Django manda erro 500 para `mail_admins`, e `ADMINS` está vazio: **o traceback se perde** | `LOGGING` com handler de console no nível `ERROR` para `django.request` (vai para o `docker logs`) |

Proposta: um bloco condicionado a `not DEBUG`, para não mexer no ambiente de dev.

```python
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_CONTENT_TYPE_NOSNIFF = True
```

Validação: `python manage.py check --deploy` deve sair sem avisos relevantes.

### 1.5 Compose de produção

- **Hoje:** o `docker-compose.yml` tem bind mount `.:/app` em `web`, `tailwind` e `daemon`, o `web`
  depende do serviço `tailwind` e o `db` publica a `5432` no host. A SPEC `ingestao_dados/007` (v4)
  deixou o *"deploy sem bind mount"* **fora de escopo**: é esta lacuna.
- **Fazer:** criar um `docker-compose.prod.yml` separado, sem tocar no de dev.

```yaml
name: dimap-geocode

services:
  db:
    image: postgis/postgis:17-3.5
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    # sem `ports`: o banco só é visível na rede interna do compose
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      retries: 10
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    env_file: .env
    environment:
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
    command: >
      gunicorn config.wsgi:application --bind 0.0.0.0:8000
      --worker-class gthread --workers 2 --threads 4 --timeout 150
      --access-logfile - --error-logfile -
    volumes:
      - dados:/app/data
      - midia:/app/media
      - ortofotos:/app/static/src/img/ortofotos_fundo
    ports:
      - "127.0.0.1:8000:8000"   # só o nginx do host enxerga
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  daemon:
    build:
      context: .
      dockerfile: docker/Dockerfile.daemon
    env_file: .env
    volumes:
      - dados:/app/data          # o mesmo volume do web: é por ele que o parquet novo chega
    restart: unless-stopped

volumes:
  pgdata:
  dados:
  midia:
  ortofotos:
```

- **Sem serviço `tailwind`.** O `Dockerfile.web` já assa o CSS minificado no estágio `css-build`.
- **Cuidado com o volume `dados`.** Um volume nomeado é preenchido com o conteúdo da imagem **só na
  primeira vez**, quando está vazio. Depois disso, parquets novos que cheguem por `git pull` e rebuild
  **não chegam** ao volume. O atualizador passa a ser só o daemon. Isso é o desejável, mas precisa
  estar combinado. Para forçar os dados da imagem: `docker compose run --rm web cp ...` ou recriar o
  volume.
- **Alternativa mais simples (não recomendada):** bind mount de `./data` do checkout git. O daemon
  passaria a escrever em arquivos versionados (`*.parquet`, `metadados_dados.json`), e cada `git
  pull` no servidor daria conflito.

### 1.6 Entrypoint

O `docker/entrypoint.sh` atual migra, sincroniza ações, roda seeds e gera ortofotos. Em produção:

- Com `DJANGO_AUTO_MIGRATE=0` (recomendado, ver 3.1), **o `sincronizar_acoes` também não roda**: ele
  está dentro do mesmo `if`. Portanto, a cada deploy que mexe em ações, ele tem de ser rodado à mão
  (ver Parte 5).
- Acrescentar `python manage.py collectstatic --noinput` **depois** do `gerar_ortofotos_fundo` (ver
  1.2).

### 1.7 Bibliotecas de front via CDN

- **Hoje:** os templates carregam do `unpkg.com`:
  - `htmx.org@2`, **sem versão exata**: um release novo do htmx 2.x entra em produção sem aviso;
  - `leaflet@1.9`, também sem patch fixo;
  - `@geoman-io/leaflet-geoman-free@2.20`.
- **Fazer:**
  - fixar versão exata (ex. `htmx.org@2.0.4`) e, de preferência, `integrity=` (SRI);
  - ou vendorizar os arquivos em `static/`.
- **Rede da prefeitura:** confirme que a rede dos usuários alcança o `unpkg.com`, o
  `*.basemaps.cartocdn.com` (tiles públicos) e o `maps.googleapis.com` (Street View). Proxies
  corporativos costumam bloquear CDN. Vendorizar elimina a dependência do unpkg.

### 1.8 Rotas de desenvolvimento expostas

- `/_teste/validacao/` (`apps/core/urls.py`) existe só para provar o middleware de validação. Em
  produção, deve ser removida ou condicionada a `DEBUG`.
- `/design_system/` é inofensiva, mas pública. Decidir se fica.
- O comando `servidores_ficticios` já recusa rodar com `DEBUG=0`. OK.

### 1.9 Healthcheck (desejável)

Não há rota de saúde. Uma `/saude/` que responde `200` sem tocar no GeoSampa, com um `SELECT 1` no
banco e conferindo que os catálogos estão aquecidos, serve ao `healthcheck` do compose e ao
monitoramento.

---

## Parte 2 — Infraestrutura

### 2.1 Servidor

- VM Linux com Docker Engine + Compose v2.
- **Memória:** reserve pelo menos 4 GB e meça. Os catálogos são carregados por worker (1.1), e o
  daemon carrega os parquets durante a carga diária.
- **Disco:**
  - imagem: ~1–2 GB com GDAL;
  - dados: ~40 MB hoje, mais ~156 MB do parquet de ITBI;
  - banco: cresce com o **acervo de documentos**. Os PDFs emitidos ficam no Postgres como `bytea`
    (`apps/documentos/models.py`), então o banco cresce a cada certidão.
- **Git LFS** instalado no servidor, se o deploy for por `git clone` (ver 4.1).

### 2.2 DNS e TLS

- Um nome interno, ex. `geocoder.dimap.<domínio>`.
- Certificado TLS: certificado institucional, ou Let's Encrypt se o nome for público.
- **HTTPS é obrigatório.** Há login, senha de uso único e cookie de sessão.

### 2.3 Proxy reverso (nginx no host)

```nginx
server {
    listen 443 ssl http2;
    server_name geocoder.dimap.exemplo.gov.br;

    ssl_certificate     /etc/ssl/certs/geocoder.pem;
    ssl_certificate_key /etc/ssl/private/geocoder.key;

    # Upload de foto do perfil e de PDF na conferência de documento.
    client_max_body_size 20m;

    location /media/ {
        alias /var/lib/docker/volumes/dimap-geocode_midia/_data/;   # ver 1.3 sobre privacidade
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 160s;   # acima do --timeout do gunicorn (1.1)
    }
}

server {
    listen 80;
    server_name geocoder.dimap.exemplo.gov.br;
    return 301 https://$host$request_uri;
}
```

`X-Forwarded-Proto` + `SECURE_PROXY_SSL_HEADER` (1.4) é o que faz o `build_absolute_uri` gerar
`https://` nos e-mails e no QR code das certidões. **Se isso falhar, o QR code de toda certidão
emitida aponta para `http://`, e o PDF já selado não se corrige.**

### 2.4 Saídas de rede

**Do servidor:**

| Destino | Quem usa | Porta |
|---|---|---|
| `wfs.geosampa.prefeitura.sp.gov.br` | web (geometrias) e daemon (cargas) | 443 |
| `wms.geosampa.prefeitura.sp.gov.br`, `raster.geosampa.prefeitura.sp.gov.br` | entrypoint (ortofotos de fundo), planta de localização das certidões | 443 / **80** |
| `prefeitura.sp.gov.br` | daemon (scraper de guias de ITBI) | 443 |
| `geocode.googleapis.com` / API do Google | geocodificação externa (se ligada) | 443 |
| servidor SMTP | e-mail (senha de uso único, recuperação) | 587 |
| `ghcr.io`, Docker Hub, PyPI, npm | **só no build** da imagem | 443 |

**Dos navegadores dos usuários:** `wms.geosampa…`, `raster.geosampa…`, `unpkg.com`,
`*.basemaps.cartocdn.com`, `maps.googleapis.com`.

> **Risco: conteúdo misto.** `WMS_RASTER_URL` tem default `http://raster.geosampa…`. Numa página
> servida em HTTPS, o navegador tenta fazer upgrade da imagem para `https://` ou a bloqueia. **Teste
> a ortofoto no domínio de produção.** Se `raster.geosampa` não responder em HTTPS, a camada de
> ortofoto some do mapa, e a saída é um proxy reverso do raster no próprio nginx.

---

## Parte 3 — Configuração (`.env` de produção)

O `.env` fica **só no servidor**, com permissão `600`, fora do git (já está no `.gitignore` e no
`.dockerignore`).

### 3.1 Obrigatórias

| Variável | Valor em produção | Observação |
|---|---|---|
| `DJANGO_DEBUG` | `0` | |
| `DJANGO_SECRET_KEY` | aleatório, ≥ 50 caracteres | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | `geocoder.dimap.exemplo.gov.br` | aceita lista separada por vírgula |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://geocoder.dimap.exemplo.gov.br` | com o esquema |
| `DJANGO_AUTO_MIGRATE` | `0` | migração é decisão humana (§4 do CLAUDE.md); ver 1.6 |
| `DJANGO_AUTO_SEED` | `0` | seeds rodam à mão na primeira subida (são idempotentes) |
| `POSTGRES_DB` / `POSTGRES_USER` | à escolha | |
| `POSTGRES_PASSWORD` | aleatória e forte | |
| `ASSINATURA_SEGREDO` | aleatório, ≥ 32 bytes | **ver alerta abaixo** |
| `ASSINATURA_ID_CHAVE` | `k1` | |
| `EMAIL_ENVIO_HABILITADO` | `1` | **ver alerta abaixo** |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORTA` | SMTP institucional ou Gmail | |
| `EMAIL_SMTP_USUARIO` / `EMAIL_SMTP_SENHA` | conta de serviço | com Gmail, é "senha de app" |
| `EMAIL_REMETENTE_NOME` | `DIMAP GeoCoder` | |
| `ENFORCE_PREFEITURA_EMAIL` | `1` | |
| `ADMIN_RF` | RF real do administrador | o default `0000000` não serve |
| `ADMIN_EMAIL` | e-mail institucional do administrador | sem ele o admin não é criado |

> **Alerta: `EMAIL_ENVIO_HABILITADO=0` em produção é falha de segurança.** Com o envio desligado, a
> senha de uso único **aparece na tela**. Quem digitar o RF do administrador no login recebe a senha
> dele. Teste o SMTP **antes** da primeira subida: `python manage.py enviar_email_teste`.

> **Alerta: `ASSINATURA_SEGREDO` é definitivo.** A conferência do selo
> (`services/utils/assinatura/conferencia.py`) usa **só o segredo atual**. O `id_chave` é gravado no
> envelope, mas ainda não há rotação. Trocar o segredo depois de emitir certidões faz **todos os
> documentos já emitidos aparecerem como VIOLADOS** na conferência por arquivo. Defina o segredo
> antes da primeira emissão, guarde-o num cofre de senhas e não o troque. Rotação de chave é tema de
> SPEC futura.

### 3.2 Opcionais

| Variável | Quando definir |
|---|---|
| `GOOGLE_GEOCODING_TOKEN` | para ligar a geocodificação externa. Vazio desliga |
| `GOOGLE_MAPS_BROWSER_KEY` | para o Street View. **Restrinja no Google Console** por referrer HTTP (o domínio de produção) e por API (Maps JavaScript API): a chave vai no HTML |
| `DTIME_ATUALIZACAO_ARQUIVOS` | horário do daemon. Default `03:00` |
| `WFS_MAX_RETRIES`, `WFS_REQUEST_TIMEOUT_SECONDS` | se for reduzir o pior caso de request (1.1) |
| `WFS_VERBOSE` | default `True`: loga **toda** requisição WFS. Em produção, `0` reduz ruído no log |
| `DOCUMENTO_UNIDADE`, `DOCUMENTO_ENDERECO`, `DOCUMENTO_LOGO_*` | se o papel timbrado não for o padrão |
| `MAP_FUNDO_PONTOS` | só se quiser outro recorte de ortofotos de fundo |

Variáveis que **não** vão para o `.env` de produção: `DB_PORT` e `WEB_PORT` (o compose de produção
não publica o banco e liga o web em `127.0.0.1`).

---

## Parte 4 — Primeira subida

Pré-requisito: Parte 1 implementada e mesclada em `main`.

### 4.1 Código e dados

```bash
sudo apt install git git-lfs
git lfs install
git clone https://github.com/h-pgy/dimap_geocode.git /opt/dimap_geocode
cd /opt/dimap_geocode
git lfs pull     # traz o parquet de ITBI (~156 MB); sem isso só fica o ponteiro de 134 bytes
```

Hoje nenhuma rota lê o parquet de ITBI em tempo de request, e o daemon o regenera na primeira
carga. Mesmo assim, não é bom deixar só o ponteiro de 134 bytes, com cara de parquet, na imagem.

### 4.2 Segredos

```bash
cp .env.example .env
chmod 600 .env
# editar segundo a Parte 3; gerar os segredos com `secrets.token_urlsafe`
```

### 4.3 Build e banco

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d db
```

### 4.4 Migração, catálogo de ações e seeds (manual)

```bash
C="docker compose -f docker-compose.prod.yml run --rm web"

$C python manage.py check --deploy
$C python manage.py migrate --noinput
$C python manage.py sincronizar_acoes
$C python manage.py enviar_email_teste            # confirma o SMTP antes de criar o admin
$C sh docker/run_seeds.sh                          # unidades → cargos → tipos de impedimento → admin
```

As seeds pulam o que já existe, e o `seed_admin` só cria o administrador se o banco não tiver
nenhum superusuário.

### 4.5 Subir a aplicação

```bash
docker compose -f docker-compose.prod.yml up -d web daemon
docker compose -f docker-compose.prod.yml logs -f web
```

Nos logs, confirme:

- as ortofotos de fundo foram geradas (ou o aviso de GeoSampa indisponível; nesse caso, rode
  `gerar_ortofotos_fundo` depois);
- o `collectstatic` rodou;
- o gunicorn subiu os workers sem erro de aquecimento de catálogo.

### 4.6 nginx e TLS

Instalar a configuração da seção 2.3, `nginx -t` e `systemctl reload nginx`.

### 4.7 Primeiro acesso

Abrir o domínio, entrar com o `ADMIN_RF` e pedir a senha de uso único, que chega no `ADMIN_EMAIL`.
Depois, definir a senha definitiva.

---

## Parte 5 — Deploys seguintes

```bash
cd /opt/dimap_geocode
git pull
git lfs pull
docker compose -f docker-compose.prod.yml build

# Só se o deploy trouxer migração ou mexer em ações: rode, revise a saída e só então siga.
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --plan
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml run --rm web python manage.py sincronizar_acoes

docker compose -f docker-compose.prod.yml up -d web daemon
```

- **Antes de migrar, faça backup do banco** (Parte 7).
- **`sincronizar_acoes` a cada deploy que inclui, remove ou altera uma ação.** É ele que projeta o
  catálogo de ações em código no banco, e com `DJANGO_AUTO_MIGRATE=0` o entrypoint não o roda (1.6).
  Na dúvida, rode: ele é seguro de repetir.
- Seed nova (cargo, unidade, tipo de impedimento): rodar o `seed_*` correspondente.
- A troca dos containers derruba as requests em andamento por alguns segundos. Para dezenas de
  usuários internos, uma janela curta resolve; não vale montar blue/green.

---

## Parte 6 — Dados territoriais (parquets de `data/`)

- O web **só lê** os parquets. Quem atualiza é o daemon, todo dia em `DTIME_ATUALIZACAO_ARQUIVOS`,
  rodando `atualizar_dados`: segmentos → nomes → endereços fiscais → variações → títulos → ITBI.
- A escrita é atômica. Uma falha no meio do pipeline mantém o parquet anterior, e o daemon segue
  agendado.
- **O web enxerga o dado novo sem restart**, pelo TTL dos catálogos (`ttl_cached_property`): 24 h
  para logradouros e codlog, 1 h para contribuinte. Para valer na hora:
  `docker compose -f docker-compose.prod.yml restart web`.
- Carga manual, sob demanda:
  ```bash
  docker compose -f docker-compose.prod.yml exec daemon python manage.py atualizar_dados
  ```
- Para acompanhar, veja `data/metadados_dados.json` (data, contagem e erro de cada carga) e os logs
  do daemon.
- Lembrete do volume `dados` (1.5): depois da primeira subida, os parquets versionados no git **não
  chegam mais** ao volume. A fonte da verdade em produção passa a ser o daemon.

---

## Parte 7 — Backup e restauração

| O quê | Onde | Criticidade | Como |
|---|---|---|---|
| Banco (servidores, competências, **registro de execução dos atos**, **acervo de documentos emitidos**) | volume `pgdata` | **alta**: registro de ato administrativo e documento oficial não se regeneram | `pg_dump` diário |
| Fotos de perfil | volume `midia` | média | cópia do volume |
| `.env` (sobretudo `ASSINATURA_SEGREDO`) | servidor | **alta**: perder o segredo invalida a conferência de todos os documentos | cofre de senhas, fora do servidor |
| Parquets | volume `dados` | baixa: o daemon regenera | — |
| Ortofotos de fundo | volume `ortofotos` | baixa: regeneráveis | — |

```bash
# backup (cron diário no host)
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > /backup/dimap_$(date +%F).dump

# restauração
docker compose -f docker-compose.prod.yml exec -T db \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean < /backup/dimap_AAAA-MM-DD.dump
```

Guarde as cópias fora da VM, com retenção definida, e **teste a restauração** pelo menos uma vez
antes de liberar o sistema.

---

## Parte 8 — Validação pós-deploy

- [ ] `https://<domínio>/` abre **com estilo** (CSS e ícones carregam; nada de 404 em `/static/` no
      DevTools).
- [ ] `http://` redireciona para `https://`.
- [ ] Ortofoto e mapa base aparecem no mapa, sem erro de conteúdo misto no console.
- [ ] Busca por nome de logradouro, endereço com número e número de contribuinte desenha linha, ponto
      e polígono.
- [ ] Login do admin: a senha de uso único **chega por e-mail** e **não aparece na tela**.
- [ ] Recuperação de senha: o link do e-mail começa com `https://<domínio>`.
- [ ] Emitir uma certidão de lançamento:
  - [ ] o PDF abre;
  - [ ] o QR code aponta para `https://<domínio>/…`;
  - [ ] a conferência pública (por código e por upload do arquivo) dá **ÍNTEGRO**.
- [ ] O registro de execução mostra a emissão (quem, perfil, entidade, quando).
- [ ] Foto de perfil: o upload funciona e a foto aparece depois de `restart web` (volume persistente).
- [ ] Erro 500 forçado aparece no `docker logs web` com traceback (LOGGING configurado).
- [ ] `/_teste/validacao/` não responde em produção.
- [ ] `docker compose … logs daemon` mostra *"próxima atualização em …h"*.
- [ ] O banco **não** responde de fora da VM na porta 5432.
- [ ] `python manage.py check --deploy` limpo.
- [ ] Backup gerado e restauração testada.

---

## Parte 9 — Riscos e decisões em aberto

1. **Foto de perfil pública via nginx** (1.3): aceitar ou proteger por rota.
2. **Ortofoto em HTTP** (2.4): testar e, se preciso, montar proxy do raster.
3. **Memória dos catálogos por worker** (1.1): medir e dimensionar a VM.
4. **CDN externo em rede corporativa** (1.7): fixar versões e, de preferência, vendorizar.
5. **SMTP:** o `.env.example` usa Gmail. Para documento oficial e e-mail de acesso de servidor
   público, um SMTP institucional é mais adequado, sujeito à política da SF.
6. **Rotação do segredo de assinatura** não existe (3.1): o segredo é definitivo até haver SPEC.
7. **Crescimento do banco** com PDFs em `bytea`: aceitável na escala atual, mas monitore o tamanho do
   `pgdata`.
8. **Sessão:** o padrão do Django é de 2 semanas. Para estação compartilhada, avalie
   `SESSION_COOKIE_AGE` menor e `SESSION_EXPIRE_AT_BROWSER_CLOSE`.

### Ordem sugerida

1. SPEC `infraestrutura/005` (checagem do ambiente com `PROD=1`) e SPEC `infraestrutura/006`
   cobrindo 1.1–1.9, aprovadas e implementadas.
2. Provisionar a VM, DNS, TLS e liberar as saídas de rede (Parte 2).
3. Montar o `.env` e testar o SMTP (Parte 3).
4. Primeira subida (Parte 4) em **homologação**, rodar a Parte 8 inteira, depois produção.
