---
spec: criacao_usuarios/001
versao: v6
atualizado_em: 2026-08-21
testes_tdd: true
implementado: false
changelog:
  - v1: versão inicial
  - v2: o envio ganha política de retry configurável e o corpo HTML passa por um validador próprio
  - v3: os itens de senha temporária passam a apontar para a SPEC 003
  - v4: a forma autofechada (`<br/>`) deixa de ser lida como fechamento sem abertura
  - v5: o validador de HTML ganha instância única e é usado como função
  - v6: a montagem dos DTOs de configuração a partir de settings ganha factories próprios
---

# SPEC criacao_usuarios/001 — Envio de e-mail pelo SMTP do Gmail

## 1 · User story
**Requisito não-funcional** — o sistema passa a saber entregar uma mensagem a um endereço de e-mail,
por conta autenticada do Gmail, com contrato tipado nas duas pontas, resiliência a falha transitória e
sem vazar `smtplib` para quem chama.

## 2 · Condições de pronto
- [ ] Uma mensagem com destinatário, assunto e corpo em texto sai pelo SMTP do Gmail, autenticada por
      senha de app, com o remetente exibindo **nome**, e chega na caixa do destinatário.
- [ ] Mensagem com corpo HTML chega com **as duas versões**: um cliente sem HTML lê o texto puro.
- [ ] Host, porta, conta, senha, nome de exibição e política de retry vêm do `.env` pela orquestração —
      nenhum deles escrito no código do enviador.
- [ ] Falha **transitória** (conexão, timeout, resposta 4xx do servidor) é repetida até o limite da
      política, com espera entre as tentativas; **falha de autenticação não é repetida**.
- [ ] Esgotadas as tentativas — ou diante de falha definitiva — quem chamou recebe uma **exceção do
      projeto**; nenhuma exceção de `smtplib` atravessa a fronteira.
- [ ] Destinatário **recusado** pelo servidor aparece nomeado no resultado do envio, sem erro — os
      demais destinatários da mesma mensagem seguem entregues.
- [ ] Com o envio **desligado por configuração**, nenhuma conexão é aberta, a mensagem é registrada no
      stdout e o resultado diz que ela não foi entregue ao servidor.
- [ ] Corpo HTML **malformado** — tag não fechada, fechamento sem abertura, fechamento fora de ordem —
      recusa a mensagem na construção dela, com a tag e a linha do erro.
- [ ] O validador aceita **texto sem marcação** e **elementos vazios** (`<br>`, `<img>`) sem exigir
      fechamento.

## 3 · Domínio
Não há domínio da DIMAP aqui: modelam-se dois contratos de utilidade. O de **transporte** — a conta que
envia, a política diante de falha, a mensagem a entregar e o que o servidor respondeu sobre ela; a
mensagem não conhece a conta que a envia, e o resultado não promete entrega ao destinatário, apenas que
o servidor SMTP a aceitou. E o de **boa-formação de HTML** — o veredito sobre um trecho de marcação e
os erros que o sustentam, um por tag problemática, cada um localizado no texto.

**`services/utils/html/models.py`**
```python
class ErroHtml(BaseModel):
    """Uma tag problemática, localizada no texto. Erro sem tag não existe: tudo aqui é sobre marcação."""

    model_config = ConfigDict(frozen=True)

    tag: str
    linha: int
    coluna: int
    mensagem: str


class ResultadoValidacaoHtml(BaseModel):
    """O veredito e o que o sustenta. Válido é exatamente 'sem erro'."""

    model_config = ConfigDict(frozen=True)

    erros: tuple[ErroHtml, ...] = ()

    @computed_field
    @property
    def valido(self) -> bool:
        return not self.erros
```

