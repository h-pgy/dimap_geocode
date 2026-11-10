---
spec: infraestrutura/005
versao: v1
atualizado_em: 2026-11-09
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC infraestrutura/005 — Checagem do ambiente de produção

## 1 · User story

**Requisito não-funcional**: com `PROD` ligado, o container `web` não sobe se alguma configuração de
ambiente perigosa para produção estiver em vigor, e lista todas elas no log.

## 2 · Condições de pronto

- [ ] Com `PROD` ligado e qualquer configuração perigosa (§3), o `web` **não sobe**: o entrypoint
      aborta **antes da migração** e sai com código diferente de zero.
- [ ] O erro lista **todas** as variáveis perigosas de uma vez, cada uma com o motivo.
- [ ] Nenhum valor de segredo (`DJANGO_SECRET_KEY`, `ASSINATURA_SEGREDO`, `POSTGRES_PASSWORD`)
      aparece no erro.
- [ ] Com `PROD` ligado e o ambiente seguro, a subida segue normalmente.
- [ ] Com `PROD` desligado (o padrão), a subida com os valores do `.env.example` segue como hoje.
- [ ] Sem `.env`, os defaults do settings são recusados quando `PROD` está ligado.

## 3 · Domínio

Esta SPEC não introduz domínio da DIMAP: é a validação da configuração já lida pelo
`config/settings.py`. A checagem recebe os valores **efetivos** (env, ou o default do settings
quando o env cala) e devolve as violações.

```python
class AmbienteProducaoInput(BaseModel):
    debug: bool
    secret_key: SecretStr
    assinatura_segredo: SecretStr
    postgres_password: SecretStr
    allowed_hosts: list[str]
    csrf_trusted_origins: list[str]
    email_envio_habilitado: bool
    enforce_prefeitura_email: bool


class Violacao(BaseModel):
    variavel: str   # o nome da variável de ambiente, ex. "DJANGO_DEBUG". Nunca carrega o valor.
    motivo: str


class AmbienteProducaoOutput(BaseModel):
    violacoes: tuple[Violacao, ...]
```

| Variável | Perigosa quando |
|---|---|
| `DJANGO_DEBUG` | ligada |
| `DJANGO_SECRET_KEY` | menos de 50 caracteres, ou menos de 5 caracteres distintos |
| `ASSINATURA_SEGREDO` | idem |
| `POSTGRES_PASSWORD` | menos de 16 caracteres |
| `DJANGO_ALLOWED_HOSTS` | contém `*` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | alguma origem com curinga (`*`) ou em `http://` |
| `EMAIL_ENVIO_HABILITADO` | desligada (a senha de uso único iria para a tela) |
| `ENFORCE_PREFEITURA_EMAIL` | desligada |

`PROD` é uma variável nova (`bool`, default `False`), lida pelo settings como as demais.

## 4 · Fora de escopo

- `DJANGO_AUTO_MIGRATE` ligado em produção: a variável é lida só pelo `entrypoint.sh`, fora do
  settings. Sem dono ainda.
- O container `daemon` não passa pela checagem, porque não tem entrypoint. Sem dono ainda.
- Configurações de produção que são código e não ambiente (cookies `Secure`,
  `SECURE_PROXY_SSL_HEADER`, `LOGGING`, `STATIC_ROOT`): ficam com a SPEC de deploy, sem número ainda
  (ver `DOCS/deploy/deploy-producao.md`, Parte 1).

## 5 · Peças de referência a compor

- `@config/settings.py` → `_parse_lista_env`: já entrega `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`
  como lista.
- `@services/utils/ambiente` → pacote dos utilitários de ambiente; a checagem mora ao lado do
  `definidos`.
- `@tests/docker/test_entrypoint.py` → harness do entrypoint com `python` falso no `PATH`.
- Skills: `management-commands`, `escrever-testes`.

## 6 · Snippets

> Os comentários abaixo são didáticos e **não são portados** para o código (CLAUDE.md §7.2).

