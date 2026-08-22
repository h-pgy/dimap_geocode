---
spec: criacao_usuarios/002
versao: v10
atualizado_em: 2026-08-21
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: o vocabulário do e-mail e o caso de uso do teste passam a viver num submódulo só
  - v3: o e-mail ganha um design system próprio, porte reduzido do tema, e o template deixa de escrever hex
  - v4: o estilo do e-mail passa a chegar inline em todo elemento, sem depender de `<style>`
  - v5: o corpo do e-mail vira sequência de blocos e o HTML passa a ser escrito no domínio, sem template
  - v6: a faixa do envelope passa a carregar a marca, com selo e nome
  - v7: os callables sem configuração ganham instância única e são usados como função
  - v8: o comando passa a especificar como relata cada desfecho do envio
  - v9: a tabela passa a exigir forma retangular e a aceitar célula sem valor
  - v10: o estilo da imagem passa a vir do tema, como o dos demais blocos
---

# SPEC criacao_usuarios/002 — E-mail como blocos, tema próprio e envio de teste

## 1 · User story
O administrador do cadastro dispara um e-mail de teste pelo terminal, no contexto de subir o envio de
e-mail num ambiente novo, para confirmar que a conta, a senha de app e o desenho da mensagem chegam
certos na caixa antes de criar usuário algum.

## 2 · Condições de pronto
- [x] Todo e-mail do sistema é uma **sequência de blocos**, e o básico existe: **título, subtítulo,
      parágrafo, destaque, tabela, imagem, botão e divisor** — nenhum e-mail escreve marcação própria.
- [x] O e-mail **não tem `<style>` nem `class`**: cada bloco sai com o estilo **inline no elemento**, e
      a mensagem se vê igual no cliente que descarta folha de estilo.
- [x] **Nenhum hex é escrito nos escritores**: toda cor, tipografia e medida vem do **tema do e-mail**,
      porte reduzido do tema do sistema, e cada valor lá declara o token de onde veio.
- [x] A **tabela é retangular**: linha com quantidade de células diferente do cabeçalho ou das
      demais é recusada na construção, e célula sem valor sai como célula em branco.
- [x] Texto que vem de fora é **escapado**: `<`, `>` e `&` no conteúdo chegam como texto na caixa do
      destinatário, nunca como marcação.
- [x] O mesmo conteúdo sai também em **texto puro**, com a tabela legível, o destaque nomeado e a URL
      do botão por extenso.
- [x] O HTML montado é **bem formado** pelo validador da SPEC [001](001-smtp.md), com todos os tipos de
      bloco — o e-mail nunca é recusado pela própria montagem.
- [x] `uv run python manage.py enviar_email_teste <endereco>` envia o e-mail de teste àquele endereço,
      dizendo **de qual ambiente** e **em que momento** partiu, e imprime o desfecho: entregue,
      recusado ou envio desligado.
- [x] Endereço inválido no argumento **falha antes de qualquer conexão**, dizendo qual é o problema.
- [x] O design do e-mail foi aprovado no **mock**, e os escritores são o porte fiel dele.

## 3 · Domínio
`services/domain/email/` é o domínio do e-mail do sistema, e guarda três coisas: **o que um e-mail
diz**, **como isso vira HTML e texto** e os **casos de uso** que produzem conteúdo — um por e-mail que o
sistema manda. Hoje há um só, o de teste; a senha temporária entra ao lado dele.

O corpo é uma **sequência de blocos**, não uma forma fixa. Cada tipo de bloco é uma entidade com os
atributos que fazem sentido para ele, e é o tipo — não um campo de configuração — que decide como o
bloco se escreve. E-mail novo é arranjo de blocos existentes; bloco novo é subtipo novo aqui, com o seu
escritor no §6.

O transporte vem pronto da SPEC [001](001-smtp.md): `MensagemEmail`, `EnviadorSmtp` e o
`ValidadorHtml`. A pergunta que esta SPEC faz a ele é **quem monta o `MensagemEmail`, e a partir de
quê**.