**`services/utils/smtp/models.py`**
```python
class SmtpRetryPolicy(BaseModel):
    """O que o consumidor declara; o laço que a obedece é do `EnviadorSmtp`."""

    model_config = ConfigDict(frozen=True)

    request_timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 5.0


class SmtpConfig(BaseModel):
    """A conta que envia. Nasce na orquestração (settings) e é injetada no enviador."""

    model_config = ConfigDict(frozen=True)

    host: str
    porta: int
    usuario: EmailStr
    # SecretStr para a senha de app não aparecer em repr, log nem traceback.
    senha: SecretStr
    # O Gmail força o From na conta autenticada; só o nome de exibição é livre.
    remetente_nome: str
    # Desligado, o enviador registra a mensagem no stdout e não abre conexão.
    envio_habilitado: bool = True


class MensagemEmail(BaseModel):
    """O que se quer entregar. Sem remetente: quem envia é a conta do `SmtpConfig`.
    `corpo_html` passa pelo validador na construção — a regra está no §6."""

    model_config = ConfigDict(frozen=True)

    destinatarios: tuple[EmailStr, ...] = Field(min_length=1)
    assunto: str
    corpo_texto: str
    # Presente, vira alternativa HTML do mesmo corpo — nunca substitui o texto.
    corpo_html: str | None = None


class ResultadoEnvio(BaseModel):
    """O que o servidor respondeu. Aceitação do SMTP não é entrega ao destinatário."""

    model_config = ConfigDict(frozen=True)

    entregue_ao_servidor: bool
    destinatarios_recusados: tuple[str, ...] = ()
```

## 4 · Fora de escopo
- Anexos e imagens embutidas na mensagem — sem dono ainda.
- **Sanitização** de HTML (remover `<script>`, atributos de evento, `javascript:`) — sem dono ainda; o
  validador só afere boa-formação.
- Validação de HTML por parser externo (`lxml`, `html5lib`) e conferência de nomes de elemento contra o
  padrão — sem dono ainda.
- Corpo montado a partir de template Django (assunto e HTML da senha temporária) — SPEC
  `criacao_usuarios/003`.
- A senha temporária em si, o model de usuário criado e a rota que dispara o envio — SPEC
  `criacao_usuarios/003`.
- Envio em fila / assíncrono e reentrega depois de esgotado o retry — sem dono ainda; ação é síncrona
  por padrão (CLAUDE.md §3.5).
- Mais de uma conta remetente (por unidade, por tipo de mensagem) — sem dono ainda.

## 5 · Peças de referência a compor
- Skills: `escrever-testes`, `pydantic-validation-errors`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`config/settings.py`** — os campos abaixo entram na `_Settings` que já existe (instância única
`_env`), e as constantes, ao lado das que já estão lá. O prefixo `EMAIL_SMTP_` evita os nomes que o
próprio Django reserva para o `send_mail` dele (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`…), que o
projeto não usa.
```python
class _Settings(BaseSettings):
    # ACRESCENTADOS por esta SPEC — o resto da classe fica como está.
    email_smtp_host: str = Field(default="smtp.gmail.com", alias="EMAIL_SMTP_HOST")
    email_smtp_porta: int = Field(default=587, alias="EMAIL_SMTP_PORTA")
    email_smtp_usuario: str = Field(default="", alias="EMAIL_SMTP_USUARIO")
    email_smtp_senha: str = Field(default="", alias="EMAIL_SMTP_SENHA")
    email_remetente_nome: str = Field(default="DIMAP GeoCoder", alias="EMAIL_REMETENTE_NOME")
    email_envio_habilitado: bool = Field(default=False, alias="EMAIL_ENVIO_HABILITADO")
    email_smtp_timeout_seconds: float = Field(default=30.0, alias="EMAIL_SMTP_TIMEOUT_SECONDS")
    email_smtp_max_retries: int = Field(default=2, alias="EMAIL_SMTP_MAX_RETRIES")
    email_smtp_retry_wait_min_seconds: float = Field(
        default=1.0,
        alias="EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS",
    )
    email_smtp_retry_wait_max_seconds: float = Field(
        default=5.0,
        alias="EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS",
    )


EMAIL_SMTP_HOST = _env.email_smtp_host
EMAIL_SMTP_PORTA = _env.email_smtp_porta
EMAIL_SMTP_USUARIO = _env.email_smtp_usuario
EMAIL_SMTP_SENHA = _env.email_smtp_senha
EMAIL_REMETENTE_NOME = _env.email_remetente_nome
EMAIL_ENVIO_HABILITADO = _env.email_envio_habilitado
EMAIL_SMTP_TIMEOUT_SECONDS = _env.email_smtp_timeout_seconds
EMAIL_SMTP_MAX_RETRIES = _env.email_smtp_max_retries
EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS = _env.email_smtp_retry_wait_min_seconds
EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS = _env.email_smtp_retry_wait_max_seconds
```

**`services/utils/html/validador.py`** — a regra: uma pilha de tags abertas; o que sobra nela no fim é
tag não fechada.
```python
# Elementos vazios não entram na pilha e não podem ser fechados.
ELEMENTOS_VAZIOS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)


