---
spec: infraestrutura/006
versao: v2
atualizado_em: 2026-11-19
testes_tdd: false
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: o teste dos arquivos de vendor é pulado quando FRONT_VENDOR_DIR não existe, porque a imagem do web não tem pytest.
---

# SPEC infraestrutura/006 — Bibliotecas de front-end servidas pelo próprio sistema

## 1 · User story

**Requisito não-funcional**: nenhuma biblioteca, folha de estilo ou fonte de terceiros é buscada na
rede em runtime. Tudo vem do `npm` com versão exata, entra na imagem no build e é servido pelo
próprio Django.

## 2 · Condições de pronto

- [x] Nenhuma página da aplicação busca script, folha ou fonte fora do próprio servidor. Com o host sem
      acesso a `unpkg.com`, `cdn.jsdelivr.net` e `fonts.googleapis.com`, o mapa, a bancada de desenho,
      o HTMX e a tipografia funcionam. Serviços de dados (WMS do GeoSampa, Street View) seguem
      externos.
- [x] A interface se comporta e renderiza **igual** à servida pelo CDN: mapa, ícones de marcador do
      Leaflet, edição do Geoman, `responseHandling` do HTMX e os pesos de Roboto e Roboto Mono.
- [x] Toda dependência do `package.json` tem versão exata, sem `^` nem `~`. Atualizar qualquer uma é
      uma mudança no `package.json` e no `package-lock.json`, visível no diff.
- [x] As bibliotecas chegam ao `web` em desenvolvimento e em produção pelo mesmo caminho, e nada delas
      é versionado no repositório nem aparece no `git status`.
- [x] Imagem montada com dependência que não se instala ou arquivo de biblioteca que não existe falha
      no `docker compose build`, não em runtime.
- [x] O styleguide (`/design_system`) também não busca nada fora do servidor.

## 3 · Domínio

Esta SPEC não introduz domínio. Ela consome o estágio `css-deps` de
[infraestrutura/004](004-build-css-compilado.md), o único `npm ci` do projeto, e faz a ele uma pergunta:
além do compilador de CSS, o mesmo `node_modules` também entrega os arquivos já distribuídos de cada
biblioteca. O artefato desta iteração é `/opt/vendor` na imagem do `web`, servido sob `static/vendor/`.

| Biblioteca | Pacote npm | Versão |
|---|---|---|
| HTMX | `htmx.org` | 2.0.11 |
| Leaflet | `leaflet` | 1.9.4 |
| Leaflet-Geoman | `@geoman-io/leaflet-geoman-free` | 2.20.8 |
| Roboto | `@fontsource/roboto` | 5.3.0 |
| Roboto Mono | `@fontsource/roboto-mono` | 5.3.0 |
| Tailwind CLI | `@tailwindcss/cli`, `tailwindcss` | 4.3.3 |
| daisyUI | `daisyui` | 5.7.4 |

As versões das três bibliotecas de JS são as que o `unpkg` resolve hoje para `htmx.org@2`,
`leaflet@1.9` e `leaflet-geoman-free@2.20`. As do Tailwind são as que o `package-lock.json` já trava.

## 4 · Fora de escopo

- Os mocks de SPEC e os das skills, que seguem em CDN para desenhar peça que ainda não existe: skill
  `mock`.
- `collectstatic`, servidor de estáticos e cache-busting de produção: SPEC de deploy, sem dono ainda.
- Auditoria periódica de vulnerabilidade das dependências (`npm audit`): sem dono ainda.

## 5 · Peças de referência a compor

- `@docker/Dockerfile.web` → estágio `css-deps`: `npm ci` sobre o lock, com `node_modules` em `/opt/node`.
- `@package.json` / `@package-lock.json` → já versionados e consumidos pelo `npm ci`.
- `@static/src/img` → imagens próprias do projeto, servidas pelo `static`.
- Skills: `componentes-frontend`, `leaflet-map`, `leaflet-geoman`, `escrever-testes`.

## 6 · Snippets

**`package.json`**: tudo exato. Biblioteca de runtime vai em `dependencies`, ferramenta de build em
`devDependencies`. O `npm ci` instala os dois grupos.
```json
{
  "dependencies": {
    "@fontsource/roboto": "5.3.0",
    "@fontsource/roboto-mono": "5.3.0",
    "@geoman-io/leaflet-geoman-free": "2.20.8",
    "htmx.org": "2.0.11",
    "leaflet": "1.9.4"
  },
  "devDependencies": {
    "@tailwindcss/cli": "4.3.3",
    "daisyui": "5.7.4",
    "tailwindcss": "4.3.3"
  }
}
```

**`docker/Dockerfile.web`**: um estágio que só recorta de `node_modules` o que o navegador carrega. Os
pacotes já vêm distribuídos e prontos, então não há bundler: é cópia.
```dockerfile
# Recorta de node_modules só o que vai ao navegador. Caminho inexistente quebra o build aqui.
FROM css-deps AS vendor
RUN mkdir -p /opt/vendor \
 && cp -r /opt/node/node_modules/leaflet/dist                          /opt/vendor/leaflet \
 && cp -r /opt/node/node_modules/@geoman-io/leaflet-geoman-free/dist   /opt/vendor/leaflet-geoman \
 && cp    /opt/node/node_modules/htmx.org/dist/htmx.min.js             /opt/vendor/htmx.min.js \
 && cp -r /opt/node/node_modules/@fontsource/roboto                    /opt/vendor/roboto \
 && cp -r /opt/node/node_modules/@fontsource/roboto-mono               /opt/vendor/roboto-mono
```