**`services/domain/email/models.py`**
```python
class BlocoEmail(BaseModel):
    """A base dos blocos: existe para o tipo discriminar quem se escreve como. Sem campo comum além
    dele — bloco não compartilha atributo, compartilha posição no corpo."""

    model_config = ConfigDict(frozen=True)


class Titulo(BlocoEmail):
    tipo: Literal["titulo"] = "titulo"
    texto: str


class Subtitulo(BlocoEmail):
    tipo: Literal["subtitulo"] = "subtitulo"
    texto: str


class Paragrafo(BlocoEmail):
    tipo: Literal["paragrafo"] = "paragrafo"
    texto: str


class Destaque(BlocoEmail):
    """O que o e-mail quer que se leia primeiro: os dados do teste hoje, a senha temporária amanhã."""

    tipo: Literal["destaque"] = "destaque"
    rotulo: str
    valor: str
    # Monoespaçada quando o valor é para ser copiado à mão — senha, código, identificador.
    monoespacado: bool = False


def _celula_preenchida(valor: str | None) -> str:
    return "" if valor is None else valor


# Célula sem valor é célula em branco, nunca linha mais curta: a forma não depende do preenchimento.
Celula = Annotated[str, BeforeValidator(_celula_preenchida)]


class Tabela(BlocoEmail):
    """Cabeçalho opcional, porque nem toda tabela nomeia coluna; linha, nenhuma é opcional."""

    tipo: Literal["tabela"] = "tabela"
    cabecalho: tuple[Celula, ...] = ()
    linhas: tuple[tuple[Celula, ...], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_forma(self) -> "Tabela":
        # O cabeçalho manda quando existe; sem ele, a primeira linha é que fixa a largura. Tabela
        # torta some como célula faltando na caixa de quem recebe — aqui ela nem chega a existir.
        larguras = {len(linha) for linha in self.linhas}
        if self.cabecalho:
            larguras.add(len(self.cabecalho))
        if len(larguras) > 1:
            raise ValueError(
                f"Tabela mal estruturada: larguras {sorted(larguras)} entre cabeçalho e linhas."
            )
        return self


class Imagem(BlocoEmail):
    tipo: Literal["imagem"] = "imagem"
    # Absoluta: e-mail não tem base de onde resolver caminho relativo.
    url: HttpUrl
    # Obrigatório: bloquear imagem é o default de vários clientes, e o alternativo é o que sobra.
    alternativo: str
    largura: int | None = None


class Botao(BlocoEmail):
    tipo: Literal["botao"] = "botao"
    rotulo: str
    url: HttpUrl


class Divisor(BlocoEmail):
    """Só separa. Sem atributo: o que ele carrega é a pausa."""

    tipo: Literal["divisor"] = "divisor"


Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Destaque | Tabela | Imagem | Botao | Divisor,
    Field(discriminator="tipo"),
]


class ConteudoEmail(BaseModel):
    """O que o e-mail diz. O assunto e o rodapé estão fora dos blocos porque todo e-mail tem os dois,
    exatamente uma vez."""

    model_config = ConfigDict(frozen=True)

    assunto: str
    blocos: tuple[Bloco, ...] = Field(min_length=1)
    rodape: str


class EmailTesteInput(BaseModel):
    """O pedido do teste. Sem conta remetente: quem envia é a configuração, não o caso de uso."""

    model_config = ConfigDict(frozen=True)

    destinatario: EmailStr
    # De onde o e-mail partiu, para quem recebe saber qual ambiente está sendo provado.
    ambiente: str
    momento: datetime
```

**Mock:** [002-mock-email-de-teste.html](002-mock-email-de-teste.html) — leia a skill `mock`.

## 4 · Fora de escopo
- A senha temporária, o usuário criado e a rota que dispara o e-mail dela — SPEC `criacao_usuarios/003`.
- Disparar o e-mail de teste pela área administrativa, com botão — sem dono ainda; aqui é terminal.
- Registro em banco dos e-mails enviados (quem disparou, para quem, quando) — sem dono ainda.
- Imagem embutida como anexo (`cid:`) e logotipo em bitmap — sem dono ainda; o bloco de imagem aponta
  para URL absoluta.