class _ColetorTags(HTMLParser):
    """Adaptador do HTMLParser da stdlib — a única herança do módulo, confinada aqui.
    O HTMLParser é leniente por natureza: quem julga é este coletor, não ele."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.abertas: list[tuple[str, int]] = []
        self.erros: list[ErroHtml] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ELEMENTOS_VAZIOS:
            return
        linha, _ = self.getpos()
        self.abertas.append((tag, linha))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <br/> e <img/> são forma válida. Sem este override o HTMLParser dispara start E end,
        # e o end cairia em handle_endtag como "fecha uma tag que não foi aberta".
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        linha, coluna = self.getpos()
        if tag in ELEMENTOS_VAZIOS:
            self._erro(tag, linha, coluna, f"<{tag}> é elemento vazio e não se fecha")
            return
        if not self.abertas:
            self._erro(tag, linha, coluna, f"</{tag}> fecha uma tag que não foi aberta")
            return
        ultima, linha_abertura = self.abertas[-1]
        if ultima != tag:
            # Não desempilha: <b><i></b></i> deve acusar o aninhamento errado, não "consertá-lo".
            self._erro(tag, linha, coluna, f"</{tag}> fecha antes de <{ultima}>, aberta na linha {linha_abertura}")
            return
        self.abertas.pop()


class ValidadorHtml:
    """Callable: recebe marcação, devolve o veredito. Boa-formação apenas — não sanitiza."""

    def __call__(self, html: str) -> ResultadoValidacaoHtml:
        coletor = _ColetorTags()
        coletor.feed(html)
        coletor.close()  # fecha o buffer: tag cortada no fim do texto vira erro, não silêncio
        nao_fechadas = tuple(
            ErroHtml(tag=tag, linha=linha, coluna=0, mensagem=f"<{tag}> foi aberta e não foi fechada")
            for tag, linha in coletor.abertas
        )
        return ResultadoValidacaoHtml(erros=(*coletor.erros, *nao_fechadas))


# Instância única do módulo: o validador não guarda estado entre chamadas — o coletor, que guarda,
# nasce e morre dentro do __call__. Quem consome usa como função, sem construir nada.
validar_html = ValidadorHtml()
```

**`services/utils/smtp/models.py`** — o HTML é aferido na fronteira; a view não faz `try/except`,
o `PydanticValidationMiddleware` intercepta.
```python
class MensagemEmail(BaseModel):
    @field_validator("corpo_html")
    @classmethod
    def _html_bem_formado(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        resultado = validar_html(valor)
        if not resultado.valido:
            raise ValueError("; ".join(erro.mensagem for erro in resultado.erros))
        return valor
```

**`services/utils/smtp/exceptions.py`** — a fronteira: o chamador nunca vê `smtplib`.
```python
class SmtpEnvioError(Exception):
    """Levantada quando a mensagem não pôde ser entregue ao servidor SMTP."""


class SmtpAutenticacaoError(SmtpEnvioError):
    """Levantada quando a conta/senha de app foi recusada — repetir não resolve."""
```

**`services/utils/smtp/enviador.py`** — a regra: montar, conectar, autenticar, entregar; repetir só o
que repetir resolve.
```python
# Falha de rede: a conexão nem chegou a servir. Repetir é a resposta certa.
FALHAS_TRANSITORIAS = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPHeloError,
    OSError,  # timeout de socket e recusa de conexão entram por aqui
)


class EnviadorSmtp:
    """Callable: recebe uma mensagem, devolve o que o servidor respondeu sobre ela."""

    def __init__(
        self,
        config: SmtpConfig,
        policy: SmtpRetryPolicy,
        *,
        # Injetável para o teste trocar o cliente real por um fake — sem rede na suíte.
        cliente_factory: Callable[[], smtplib.SMTP] | None = None,
    ) -> None:
        self._config = config
        self._policy = policy
        self._cliente_factory = cliente_factory or self._abrir_cliente

    def __call__(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        return self.pipeline(mensagem)

    def pipeline(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        mime = self._montar_mime(mensagem)
        if not self._config.envio_habilitado:
            print(f"[SMTP desligado] para={mensagem.destinatarios} assunto={mensagem.assunto}")
            return ResultadoEnvio(entregue_ao_servidor=False)
        return self._entregar(mime)

    def _montar_mime(self, mensagem: MensagemEmail) -> EmailMessage:
        mime = EmailMessage()
        # Address monta o "Nome <conta@dominio>" com o escape correto — nada de f-string.
        mime["From"] = Address(
            display_name=self._config.remetente_nome,
            addr_spec=str(self._config.usuario),
        )
        mime["To"] = ", ".join(mensagem.destinatarios)
        mime["Subject"] = mensagem.assunto
        mime.set_content(mensagem.corpo_texto)
        if mensagem.corpo_html is not None:
            # add_alternative mantém o texto como primeira parte: cliente sem HTML lê ele.
            mime.add_alternative(mensagem.corpo_html, subtype="html")
        return mime

    def _entregar(self, mime: EmailMessage) -> ResultadoEnvio:
        for tentativa in range(self._policy.max_retries + 1):  # range FINITO → sem loop infinito
            resultado = self._tentar(mime, tentativa)
            if resultado is not None:
                return resultado
        raise AssertionError("laço de retry terminou sem retornar nem levantar")

    def _tentar(self, mime: EmailMessage, tentativa: int) -> ResultadoEnvio | None:
        """O resultado, ou None quando ainda há tentativa; esgotado, levanta."""
        try:
            # Conexão NOVA a cada tentativa, e não uma guardada no __init__: as falhas que a
            # política repete (SMTPConnectError, SMTPServerDisconnected) deixam o cliente morto,
            # e o Gmail derruba conexão ociosa antes do próximo envio.
            with self._cliente_factory() as cliente:
                cliente.starttls(context=ssl.create_default_context())
                cliente.login(self._config.usuario, self._config.senha.get_secret_value())
                # send_message devolve só os destinatários RECUSADOS; os demais foram aceitos.
                recusados = cliente.send_message(mime)
        except smtplib.SMTPAuthenticationError as exc:  # antes do genérico: 5xx que retry não conserta
            raise SmtpAutenticacaoError(f"conta {self._config.usuario} recusada") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            # Todos recusados: é resposta do servidor sobre os endereços, não falha de envio.
            return ResultadoEnvio(
                entregue_ao_servidor=False,
                destinatarios_recusados=tuple(exc.recipients),
            )
        except (smtplib.SMTPException, OSError) as exc:
            if not self._e_transitoria(exc):
                raise SmtpEnvioError(f"falha definitiva em {self._config.host}: {exc!r}") from exc
            self._esperar_ou_desistir(repr(exc), tentativa, exc)
            return None
        return ResultadoEnvio(
            entregue_ao_servidor=True,
            destinatarios_recusados=tuple(recusados),
        )

    def _e_transitoria(self, exc: Exception) -> bool:
        if isinstance(exc, smtplib.SMTPResponseException):
            return 400 <= exc.smtp_code < 500  # 4xx é recusa temporária no protocolo SMTP
        return isinstance(exc, FALHAS_TRANSITORIAS)

    def _esperar_ou_desistir(self, motivo: str, tentativa: int, causa: Exception) -> None:
        total = self._policy.max_retries + 1
        if tentativa >= self._policy.max_retries:
            raise SmtpEnvioError(f"{self._config.host}: {motivo} após {total} tentativas") from causa
        time.sleep(
            random.uniform(
                self._policy.retry_wait_min_seconds,
                self._policy.retry_wait_max_seconds,
            )
        )

    def _abrir_cliente(self) -> smtplib.SMTP:
        return smtplib.SMTP(
            self._config.host,
            self._config.porta,
            timeout=self._policy.request_timeout_seconds,
        )
```

**`services/utils/smtp/config.py`** — o comando (e, depois, a view) não remonta os DTOs campo a
campo: pede aos factories, no mesmo padrão de `services.integrations.wfs`. O `settings` entra como
objeto injetado, tipado por `Protocol` — `services/` não importa Django.
```python
class SmtpSettingsLike(Protocol):
    EMAIL_SMTP_HOST: str
    EMAIL_SMTP_PORTA: int
    EMAIL_SMTP_USUARIO: str
    EMAIL_SMTP_SENHA: str
    EMAIL_REMETENTE_NOME: str
    EMAIL_ENVIO_HABILITADO: bool
    EMAIL_SMTP_TIMEOUT_SECONDS: float
    EMAIL_SMTP_MAX_RETRIES: int
    EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS: float
    EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS: float


def build_smtp_config(source: SmtpSettingsLike) -> SmtpConfig:
    return SmtpConfig(
        host=source.EMAIL_SMTP_HOST,
        porta=source.EMAIL_SMTP_PORTA,
        usuario=source.EMAIL_SMTP_USUARIO,
        senha=SecretStr(source.EMAIL_SMTP_SENHA),
        remetente_nome=source.EMAIL_REMETENTE_NOME,
        envio_habilitado=source.EMAIL_ENVIO_HABILITADO,
    )


def build_smtp_retry_policy(source: SmtpSettingsLike) -> SmtpRetryPolicy:
    return SmtpRetryPolicy(
        request_timeout_seconds=source.EMAIL_SMTP_TIMEOUT_SECONDS,
        max_retries=source.EMAIL_SMTP_MAX_RETRIES,
        retry_wait_min_seconds=source.EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=source.EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS,
    )
```

**`services/utils/smtp/__init__.py`** e **`services/utils/html/__init__.py`** — só reexportam. A
instância única sai junto da classe: quem quiser um validador com outro comportamento constrói o seu.
```python
# services/utils/smtp/__init__.py
from .enviador import EnviadorSmtp
from .exceptions import SmtpAutenticacaoError, SmtpEnvioError
from .config import build_smtp_config, build_smtp_retry_policy
from .models import MensagemEmail, ResultadoEnvio, SmtpConfig, SmtpRetryPolicy

# services/utils/html/__init__.py
from .models import ErroHtml, ResultadoValidacaoHtml
from .validador import ValidadorHtml, validar_html
```

**`.env.example`**
```bash
# E-mail — SMTP do Gmail. A senha é uma "senha de app" da conta, não a senha de login.
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORTA=587
EMAIL_SMTP_USUARIO=
EMAIL_SMTP_SENHA=
EMAIL_REMETENTE_NOME=DIMAP GeoCoder
EMAIL_ENVIO_HABILITADO=0
# Resiliência a timeout/conexão (opcional; os defaults espelham o SmtpRetryPolicy)
# EMAIL_SMTP_TIMEOUT_SECONDS=30.0
# EMAIL_SMTP_MAX_RETRIES=2
# EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS=1.0
# EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS=5.0
```

## 7 · Caveats
O retry roda dentro do ciclo request/response de quem chama. O envio é síncrono por ser parte de um ato
administrativo, e não há fila no projeto para onde empurrá-lo. O custo é que, com os defaults, uma
indisponibilidade do Gmail segura o usuário por até três tentativas mais duas esperas antes do erro.

Conexão nova a cada mensagem, sem pool nem sessão reaproveitada — e cada tentativa do retry reabre
tudo, inclusive o `starttls` e o `login`. Reabrir não é escolha dentro do retry, é requisito: a
conexão que falhou está morta. O custo é um handshake TLS por tentativa, irrelevante para dezenas de
usuários e caro no dia em que houver envio em lote, que pediria um método próprio para várias
mensagens numa sessão só.

`_ColetorTags` herda de `HTMLParser`, e o §7.1 do CLAUDE.md trata herança como exceção rara. A stdlib
só oferece o parser por subclasse, e a alternativa seria escrever um tokenizer de HTML à mão. O custo é
uma herança de biblioteca no projeto, contida numa classe privada que o `ValidadorHtml` compõe.

O validador afere boa-formação, não segurança: `<script>`, `onclick=` e `javascript:` passam intactos.
Sanitizar exige lista de elementos e atributos permitidos, que é escopo próprio. O custo é que o corpo
HTML precisa continuar vindo de template do projeto — HTML de origem não confiável não pode ser
entregue a este enviador sem uma SPEC de sanitização antes.

A senha de app fica em texto puro no `.env`, como as demais credenciais do projeto. Não há cofre de
segredos no ambiente e criar um só para isto seria desproporcional. O custo é que quem lê o arquivo
consegue enviar e-mail como a conta da DIMAP — a mitigação é a senha ser de app, revogável sem trocar
a senha da conta.

## 8 · Testes (TDD)
- `test_mensagem_carrega_remetente_com_nome_de_exibicao` — o `From` do MIME sai como
  `"DIMAP GeoCoder" <conta@gmail.com>`, com destinatários e assunto no lugar.
- `test_corpo_html_vira_alternativa_do_texto` — mensagem com HTML sai `multipart/alternative` com as
  duas partes, texto primeiro; sem HTML, sai `text/plain` simples.
- `test_envio_autentica_antes_de_entregar` — o cliente fake registra `starttls`, `login` e
  `send_message`, nessa ordem.
- `test_falha_de_autenticacao_nao_e_repetida` — `SMTPAuthenticationError` sobe como
  `SmtpAutenticacaoError` na primeira tentativa, sem segunda conexão.
- `test_falha_transitoria_e_repetida_e_entrega_na_tentativa_seguinte` — cliente que recusa conexão duas
  vezes e aceita na terceira devolve `entregue_ao_servidor=True`.
- `test_tentativas_esgotadas_viram_excecao_do_projeto` — falha transitória em todas as tentativas sobe
  como `SmtpEnvioError`, e o número de tentativas obedece à política.
- `test_destinatario_recusado_aparece_no_resultado` — cliente que recusa um dos três endereços devolve
  `entregue_ao_servidor=True` e o recusado nomeado.
- `test_envio_desligado_nao_abre_conexao` — com `envio_habilitado=False`, a factory de cliente não é
  chamada e o resultado diz `entregue_ao_servidor=False`.
- `test_html_malformado_recusa_a_mensagem` — tag não fechada, fechamento sem abertura e fechamento fora
  de ordem impedem a construção de `MensagemEmail`, com a tag e a linha no erro.
- `test_html_bem_formado_passa_com_elementos_vazios` — texto puro, `<br>`, `<img>` sem fechamento e a
  forma autofechada `<br/>` dão veredito válido, com aninhamento correto.