**`services/utils/ambiente/producao.py`**
```python
TAMANHO_MINIMO_SEGREDO = 50
CARACTERES_DISTINTOS_MINIMOS_SEGREDO = 5
TAMANHO_MINIMO_SENHA_BANCO = 16


class ChecarAmbienteProducao:
    def __call__(self, ambiente: AmbienteProducaoInput) -> AmbienteProducaoOutput:
        return self.pipeline(ambiente)

    def pipeline(self, ambiente: AmbienteProducaoInput) -> AmbienteProducaoOutput:
        # Todas as regras rodam sempre: quem faz o deploy corrige tudo numa volta só,
        # em vez de descobrir uma violação por tentativa.
        regras = (
            self._debug,
            self._secret_key,
            self._assinatura_segredo,
            self._senha_banco,
            self._allowed_hosts,
            self._csrf_trusted_origins,
            self._envio_email,
            self._enforce_prefeitura_email,
        )
        violacoes = tuple(v for regra in regras if (v := regra(ambiente)) is not None)
        return AmbienteProducaoOutput(violacoes=violacoes)

    def _debug(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if not ambiente.debug:
            return None
        return Violacao(
            variavel="DJANGO_DEBUG",
            motivo="debug ligado expõe traceback e configuração a qualquer visitante.",
        )

    def _secret_key(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if not self._eh_segredo_fraco(ambiente.secret_key):
            return None
        return Violacao(
            variavel="DJANGO_SECRET_KEY",
            motivo=f"precisa de ao menos {TAMANHO_MINIMO_SEGREDO} caracteres aleatórios.",
        )

    # _assinatura_segredo, _senha_banco e _enforce_prefeitura_email seguem o mesmo molde.

    def _csrf_trusted_origins(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        # O default do settings confia em túneis do ngrok (curinga), e `http://` deixa o
        # token CSRF trafegar em claro.
        inseguras = [
            origem
            for origem in ambiente.csrf_trusted_origins
            if "*" in origem or origem.startswith("http://")
        ]
        if not inseguras:
            return None
        # A origem não é segredo: pode ir na mensagem, e ajuda a achar a linha no .env.
        return Violacao(
            variavel="DJANGO_CSRF_TRUSTED_ORIGINS",
            motivo=f"origens com curinga ou sem HTTPS: {', '.join(inseguras)}.",
        )

    def _envio_email(self, ambiente: AmbienteProducaoInput) -> Violacao | None:
        if ambiente.email_envio_habilitado:
            return None
        return Violacao(
            variavel="EMAIL_ENVIO_HABILITADO",
            motivo="desligado, a senha de uso único aparece na tela de quem digitar o RF.",
        )

    def _eh_segredo_fraco(self, segredo: SecretStr) -> bool:
        # Os defaults de dev ("dev-insecure-...") têm menos de 50 caracteres: o critério de
        # tamanho os pega sem que a regra precise conhecer cada valor de dev.
        valor = segredo.get_secret_value()
        return (
            len(valor) < TAMANHO_MINIMO_SEGREDO
            or len(set(valor)) < CARACTERES_DISTINTOS_MINIMOS_SEGREDO
        )


checar_ambiente_producao = ChecarAmbienteProducao()
```

**`config/settings.py`** (acréscimo)
```python
    prod: bool = Field(default=False, alias="PROD")