- Modo escuro do cliente de e-mail — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/smtp` → `EnviadorSmtp`, `MensagemEmail`, `SmtpConfig`: o transporte inteiro, da SPEC 001.
- `@services/utils/html` → `ValidadorHtml`: afere a boa-formação do HTML montado.
- `@static/src/tema-dimap.dev.css` → o tema do sistema: a fonte de onde cada valor do e-mail é transcrito.
- Skills: `mock`, `componentes-frontend`, `management-commands`, `ontologia`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/email/tema.py`** — o design system do e-mail: **só** as peças que os escritores
usam, cada uma já na forma de um atributo `style` inteiro. Fonte única dos valores, cada um nomeando o
token de origem.
```python
# Cliente de e-mail não tem Tailwind, daisyUI, var() nem folha confiável: cada declaração viaja
# colada ao elemento. Chave = peça; valor = o atributo style inteiro.
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
    # A faixa é o único lugar do e-mail com tinta clara sobre fundo escuro.
    "marca_selo": (
        "background:#FFFFFF;border-radius:8px;color:#0096C7;font-size:18px;"
        "font-weight:900;text-align:center;height:32px;"
    ),
    "marca_nome": "padding-left:12px;color:#FFFFFF;font-size:15px;font-weight:700;",
    "rodape": "padding:0 28px 24px;color:#5B7290;font-size:13px;",  # rocha-600
}
```

**`services/domain/email/escritores.py`** — um escritor por bloco. Cada um é a única linha do projeto
que sabe **como aquele bloco vira HTML**, e nenhum deles escreve valor: pede a peça ao tema.
```python
def _texto(bruto: str) -> str:
    # Escrever HTML na mão tira do Django o autoescape: o escape passa a ser daqui, e vale para
    # TODO valor interpolado. Sem isso, um "<" no nome de uma unidade vira marcação na caixa.
    return escape(bruto)


class EscritorTitulo:
    def __call__(self, bloco: Titulo) -> str:
        return f'<h1 style="{TEMA_EMAIL["titulo"]}">{_texto(bloco.texto)}</h1>'


class EscritorSubtitulo:
    def __call__(self, bloco: Subtitulo) -> str:
        return f'<h2 style="{TEMA_EMAIL["subtitulo"]}">{_texto(bloco.texto)}</h2>'


class EscritorParagrafo:
    def __call__(self, bloco: Paragrafo) -> str:
        return f'<p style="{TEMA_EMAIL["paragrafo"]}">{_texto(bloco.texto)}</p>'


class EscritorDestaque:
    def __call__(self, bloco: Destaque) -> str:
        estilo = TEMA_EMAIL["valor_mono"] if bloco.monoespacado else TEMA_EMAIL["valor"]
        return (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td style="{TEMA_EMAIL["poco"]}">'
            f'<span style="{TEMA_EMAIL["overline"]}">{_texto(bloco.rotulo)}</span><br>'
            f'<span style="{estilo}">{_texto(bloco.valor)}</span>'
            "</td></tr></table>"
        )


class EscritorTabela:
    """Callable com mais de uma etapa: o `__call__` delega, o pipeline monta."""

    def __call__(self, bloco: Tabela) -> str:
        return self.pipeline(bloco)

    def pipeline(self, bloco: Tabela) -> str:
        partes = ['<table role="presentation" width="100%" cellpadding="0" cellspacing="0">']
        if bloco.cabecalho:
            partes.append(self._linha(bloco.cabecalho, TEMA_EMAIL["celula_cabecalho"]))
        partes.extend(self._linha(linha, TEMA_EMAIL["celula"]) for linha in bloco.linhas)
        partes.append("</table>")
        return "".join(partes)

    def _linha(self, celulas: tuple[str, ...], estilo: str) -> str:
        return "<tr>" + "".join(f'<td style="{estilo}">{_texto(c)}</td>' for c in celulas) + "</tr>"


class EscritorImagem:
    def __call__(self, bloco: Imagem) -> str:
        # width como ATRIBUTO, não CSS: é o que o Outlook obedece.
        largura = f' width="{bloco.largura}"' if bloco.largura is not None else ""
        return (
            f'<img src="{bloco.url}" alt="{_texto(bloco.alternativo)}"{largura} '
            f'style="{TEMA_EMAIL["imagem"]}">'
        )


class EscritorBotao:
    def __call__(self, bloco: Botao) -> str:
        return f'<a href="{bloco.url}" style="{TEMA_EMAIL["botao"]}">{_texto(bloco.rotulo)}</a>'


class EscritorDivisor:
    def __call__(self, bloco: Divisor) -> str:
        return f'<hr style="{TEMA_EMAIL["divisor"]}">'


# O registro é a única lista de tipos do módulo: bloco novo entra aqui e em lugar nenhum mais.
ESCRITORES: dict[str, Callable[[Any], str]] = {
    "titulo": EscritorTitulo(),
    "subtitulo": EscritorSubtitulo(),
    "paragrafo": EscritorParagrafo(),
    "destaque": EscritorDestaque(),
    "tabela": EscritorTabela(),
    "imagem": EscritorImagem(),
    "botao": EscritorBotao(),
    "divisor": EscritorDivisor(),
}
```

