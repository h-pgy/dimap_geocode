---
spec: criacao_usuarios/003
versao: v1
atualizado_em: 2026-08-21
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC criacao_usuarios/003 — O bloco de OTP e o e-mail que entrega o acesso

## 1 · User story
O servidor recém-cadastrado lê na caixa de entrada o RF e a senha temporária — cada dígito na sua
caixa, como num campo de código — para digitá-la no primeiro acesso sem errar caractere.

## 2 · Condições de pronto
- [x] O vocabulário de blocos do e-mail ganha o **OTP**: rótulo e um **caractere por caixa**, em
      fileira — nenhum e-mail escreve marcação própria para isso.
- [x] As caixas saem com **estilo inline** vindo do tema do e-mail, sem `<style>` e sem `class`, e o
      vão entre elas sobrevive ao cliente que descarta folha de estilo.
- [x] Código **maior do que cabe** na largura fixa da placa é recusado na construção do bloco.
- [x] O mesmo código sai em **texto puro** como rótulo e valor na mesma linha, legível sem as caixas.
- [x] Existe o **e-mail de acesso**: saudação pelo nome, o RF em destaque, a senha temporária no bloco
      de OTP, a instrução de troca e o botão que leva ao sistema.
- [x] O HTML montado é **bem formado** pelo validador da SPEC [001](001-smtp.md), com o bloco novo
      entre os demais.
- [x] A senha chega ao montador como **segredo** e só vira texto dentro do corpo da mensagem:
      `repr`, log e traceback do pedido não a mostram.
- [x] O desenho foi aprovado no **mock**, que traz o bloco novo ao lado dos demais e o e-mail de
      acesso inteiro.

## 3 · Domínio
Um bloco novo no vocabulário, e um montador que o usa. O OTP é irmão do destaque — rótulo e valor —,
e o que o separa é a forma: o valor não se lê como palavra, se digita caractere a caractere.

**`services/domain/email/models.py`**
```python
# Cada caixa ocupa largura fixa, e a placa do e-mail tem 600px: acima disto a fileira quebra e o
# código deixa de se ler como um só.
LIMITE_CARACTERES_OTP = 10


class Otp(BlocoEmail):
    """O código que se digita caractere a caractere — uma caixa por caractere, como o campo de OTP
    do design system."""

    tipo: Literal["otp"] = "otp"
    rotulo: str
    valor: str = Field(min_length=1, max_length=LIMITE_CARACTERES_OTP)


Bloco = Annotated[
    # ALTERADO nesta SPEC: `Otp` entra na união discriminada, ao lado dos blocos da SPEC 002.
    Titulo | Subtitulo | Paragrafo | Destaque | Otp | Tabela | Imagem | Botao | Divisor,
    Field(discriminator="tipo"),
]


class EmailAcessoInput(BaseModel):
    """O pedido do e-mail que entrega o acesso. Sem conta remetente: quem envia é a configuração,
    não o caso de uso."""

    model_config = ConfigDict(frozen=True)

    nome: str
    rf: str
    destinatario: EmailStr
    # SecretStr para a senha não aparecer em repr, log nem traceback de quem passa o pedido adiante;
    # no corpo da mensagem ela viaja em claro, que é o propósito dela.
    senha_temporaria: SecretStr
    url_acesso: HttpUrl
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`ConteudoEmail`, `BlocoEmail` e os oito blocos](002-email-de-teste.md) — "como uma mensagem se
  escreve neste sistema?"; o OTP entra como o nono, pela mesma porta.
- [`TEMA_EMAIL`](002-email-de-teste.md) — "de onde vem cada cor e cada medida?"; a caixa não escreve
  hex nem pixel próprio.
- [`ESCRITORES` e `RenderizadorTextoPuro`](002-email-de-teste.md) — os dois registros que todo bloco
  novo alcança: o que o escreve em HTML e o que o diz em texto.
- [`MontarEmailTeste`](002-email-de-teste.md) — o molde do montador: pedido tipado → `ConteudoEmail`.
- [`validar_html`](001-smtp.md) — "esta marcação fecha o que abre?", cobrado na construção da
  `MensagemEmail`.

**Mock:** [003-mock-email-de-acesso.html](003-mock-email-de-acesso.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Gerar a senha temporária, gravá-la e mandar a mensagem — SPEC `criacao_usuarios/004`.
- O campo de OTP **na interface web**, para digitar o código: aqui nasce a forma do e-mail, não o
  componente do design system — sem dono ainda.
- Registro em banco dos e-mails enviados — sem dono ainda.
- E-mail avisando troca de senha, de RF ou de endereço — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/email/tema.py` → `TEMA_EMAIL`: a fonte única de cor, tipografia e medida do
  e-mail; as chaves do OTP entram aqui.
- `@services/domain/email/escritores.py` → `ESCRITORES` e `_texto`: o registro de escritores e o
  escape de todo valor interpolado.
- `@services/domain/email/texto_puro.py` → `RenderizadorTextoPuro._escrever`: o `match` que dá forma
  em texto a cada bloco.
- `@services/domain/email/teste.py` → `MontarEmailTeste`: o molde do montador, com instância única.
- `@services/domain/email/__init__.py`: o pacote reexporta o bloco, o pedido e o montador novos.
- `@.claude/skills/componentes-frontend/examples/design_system.html` e
  https://daisyui.com/components/otp/ — a forma que a caixa reproduz.