e, na imagem final, ao lado do `COPY` do CSS assado:
```dockerfile
# Fora de /app: em desenvolvimento o bind mount esconderia /app/static/dist.
COPY --from=vendor /opt/vendor /opt/vendor
```

**`config/settings.py`**: o diretório entra no `static` com prefixo, então o caminho público não muda
entre dev e produção.
```python
class _Settings(BaseSettings):
    ...
    front_vendor_dir: Path = Field(default=Path("/opt/vendor"), alias="FRONT_VENDOR_DIR")

FRONT_VENDOR_DIR = _env.front_vendor_dir

STATICFILES_DIRS = [
    BASE_DIR / "static" / "dist",
    BASE_DIR / "static" / "src",
    ("vendor", FRONT_VENDOR_DIR),
]
```

**`templates/base.html`**: os mesmos lugares e a mesma ordem de hoje. Só a origem muda.
```html
{% load static %}
<link rel="stylesheet" href="{% static 'vendor/roboto/300.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto/400.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto/500.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto/700.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto/900.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto-mono/400.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto-mono/500.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/roboto-mono/700.css' %}" />

<link rel="stylesheet" href="{% static 'vendor/leaflet/leaflet.css' %}" />
<link rel="stylesheet" href="{% static 'vendor/leaflet-geoman/leaflet-geoman.css' %}" />
<link rel="stylesheet" href="{% static 'output.css' %}" />
<script src="{% static 'vendor/htmx.min.js' %}"></script>
...
<script src="{% static 'vendor/leaflet/leaflet.js' %}"></script>
<script src="{% static 'vendor/leaflet-geoman/leaflet-geoman.min.js' %}"></script>
```

O `preconnect` para o Google sai. `templates/core/design_system.html` troca as mesmas fontes, e a
foto de exemplo do `picsum.photos` passa a ser uma imagem de `static/src/img`.

## 7 · Caveats

As bibliotecas entram por cópia dos arquivos já distribuídos, sem bundler. É o formato em que o CDN
já as servia, e o JS do projeto continua lendo `L` e `htmx` como globais, sem mexer em nenhum módulo.
O custo é que o navegador segue fazendo uma requisição por biblioteca, sem minificação conjunta.

O vendor mora em `/opt/vendor`, dentro da imagem, e não em `static/dist`. O bind mount do código em
desenvolvimento esconderia `/app/static/dist` da imagem. Assim dev e produção leem o mesmo diretório
sem passo de cópia na subida. O custo é que rodar o Django fora do compose exige apontar
`FRONT_VENDOR_DIR` para uma pasta montada à mão, e atualizar uma biblioteca exige
`docker compose build`.

O `npm ci` continua baixando do registro do npm no build da imagem. O lock fixa a versão e o hash de
cada pacote, então o que se baixa é verificado. O custo é que o build da imagem, não o runtime, fica
dependente do registro estar no ar.

Atualização de segurança deixa de chegar sozinha: com versão exata, um patch do HTMX ou do Leaflet só
entra quando alguém sobe a versão no `package.json`. Esse é o propósito da SPEC. O custo é que a
vigilância passa a ser manual.

As fontes do `@fontsource` trazem todos os subconjuntos de caracteres (latim, cirílico, grego,
vietnamita). O `unicode-range` de cada folha faz o navegador baixar só o latim. O custo são alguns MB
a mais na imagem.

## 8 · Testes (TDD)

- `test_templates_nao_referenciam_cdn` — nenhum arquivo de `templates/` ou `apps/**/templates/` cita
  `unpkg.com`, `cdn.jsdelivr.net`, `esm.sh`, `fonts.googleapis.com`, `fonts.gstatic.com` ou
  `picsum.photos`. Falha se uma página nova voltar a puxar biblioteca da rede.
- `test_package_json_so_tem_versao_exata` — toda entrada de `dependencies` e `devDependencies` é uma
  versão exata, sem faixa. Falha no primeiro `^` reintroduzido por `npm install` sem `--save-exact`.
- `test_lock_bate_com_package_json` — a versão de cada pacote direto no `package-lock.json` é a do
  `package.json`. Falha se alguém editar um sem regenerar o outro, que é o que faz o `npm ci` abortar
  no build.
- `test_todo_static_vendor_dos_templates_existe` — todo `{% static 'vendor/...' %}` citado nos
  templates é encontrado pelos finders do Django. Falha se uma atualização de pacote mudar o nome de um
  arquivo em `dist/`. *(marker `integration`; a imagem do `web` não tem pytest, então roda no host
  com `FRONT_VENDOR_DIR` apontando para uma cópia do `/opt/vendor` extraída da imagem, e é pulado
  quando o diretório não existe)*
- `test_home_serve_bibliotecas_locais` — a resposta de `/` traz os `<script>` e `<link>` de
  `static/vendor/` e nenhum endereço externo de biblioteca.

Smoke manual: com o `web` no ar, bloquear a saída para `unpkg.com`, `cdn.jsdelivr.net` e
`fonts.googleapis.com` (por exemplo, apontando-os para `127.0.0.1` no `/etc/hosts` do host), abrir o
mapa e conferir: os marcadores do Leaflet aparecem, a bancada desenha e edita, a busca troca resultado
via HTMX, a tipografia é Roboto, e a aba Network do navegador não mostra nenhuma requisição a esses
domínios.