**`services/domain/email/html.py`** — o envelope: a água, a placa e a faixa em volta do que os
escritores produziram.
```python
class RenderizadorEmailHtml:
    """Callable: ConteudoEmail → o HTML inteiro do e-mail."""

    def __init__(self, escritores: Mapping[str, Callable[[Any], str]] | None = None) -> None:
        self._escritores = dict(escritores or ESCRITORES)

    def __call__(self, conteudo: ConteudoEmail) -> str:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: ConteudoEmail) -> str:
        corpo = "".join(self._escrever(bloco) for bloco in conteudo.blocos)
        return self._envelopar(corpo, conteudo.rodape)

    def _escrever(self, bloco: BlocoEmail) -> str:
        # Bloco sem escritor levanta KeyError na montagem, onde há teste e stack trace —
        # e não como buraco silencioso na caixa de quem recebe.
        return self._escritores[bloco.tipo](bloco)

    def _envelopar(self, corpo: str, rodape: str) -> str:
        # Largura e alinhamento como ATRIBUTO de tabela, não CSS: é o que sobrevive em qualquer
        # cliente. Aninhamento de tabela no lugar de flex, pelo mesmo motivo.
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="{TEMA_EMAIL["fundo"]}"><tr><td align="center">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
            f'style="{TEMA_EMAIL["placa"]}">'
            f'<tr><td style="{TEMA_EMAIL["faixa"]}">{self._marca()}</td></tr>'
            f'<tr><td style="{TEMA_EMAIL["corpo"]}">{corpo}</td></tr>'
            f'<tr><td style="{TEMA_EMAIL["rodape"]}">{escape(rodape)}</td></tr>'
            "</table></td></tr></table>"
        )

    def _marca(self) -> str:
        # Tabela de duas células, e não inline-block: alinhamento vertical confiável no Outlook.
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td width="32" style="{TEMA_EMAIL["marca_selo"]}">D</td>'
            f'<td style="{TEMA_EMAIL["marca_nome"]}">DIMAP GeoCoder</td>'
            "</tr></table>"
        )


# Instância única: o renderizador não guarda estado, e o registro de escritores é o default.
renderizar_html = RenderizadorEmailHtml()
```

**`services/domain/email/texto_puro.py`** — a mesma sequência de blocos em texto: o que só existe no
HTML (o botão, a moldura da tabela) vira palavra.
```python
class RenderizadorTextoPuro:
    """Callable: ConteudoEmail → o corpo em texto. Bloco que não diz nada em texto não entra."""

    def __call__(self, conteudo: ConteudoEmail) -> str:
        return "\n\n".join(self.pipeline(conteudo))

    def pipeline(self, conteudo: ConteudoEmail) -> list[str]:
        blocos = [texto for bloco in conteudo.blocos if (texto := self._escrever(bloco))]
        blocos.append(conteudo.rodape)
        return blocos

    def _escrever(self, bloco: BlocoEmail) -> str:
        match bloco:
            case Titulo() | Subtitulo() | Paragrafo():
                return bloco.texto
            case Destaque():
                return f"{bloco.rotulo}: {bloco.valor}"
            case Tabela():
                # Sem moldura: cada linha vira uma linha de texto com as células separadas.
                return "\n".join(" | ".join(linha) for linha in (*_cabecalho(bloco), *bloco.linhas))
            case Imagem():
                return f"[imagem: {bloco.alternativo}]"
            case Botao():
                # O botão não existe em texto: sobra o rótulo e a URL inteira, clicável no cliente.
                return f"{bloco.rotulo}: {bloco.url}"
            case Divisor():
                return ""  # a pausa já é o parágrafo em branco do join
        raise AssertionError(f"bloco sem forma em texto: {bloco!r}")


renderizar_texto_puro = RenderizadorTextoPuro()
```