- Skills: `mock`, `componentes-frontend`, `ontologia`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/email/tema.py`** — as duas peças novas, cada valor transcrito de um token.
```python
TEMA_EMAIL: dict[str, str] = {
    ...,
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
}
```

**`services/domain/email/escritores.py`** — o escritor do bloco, e o registro que ele alcança.
```python
class EscritorOtp:
    def __call__(self, bloco: Otp) -> str:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Otp) -> str:
        # A moldura é a mesma do destaque — poço com overline —, e é a fileira que muda.
        return (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td style="{TEMA_EMAIL["poco"]}">'
            f'<span style="{TEMA_EMAIL["overline"]}">{_texto(bloco.rotulo)}</span>'
            f"{self._fileira(bloco.valor)}"
            "</td></tr></table>"
        )

    def _fileira(self, valor: str) -> str:
        # O vão entre as caixas é `cellspacing`, ATRIBUTO da tabela: `margin` em <td> é ignorado
        # pelo Outlook, e caixas coladas leem como um número só.
        return (
            f'<table role="presentation" cellpadding="0" cellspacing="8" '
            f'style="{TEMA_EMAIL["otp_fileira"]}"><tr>{self._caixas(valor)}</tr></table>'
        )

    def _caixas(self, valor: str) -> str:
        return "".join(
            f'<td style="{TEMA_EMAIL["otp_caixa"]}">{_texto(caractere)}</td>'
            for caractere in valor
        )


# O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
ESCRITORES: dict[str, Callable[[Any], str]] = {
    ...,
    "otp": EscritorOtp(),
}
```

**`services/domain/email/texto_puro.py`** — em texto não há caixa: sobra o código inteiro.
```python
    def _escrever(self, bloco: object) -> str:
        match bloco:
            ...
            # O OTP e o destaque dizem a mesma coisa em texto — rótulo e valor —, e o que os
            # separava era só a forma.
            case Destaque() | Otp():
                return f"{bloco.rotulo}: {bloco.valor}"
```

**`services/domain/email/acesso.py`** — o montador, no mesmo molde do e-mail de teste.
```python
ASSUNTO_ACESSO = "DIMAP GeoCoder — seu acesso"


class MontarEmailAcesso:
    """Callable: o pedido vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailAcessoInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO_ACESSO,
            blocos=(
                Titulo(texto="Sua conta no DIMAP GeoCoder já existe"),
                Paragrafo(texto=f"{pedido.nome}, entre com o seu RF e a senha temporária abaixo."),
                Destaque(rotulo="RF", valor=pedido.rf, monoespacado=True),
                # `get_secret_value` no último ponto antes do corpo: o SecretStr protege quem passa
                # o pedido adiante, não a mensagem — que existe para entregar a senha.
                Otp(
                    rotulo="Senha temporária",
                    valor=pedido.senha_temporaria.get_secret_value(),
                ),
                Paragrafo(texto="Troque a senha assim que entrar."),
                Botao(rotulo="Acessar o DIMAP GeoCoder", url=pedido.url_acesso),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_acesso = MontarEmailAcesso()
```

## 7 · Caveats
**A largura da caixa é fixa e vive no tema, e o limite de caracteres decorre dela.** Caixa que se
ajusta ao caractere sairia desalinhada entre dígitos estreitos e largos, e sem o limite a fileira
quebraria em duas linhas na placa de 600px. Custo: o comprimento da senha (SPEC
`criacao_usuarios/004`) passa a ter teto aqui, longe de onde ele é escolhido, e passar de dez
caracteres derruba a montagem em vez de encolher a caixa.

**O Outlook desenha as caixas de canto reto.** O motor do Word ignora `border-radius`, e não há
recurso que o contorne sem imagem de fundo. Custo: o mesmo e-mail se lê arredondado no Gmail e
quadrado no Outlook, e o mock não mostra essa segunda forma.

**A senha só existe em claro dentro do corpo montado.** O `SecretStr` protege o pedido em log e
traceback, e o desembrulho acontece uma vez, no montador. Custo: quem imprimir o HTML montado — um
teste, um `print` de depuração — tem a senha na tela, e nada no tipo avisa isso.

## 8 · Testes (TDD)
Todos são domínio puro e rodam na suíte padrão.

- `test_otp_escreve_uma_caixa_por_caractere` — um código de oito dígitos sai com oito células, na
  ordem, cada uma com o estilo da caixa vindo do tema e nenhum valor escrito no escritor.
- `test_otp_recusa_codigo_alem_da_largura` — código mais longo que o limite levanta na construção do
  bloco, não no render.
- `test_otp_sai_legivel_em_texto_puro` — o mesmo bloco vira rótulo e valor na mesma linha.
- `test_email_de_acesso_diz_rf_senha_e_caminho` — os blocos saem na ordem, com o RF em destaque, a
  senha no OTP e a URL no botão.
- `test_email_de_acesso_e_bem_formado` — o HTML do e-mail inteiro, com o bloco novo, passa pelo
  validador da SPEC 001.
- `test_senha_nao_aparece_no_repr_do_pedido` — o `repr` do `EmailAcessoInput` esconde a senha que o
  corpo montado mostra.