PROD = _env.prod
```

**`apps/core/management/commands/checar_ambiente_producao.py`**
```python
class Command(BaseCommand):
    help = "Com PROD ligado, recusa o ambiente que tenha configuração perigosa para produção."

    def handle(self, *args: object, **options: object) -> None:
        # Decidir SE chama é orquestração; QUAIS regras valem é do serviço.
        if not settings.PROD:
            self.stdout.write("PROD desligado: checagem do ambiente de produção pulada.")
            return
        resultado = checar_ambiente_producao(
            AmbienteProducaoInput(
                debug=settings.DEBUG,
                secret_key=SecretStr(settings.SECRET_KEY),
                assinatura_segredo=settings.ASSINATURA_SEGREDO,
                postgres_password=SecretStr(settings.DATABASES["default"]["PASSWORD"]),
                allowed_hosts=settings.ALLOWED_HOSTS,
                csrf_trusted_origins=settings.CSRF_TRUSTED_ORIGINS,
                email_envio_habilitado=settings.EMAIL_ENVIO_HABILITADO,
                enforce_prefeitura_email=settings.ENFORCE_PREFEITURA_EMAIL,
            )
        )
        if resultado.violacoes:
            linhas = "\n".join(f"  - {v.variavel}: {v.motivo}" for v in resultado.violacoes)
            # CommandError sai com código 1: é isso que o `set -e` do entrypoint pega.
            raise CommandError(f"ambiente de produção inseguro, deploy abortado:\n{linhas}")
        self.stdout.write(self.style.SUCCESS("Ambiente de produção conferido."))
```

**`docker/entrypoint.sh`** (antes do bloco de migração)
```sh
# Primeiro passo da subida: nada toca o banco antes de o ambiente ser aprovado.
if [ -f manage.py ]; then
    echo "==> Checando ambiente de produção..."
    python manage.py checar_ambiente_producao
fi
```

**`docker-compose.yml`** (`web.environment`) e **`.env.example`**
```yaml
      PROD: ${PROD:-0}
```
```sh
# Ligado, o web recusa subir com configuração perigosa (DEBUG, segredos de dev, e-mail desligado...).
PROD=0
```

## 7 · Caveats

A força dos segredos é julgada por tamanho e variedade de caracteres, não por comparação com os
valores de dev. Assim a regra não precisa de uma segunda cópia de cada default do settings. O custo
é que um valor longo, mas conhecido (copiado de um tutorial, por exemplo), passa pela checagem.

`PROD` é uma chave separada de `DJANGO_DEBUG`, porque homologação roda com `DEBUG=0` e ainda precisa
de e-mail desligado e outros afrouxamentos. O custo: em produção sem `PROD=1`, a checagem inteira é
pulada em silêncio.

A checagem roda no entrypoint, não no import do settings, porque no settings ela quebraria
management commands e testes. O custo: subir o processo sem o entrypoint da imagem (gunicorn direto
no host, ou `--entrypoint` sobrescrito) escapa da checagem.

## 8 · Testes (TDD)

- `test_ambiente_seguro_nao_tem_violacao`: valores fortes em todas as variáveis devolvem
  `violacoes` vazio.
- `test_cada_configuracao_perigosa_vira_violacao_da_sua_variavel`: parametrizado pelas 8 linhas da
  tabela do §3. Partindo do ambiente seguro, estragar uma variável gera **exatamente uma** violação,
  com aquele nome de variável.
- `test_segredo_longo_e_repetitivo_e_fraco`: `"a" * 60` em `DJANGO_SECRET_KEY` é violação (a borda
  do critério de variedade).
- `test_defaults_de_dev_sao_recusados_de_uma_vez`: os valores do `.env.example` (e os defaults do
  settings) geram, numa chamada só, uma violação para cada variável perigosa que eles carregam (7;
  `ENFORCE_PREFEITURA_EMAIL` já vem ligado).
- `test_comando_com_prod_desligado_nao_checa`: com `PROD=False` e o ambiente inseguro, o comando
  termina sem erro.
- `test_comando_com_prod_ligado_e_ambiente_inseguro_aborta_listando_tudo`: com `PROD=True`, o
  comando levanta `CommandError` com uma linha por violação.
- `test_erro_do_comando_nao_exibe_valor_de_segredo`: o texto do `CommandError` não contém o valor de
  `DJANGO_SECRET_KEY`, de `ASSINATURA_SEGREDO` nem de `POSTGRES_PASSWORD`.
- `test_entrypoint_aborta_antes_da_migracao_quando_checagem_falha` (em `tests/docker/`): com o
  `python` falso falhando em `checar_ambiente_producao`, o entrypoint sai com código diferente de
  zero, sem chamar `migrate` nem o `CMD`.