**`services/domain/email/montagem.py`** — as duas versões saem do MESMO conteúdo.
```python
class MontarMensagem:
    """Callable: ConteudoEmail → MensagemEmail, pronta para o EnviadorSmtp da SPEC 001."""

    def __init__(
        self,
        # Injetáveis para o teste trocar um renderizador; o default é a instância do módulo.
        html: Callable[[ConteudoEmail], str] | None = None,
        texto: Callable[[ConteudoEmail], str] | None = None,
    ) -> None:
        self._html = html or renderizar_html
        self._texto = texto or renderizar_texto_puro

    def __call__(self, conteudo: ConteudoEmail, destinatarios: tuple[str, ...]) -> MensagemEmail:
        return MensagemEmail(
            destinatarios=destinatarios,
            assunto=conteudo.assunto,
            corpo_texto=self._texto(conteudo),
            # O ValidadorHtml da SPEC 001 roda no field_validator de MensagemEmail: escritor
            # que produza marcação torta é pego aqui, não na caixa de quem recebe.
            corpo_html=self._html(conteudo),
        )


montar_mensagem = MontarMensagem()
```

**`services/domain/email/teste.py`** — o corpo do e-mail de teste, e só ele. Cada e-mail do sistema
ganha um módulo assim ao lado deste.
```python
ASSUNTO = "DIMAP GeoCoder — e-mail de teste"


class MontarEmailTeste:
    """Callable: o pedido de teste vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailTesteInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO,
            blocos=(
                Titulo(texto="O envio de e-mail está funcionando"),
                Paragrafo(
                    texto="Esta mensagem foi disparada para provar a configuração de envio do "
                    "DIMAP GeoCoder."
                ),
                # O destaque carrega o que identifica ESTE envio: sem isso, dois testes seguidos
                # são indistinguíveis na caixa de entrada.
                Destaque(
                    rotulo="Ambiente e momento do disparo",
                    valor=f"{pedido.ambiente} · {pedido.momento:%d/%m/%Y %H:%M:%S}",
                    monoespacado=True,
                ),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_teste = MontarEmailTeste()
```

**`apps/users/`** — app novo, registrado em `INSTALLED_APPS` (sem isso o `manage.py` não acha o
comando). Nesta iteração ele tem só `apps.py` e a árvore `management/commands/`: nenhuma rota, nenhum
model, nenhuma migração.

**`apps/users/management/commands/enviar_email_teste.py`** — o comando é fino: lê `settings`, monta os
DTOs, chama as peças e formata o desfecho. É o único jeito de provar o envio ponta a ponta, então o
que ele imprime é parte do entregável, não enfeite.
```python
class Command(BaseCommand):
    help = "Envia um e-mail de teste para o endereço informado, provando a configuração de SMTP."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("destinatario", type=str)

    def handle(self, *args: object, **options: object) -> None:
        # EmailStr valida aqui: endereço torto morre antes de qualquer conexão.
        pedido = EmailTesteInput(
            destinatario=str(options["destinatario"]),
            ambiente=settings.ALLOWED_HOSTS[0],
            momento=timezone.now(),
        )
        conteudo = montar_email_teste(pedido)
        mensagem = montar_mensagem(conteudo, destinatarios=(pedido.destinatario,))
        enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
        resultado = enviador(mensagem)
        self.stdout.write(self._desfecho(resultado, pedido.destinatario))

    def _desfecho(self, resultado: ResultadoEnvio, destinatario: str) -> str:
        # A ORDEM importa: recusa total devolve entregue_ao_servidor=False COM a lista de
        # recusados. Perguntar por "entregue" primeiro faria uma recusa ser relatada como
        # "envio desligado" — o desfecho mais enganoso possível para quem está testando.
        if resultado.destinatarios_recusados:
            recusados = ", ".join(resultado.destinatarios_recusados)
            return self.style.ERROR(f"Recusado pelo servidor: {recusados}")
        if not resultado.entregue_ao_servidor:
            return self.style.WARNING(
                "Envio desligado (EMAIL_ENVIO_HABILITADO=0): a mensagem foi montada e impressa, "
                f"mas nada foi enviado a {destinatario}."
            )
        return self.style.SUCCESS(f"Entregue ao servidor SMTP para {destinatario}.")
```

O comando **não** expõe `--verbose` nem `--automatico`: essas duas são do contrato dos comandos de
carga (`ScriptRunner`, SPEC `ingestao_dados/006`), e este não é um deles — não lê base oficial, não
grava em `data/` e não roda pelo daemon.

## 7 · Caveats
O HTML do e-mail é montado no domínio, em `services/domain/email/`, e não em `templates/` — é a única
marcação do projeto que não vive lá, e a única que roda sem o autoescape do Django. O e-mail não é
resposta HTTP: é documento de estilo inline, sem relação com o `base.html`, e escrevê-lo no domínio é o
que dá um lugar só onde o tema é aplicado, em vez de espalhar hex por template. O custo é que o escape
de todo valor interpolado passa a ser responsabilidade dos escritores — por isso é condição de pronto e
teste — e quem procura marcação em `templates/` não acha a do e-mail.

O tema do e-mail é porte reduzido do tema do sistema, feito à mão, com os valores copiados dos tokens.
Nem Tailwind, nem daisyUI, nem `var()`, nem blur atravessam um cliente de e-mail: o §3.4 do CLAUDE.md
vale aqui como fonte dos valores, não como biblioteca a compor. O custo é que esses valores podem
divergir do tema quando ele mudar, sem nada que avise.

Todo estilo viaja inline no elemento, o que descarta media query, `:hover` e qualquer seletor. É o
único formato que sobrevive a cliente que remove `<style>` — o app do Gmail com conta de terceiros é o
caso conhecido —, e o e-mail chegar certo vem antes de chegar bonito. O custo é um leiaute de largura
fixa em 600px, sem adaptação a tela estreita além do que o próprio cliente faz, e sem reação nenhuma ao
ponteiro.

O comando mora em `apps/users`, um app novo que ainda não tem rota, model nem ação. Ele nasce agora
porque é a casa da criação de usuário da SPEC `criacao_usuarios/003` e o destino do que hoje está
acumulado em `apps/user_admin`, que será migrado e renomeado em iteração própria. O custo é conviver
por enquanto com dois apps de nome parecido, um deles servindo só de casa para um comando.

O e-mail de teste não é registrado em lugar nenhum: o desfecho só aparece no stdout de quem rodou o
comando. Não é ato administrativo — é ferramenta de operação, e o §3.5 do CLAUDE.md pede registro para
ação, não para comando. O custo é que não há como saber depois quem disparou teste, para onde e se
chegou.

## 8 · Testes (TDD)
- `test_cada_tipo_de_bloco_sai_com_o_estilo_do_tema` — o HTML de cada bloco carrega o `style` da peça
  correspondente de `TEMA_EMAIL`, e nenhum outro valor.
- `test_texto_de_bloco_e_escapado` — `<b>` e `&` no texto de um bloco chegam como texto, não como
  marcação.
- `test_tabela_escreve_cabecalho_e_linhas_na_ordem` — tabela com cabeçalho e duas linhas sai com as
  células na ordem declarada; sem cabeçalho, nenhuma linha de cabeçalho aparece; célula sem valor
  sai como célula em branco.
- `test_tabela_recusa_linha_de_largura_diferente` — linha com mais ou menos células que o cabeçalho,
  ou que as demais linhas, levanta na construção do bloco.
- `test_bloco_sem_escritor_falha_na_montagem` — bloco cujo tipo não está no registro levanta na
  montagem, em vez de sumir do e-mail.
- `test_html_montado_e_bem_formado_e_nao_tem_folha_nem_classe` — com todos os tipos de bloco, o HTML
  passa no `ValidadorHtml` e não contém `<style>` nem atributo `class`.
- `test_texto_puro_preserva_blocos_e_url` — a versão texto traz título, parágrafos, o destaque nomeado,
  a tabela legível e a URL do botão por extenso, sem linha em branco dobrada.
- `test_conteudo_do_email_de_teste_diz_ambiente_e_momento` — `MontarEmailTeste` devolve o assunto fixo
  e um destaque com o ambiente e o instante do disparo.
- `test_montagem_devolve_mensagem_com_as_duas_versoes` — `MontarMensagem` devolve `MensagemEmail` com o
  assunto do conteúdo e os dois corpos preenchidos.
- `test_comando_recusa_endereco_invalido` — endereço torto encerra o comando sem instanciar o enviador.
- `test_comando_relata_o_desfecho_do_envio` — com enviador fake, o comando imprime entregue, recusado e
  desligado conforme o `ResultadoEnvio`.
