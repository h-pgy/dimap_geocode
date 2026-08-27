---
spec: autenticacao/003
versao: v2
atualizado_em: 2026-08-27
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: acionador de logout na página do servidor, e `/logout/` passa a exigir POST de sessão autenticada
---

# SPEC autenticacao/003 — Recuperação de senha por link de uso único no e-mail

## 1 · User story
O servidor da DIMAP que esqueceu a senha pede, da própria tela de login, um link de uso único para o
seu e-mail institucional e volta a entrar definindo uma senha nova.

E, do outro lado da sessão, ele a encerra pela própria página — o acionador de logout que a SPEC
[001](001-login-e-primeiro-acesso.md) deixou marcado para esta (§4 de lá) e que, sem gatilho, deixava
a rota alcançável só pela URL.

## 2 · Condições de pronto
- [ ] O ramo de senha do partial dinâmico do login exibe o acionador **"Esqueci minha senha"**, que
      leva o RF já digitado para a tela de recuperação (`/esqueci-minha-senha/?rf=`); havendo pedido
      de redefinição **em aberto** para aquele RF, o mesmo partial exibe o aviso na **cor semântica
      de informação**, dizendo que o link está na caixa de entrada.
- [ ] A tela de recuperação, com RF de servidor **ativo e de senha definitiva**, exibe o nome e o
      **e-mail institucional cadastrado em texto claro** e o botão que dispara o envio — que acontece
      **só por POST**: abrir a tela não emite link nem mensagem alguma.
- [ ] RF sem conta ativa exibe a tarja "Não há conta ativa para este RF"; RF **em primeiro acesso**
      (`senha_provisoria=True`) exibe a tarja dizendo que a entrada dele é pela senha de uso único,
      o caminho do primeiro login e o acionador de **reemissão do código**, que nasce
      **indisponível** — a rota dele é da SPEC da reemissão (§4). Nos dois casos não há acionador de
      envio de link, e o POST **não emite link nem mensagem** — a recusa é da rota, não da ausência
      do botão.
- [ ] A mensagem enviada declara que a redefinição foi **solicitada para a conta do servidor**, traz o
      **botão do link**, diz que o link é de **uso único** e por quanto tempo vale, e instrui a
      **ignorar a mensagem** quem não fez o pedido.
- [ ] Abrir o link autentica o servidor e o leva à tela de definição de senha
      (`autenticacao:definir_senha`) **sem exigir a senha atual**.
- [ ] O link vale **uma vez**: reabri-lo depois de consumido, abri-lo depois de vencido o prazo ou
      adulterar qualquer parte dele responde **410**, com a tela de link inválido oferecendo novo
      pedido, e **não** autentica ninguém.
- [ ] Gravada a nova senha por este caminho, a sessão é **encerrada** e o servidor é levado à tela de
      login, como no primeiro acesso.
- [ ] Pedido repetido dentro de **2 minutos** de um envio bem-sucedido **não chama o SMTP**: a tela
      diz que a mensagem acabou de sair, o acionador de envio fica indisponível e a **contagem
      regressiva** corre até liberá-lo sozinho. Passada a janela, o reenvio entrega o **mesmo link**
      enquanto ele valer; expirado, consumido ou com a senha já trocada, o pedido emite um link novo.
- [ ] Com `EMAIL_ENVIO_HABILITADO` **desligado**, a tela de confirmação exibe o **link em texto
      claro** com o botão de copiar e a tarja declarando que a exibição existe só para
      desenvolvimento; com o envio **ligado**, o link **não existe no HTML** da resposta; falha de
      entrega no SMTP devolve a tarja de recusa em português, também sem link em tela.
- [ ] O design da tela de recuperação, da tela de confirmação, da tela de link inválido e do
      acionador gravado foi aprovado no **mock**, e as peças novas foram portadas para
      `static/src/tema-dimap.dev.css` e para o styleguide antes de qualquer template usá-las.
- [ ] A página do servidor exibe o acionador **"Encerrar sessão"** — o `.btn-etched-swell` já
      aprovado no mock desta SPEC, sem peça nova — **só para quem vê o próprio perfil**, no fim do
      painel, em **linha própria abaixo da fileira de ações** e **centralizado** com ela, como
      último gesto da página.
- [ ] A rota `/logout/` **só encerra a sessão por POST de sessão autenticada**: GET responde **405**
      sem tocar na sessão, e POST sem o token CSRF daquela sessão é recusado com **403**. É o que
      valida que quem pede a saída é o próprio dono da sessão — uma página de terceiro, ou um
      prefetch do navegador sobre o `href`, não derruba mais ninguém. **Substitui o GET da SPEC 001.**

## 3 · Domínio
O pedido de recuperação, o endereço para onde ele vai e o que a mensagem diz. O link de uso único
não é entidade: ele é o token do `PasswordResetTokenGenerator` do `django.contrib.auth`, derivado do
estado do próprio servidor (§6).

```python
class EmailRecuperacaoInput(BaseModel):
    """O pedido do e-mail que entrega o link de redefinição. Sem conta remetente: quem envia é a
    configuração, não o caso de uso."""

    model_config = ConfigDict(frozen=True)

    nome: str
    destinatario: EmailStr
    url_recuperacao: HttpUrl
    # Vem da orquestração, como todo valor de settings: o corpo da mensagem promete o prazo que o
    # `PASSWORD_RESET_TIMEOUT` de fato cobra.
    validade_horas: int


class PedidoRecuperacaoInput(BaseModel):
    """O pedido de recuperação submetido na tela."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    # Esquema e host da requisição: o link precisa ser absoluto, e o domínio é da orquestração.
    base_url: HttpUrl
    validade_horas: int


class DestinoRecuperacaoOutput(BaseModel):
    """Para onde o link iria — o que a tela mostra antes de qualquer envio. Os três estados são
    excludentes, e cada um leva a uma tela diferente: o envio, a tarja de conta inexistente e o
    desvio para o primeiro acesso."""

    model_config = ConfigDict(frozen=True)

    rf: str
    nome: str = ""
    email: str = ""
    estado: Literal["recuperavel", "sem_conta", "primeiro_acesso"]


class EstadoRfOutput(BaseModel):
    """O estado resolvido do RF para renderização do partial do login."""

    model_config = ConfigDict(frozen=True)

    rf: str
    eh_primeiro_login: bool
    rf_encontrado: bool
    # ALTERADO nesta SPEC: campo novo. Há um link de redefinição emitido e ainda válido para este
    # RF — o partial do login avisa, para quem chegou aqui sem lembrar que pediu.
    recuperacao_em_aberto: bool = False


class LinkRecuperacaoInput(BaseModel):
    """As duas partes do link de uso único, como chegam da rota."""

    model_config = ConfigDict(frozen=True)

    uidb64: str = Field(min_length=1)
    token: str = Field(min_length=1)
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Perfil`](../../apps/user_admin/models/user.py) — o servidor ativo cujo `email`, `password` e
  `last_login` respondem para onde o link vai e por quanto tempo ele vale.
- [`RegistroFuncional`](../../apps/user_admin/schemas.py) — a forma do RF que a tela recebe pela query
  string e devolve no POST.
- [`ConteudoEmail` e os blocos](../../services/domain/email/models.py) — o vocabulário em que a
  mensagem é escrita, o mesmo do e-mail de acesso.
- [`SPEC autenticacao/002`](002-definir-e-redefinir-senha.md) — a tela de definição de senha em que
  este fluxo desemboca, e cuja decisão de exigir ou não a senha atual passa a ter duas causas (§6).
- [`SPEC criacao_usuarios/007`](../criacao_usuarios/007-senha-em-tela-sem-envio.md) — o regime de
  exibir em tela o que a caixa de entrada receberia quando o envio está desligado.

**Mock:** [003-mock-recuperacao-de-senha-por-email.html](003-mock-recuperacao-de-senha-por-email.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Aviso ao servidor de que a senha foi trocada, e a partir de qual endereço — sem dono ainda.
- Reemissão da senha de uso único para quem está em primeiro acesso e perdeu o e-mail de cadastro —
  próxima SPEC do épico; a tela desta já traz o acionador, indisponível até ele ter rota (§7).

## 5 · Peças de referência a compor
- `@services/domain/email` → `ConteudoEmail`, `Titulo`, `Paragrafo`, `Botao`, `Divisor`,
  `montar_mensagem`: os blocos e a montagem da mensagem.
- `@services/utils/smtp` → `EnviadorSmtp`, `SmtpEnvioError`, `build_smtp_config`,
  `build_smtp_retry_policy`: a conversa com o servidor de e-mail.
- `@apps/user_admin/cadastro.py` → `_entregar_senha`: o envio que trata envio desligado e recusa de
  destinatário.
- `@apps/autenticacao/services.py` → `resolver_estado_rf`: a leitura de RF ativo na tela de login.
- `@apps/autenticacao/views.py` → `BACKEND_AUTENTICACAO`: o backend explícito que o `login()` exige.
- `@services/utils/erros_formulario` → `Formulario`, `CampoDeFormulario`, `ErroBruto`,
  `TradutorDeRecusa`: a recusa em português com o controle realçado.
- `@static/src/tema-dimap.dev.css` → `.btn-etched`, `.btn-etched-swell`, `.btn-copiar`,
  `.glass-panel`, `.card-well`, `.tarja-vinculo-critica`, `.input-glass`.
- `@templates/user_admin/perfil.html` → a fileira de ações do fim do painel, com a condição
  `request.user.pk == perfil.pk` que já rege o atalho de redefinir senha.
- `django.contrib.auth.tokens` → `default_token_generator`; `django.utils.http` →
  `urlsafe_base64_encode` / `urlsafe_base64_decode`; `django.core.cache` → `cache`.
- `django.views.decorators.http` → `require_POST`; `django.contrib.auth.decorators` →
  `login_required`: os dois já em uso nas demais rotas do app.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `erros-de-formulario`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`config/settings.py`** — o prazo do link, lido de um lugar só.
```python
RECUPERACAO_SENHA_VALIDADE_HORAS = 1
# O nome é do Django: é ele que o `PasswordResetTokenGenerator.check_token` consulta.
PASSWORD_RESET_TIMEOUT = RECUPERACAO_SENHA_VALIDADE_HORAS * 3600
```

**`apps/core/entrega_email.py`** — o envio que hoje é privado do cadastro, parametrizado pela
mensagem. `criar_servidor` passa a compô-lo, sem mudança de comportamento: `_entregar_senha` fica só
com a montagem, e as fixtures que trocam o enviador por um fake (`tests/apps/user_admin/
test_cadastro.py` e `tests/apps/user_admin/views/test_criar_servidor.py`) passam a apontar para este
módulo — a suíte `banco` do cadastro roda verde antes de `implementado: true`.
```python
def entregar_email(mensagem: MensagemEmail) -> bool:
    """True quando a mensagem foi de fato entregue ao SMTP; False quando o envio está desligado por
    configuração — que não é falha. Destinatário recusado e servidor fora do ar são o mesmo desfecho
    para quem chamou: a mensagem não chegou, e vira exceção."""
    if not settings.EMAIL_ENVIO_HABILITADO:
        print(f"[SMTP desligado] para={mensagem.destinatarios} assunto={mensagem.assunto}")
        return False
    enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
    resultado = enviador(mensagem)
    if resultado.destinatarios_recusados:
        raise SmtpEnvioError(f"Destinatário recusado: {mensagem.destinatarios}.")
    return True
```

**`services/domain/email/recuperacao.py`** — o que a mensagem diz.
```python
ASSUNTO_RECUPERACAO = "DIMAP GeoCoder — redefinição de senha"


class MontarEmailRecuperacao:
    """Callable: o pedido vira o que o e-mail vai dizer."""

    def __call__(self, pedido: EmailRecuperacaoInput) -> ConteudoEmail:
        return ConteudoEmail(
            assunto=ASSUNTO_RECUPERACAO,
            blocos=(
                Titulo(texto="Redefinição de senha"),
                Paragrafo(
                    texto=(
                        f"{pedido.nome}, foi solicitada a redefinição da senha da sua conta no "
                        "DIMAP GeoCoder."
                    )
                ),
                Botao(rotulo="Definir uma nova senha", url=pedido.url_recuperacao),
                # O prazo e o uso único não são detalhe de rodapé: são o que explica o link parar
                # de funcionar depois — e o que evita o segundo pedido por engano.
                Paragrafo(
                    texto=(
                        "O link é de uso único e vale por "
                        f"{pedido.validade_horas} hora(s): depois de aberto uma vez, ele deixa de "
                        "funcionar."
                    )
                ),
                Divisor(),
                Paragrafo(
                    texto=(
                        "Se não foi você quem pediu, ignore esta mensagem: sua senha continua a "
                        "mesma."
                    )
                ),
            ),
            rodape="Mensagem automática do DIMAP GeoCoder. Não é necessário responder.",
        )


montar_email_recuperacao = MontarEmailRecuperacao()
```

**`apps/autenticacao/recuperacao.py`** — a emissão e o consumo do link de uso único.
```python
# O gerador do contrib.auth deriva o token de pk + hash da senha + `last_login` + e-mail + carimbo
# de tempo. É `last_login` que faz o uso único: o consumo do link autentica o servidor, o
# `last_login` muda e o mesmo token deixa de conferir (Caveats).
SESSAO_SENHA_SEM_ATUAL = "recuperacao_dispensa_senha_atual"
ERRO_ENTREGA = "Não foi possível enviar o link para {email}. Tente novamente em instantes."


@dataclass(frozen=True)
class DesfechoRecuperacao:
    """Recado do ato para a view, no molde do `DesfechoCadastro`: não é DTO de domínio e não cruza
    fronteira de serviço."""

    email: str
    enviado: bool = False
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    # Segundos que faltam para o próximo envio. Maior que zero é a etiqueta de "nada saiu agora
    # porque a mensagem anterior acabou de sair" — e é o número que a tela mostra.
    espera_segundos: int = 0
    # Preenchido SÓ quando o envio está desligado — `None` é a etiqueta de "foi entregue", e é ela
    # que a tela lê para decidir se mostra o link (SPEC criacao_usuarios/007).
    link_a_exibir: str | None = None


CHAVE_TOKEN = "recuperacao_senha:{pk}"
CHAVE_JANELA = "recuperacao_senha_janela:{pk}"
JANELA_REENVIO_SEGUNDOS = 120


def _espera_do_reenvio(perfil: Perfil) -> int:
    """O valor guardado é o instante em que o envio libera, e não um sinalizador: sem ele a tela
    diria "aguarde" sem saber quanto, e o cache do Django não conta o tempo que falta para uma
    chave expirar."""
    liberado_em = cache.get(CHAVE_JANELA.format(pk=perfil.pk))
    if liberado_em is None:
        return 0
    return max(0, int(liberado_em - time.time()))


def _armar_janela(perfil: Perfil) -> None:
    # Só depois de a mensagem sair de fato: a janela protege caixa de entrada, e com o envio
    # desligado não há nenhuma a proteger — segurar ali só atrapalharia o desenvolvimento.
    cache.set(
        CHAVE_JANELA.format(pk=perfil.pk),
        time.time() + JANELA_REENVIO_SEGUNDOS,
        timeout=JANELA_REENVIO_SEGUNDOS,
    )


def _token_vigente(perfil: Perfil) -> str | None:
    """O cache é palpite, não autoridade: quem diz se o link ainda vale é o gerador, que já sabe da
    senha trocada e do link consumido. Entrada perdida (reinício, outro processo) só custa um link
    novo — e o primeiro consumo mata todos eles de uma vez."""
    guardado = cache.get(CHAVE_TOKEN.format(pk=perfil.pk))
    if guardado is None or not default_token_generator.check_token(perfil, guardado):
        return None
    return str(guardado)


def _token_do_pedido(perfil: Perfil) -> str:
    """Enquanto o link anterior vale, o pedido repetido reenvia o MESMO — o token embute o próprio
    carimbo de tempo, então reemitir é a única forma de gerar outro, e cada reemissão deixaria mais
    um link de portador vivo na caixa de entrada."""
    vigente = _token_vigente(perfil)
    if vigente is not None:
        return vigente
    token = default_token_generator.make_token(perfil)
    # O TTL é a validade do próprio link: entrada que sobrevive ao token só devolveria um link morto
    # para o `check_token` recusar no pedido seguinte.
    cache.set(CHAVE_TOKEN.format(pk=perfil.pk), token, timeout=settings.PASSWORD_RESET_TIMEOUT)
    return token


def ha_pedido_em_aberto(perfil: Perfil) -> bool:
    """A pergunta da tela de login. Só leitura: perguntar não pode ter como efeito colateral a
    emissão de um link."""
    return _token_vigente(perfil) is not None


def montar_link_recuperacao(perfil: Perfil, base_url: HttpUrl) -> str:
    caminho = reverse(
        "autenticacao:recuperar_senha",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(perfil.pk)),
            "token": _token_do_pedido(perfil),
        },
    )
    return urljoin(str(base_url), caminho)


def _perfil_recuperavel(rf: str) -> Perfil | None:
    """`senha_provisoria=False` é a metade que importa da regra: quem está em primeiro acesso já tem
    uma credencial de uso único esperando na caixa de entrada, e emitir uma segunda porta para o
    mesmo estado é dobrar a superfície de entrada sem dobrar a garantia."""
    return Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=False).first()


def enviar_link_recuperacao(pedido: PedidoRecuperacaoInput) -> DesfechoRecuperacao:
    perfil = _perfil_recuperavel(pedido.rf)
    if perfil is None:
        # Conta inexistente, inativa ou em primeiro acesso: nenhuma delas monta e-mail ou gera link.
        # A tela já disse qual é o caso antes do POST; aqui o que importa é não emitir nada.
        return DesfechoRecuperacao(email="")
    espera = _espera_do_reenvio(perfil)
    if espera:
        # Sai antes de montar link, conteúdo e mensagem: dentro da janela o pedido não produz nada,
        # nem trabalho nem token.
        return DesfechoRecuperacao(email=perfil.email, enviado=True, espera_segundos=espera)
    link = montar_link_recuperacao(perfil, pedido.base_url)
    conteudo = montar_email_recuperacao(
        EmailRecuperacaoInput(
            nome=perfil.nome,
            destinatario=perfil.email,
            url_recuperacao=link,
            validade_horas=pedido.validade_horas,
        )
    )
    try:
        entregue = entregar_email(montar_mensagem(conteudo, destinatarios=(perfil.email,)))
    except SmtpEnvioError:
        return DesfechoRecuperacao(email=perfil.email, recusa=_recusa_da_entrega(perfil.email))
    if entregue:
        _armar_janela(perfil)
    return DesfechoRecuperacao(
        email=perfil.email,
        enviado=entregue,
        link_a_exibir=None if entregue else link,
    )


def resolver_perfil_do_link(link: LinkRecuperacaoInput) -> Perfil | None:
    """Link vencido, já consumido, adulterado, de servidor inativo ou de servidor que voltou ao
    primeiro acesso: todos devolvem None. Quem distingue o motivo é o log, não a tela — a tela
    oferece pedir outro.

    A mesma regra de emissão vale no consumo: o estado da conta pode ter mudado entre um e outro, e
    quem decide é a rota que executa, não a que ofereceu."""
    try:
        pk = urlsafe_base64_decode(link.uidb64).decode()
        perfil = Perfil.objects.get(pk=pk, is_active=True, senha_provisoria=False)
    except (ValueError, TypeError, Perfil.DoesNotExist):
        return None
    if not default_token_generator.check_token(perfil, link.token):
        return None
    return perfil
```

**`apps/autenticacao/urls.py`** — as rotas, com o token no fim do caminho.
```python
urlpatterns += [
    path("esqueci-minha-senha/", views.esqueci_senha_view, name="esqueci_senha"),
    path("esqueci-minha-senha/enviar/", views.enviar_link_view, name="enviar_link_recuperacao"),
    path(
        "recuperar-senha/<str:uidb64>/<str:token>/",
        views.recuperar_senha_view,
        name="recuperar_senha",
    ),
]
```

**`apps/autenticacao/views.py`** — a orquestração do pedido e do consumo.
```python
def esqueci_senha_view(request: HttpRequest) -> HttpResponse:
    destino = resolver_destino_recuperacao(ConsultaRfInput(rf=request.GET.get("rf", "").strip()))
    return render(
        request,
        "autenticacao/esqueci_senha.html",
        {"destino": destino, **contexto_fundo_admin()},
    )


@require_POST
def enviar_link_view(request: HttpRequest) -> HttpResponse:
    desfecho = enviar_link_recuperacao(
        PedidoRecuperacaoInput(
            rf=request.POST.get("rf", "").strip(),
            base_url=request.build_absolute_uri("/"),
            validade_horas=settings.RECUPERACAO_SENHA_VALIDADE_HORAS,
        )
    )
    status = 422 if desfecho.recusa.mensagens else 200
    return render(
        request,
        "autenticacao/partials/_envio_recuperacao.html",
        {"desfecho": desfecho},
        status=status,
    )


def recuperar_senha_view(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    perfil = resolver_perfil_do_link(LinkRecuperacaoInput(uidb64=uidb64, token=token))
    if perfil is None:
        return render(
            request,
            "autenticacao/link_invalido.html",
            contexto_fundo_admin(),
            status=410,
        )
    # A ordem importa: `login()` atualiza `last_login`, que entra no hash do token — é esta linha
    # que queima o link, e ela só pode rodar depois de o token ter conferido.
    login(request, perfil, backend=BACKEND_AUTENTICACAO)
    request.session[SESSAO_SENHA_SEM_ATUAL] = True
    return redirect("autenticacao:definir_senha")
```

**`apps/autenticacao/views.py`** — a tela de definir senha da SPEC 002, ALTERADA: a dispensa da senha
atual deixa de ser sinônimo de primeiro acesso. O resto das views permanece como está — o delta é a
origem do booleano e o nome dele, não o fluxo, que já está implementado e testado. O rename alcança
`views.py`, o parâmetro de `gravar_senha` em `senha.py` e as ramificações de
`definir_senha.html`; **não** alcança o `eh_primeiro_login` de
[`EstadoRfOutput`](#3--domínio), que é outro estado — o do RF na tela de login — e cujo nome
continua certo.
```python
def _dispensa_senha_atual(request: HttpRequest) -> bool:
    """Senha de uso único do primeiro acesso e link de recuperação chegam no mesmo lugar: nos dois
    casos não existe senha atual que o servidor consiga informar. O `or` só alarga o que a SPEC 002
    já fazia — quem vem do OTP segue caindo no mesmo ramo."""
    perfil = cast(Perfil, request.user)
    return perfil.senha_provisoria or request.session.get(SESSAO_SENHA_SEM_ATUAL, False)


@login_required
def definir_senha_view(request: HttpRequest) -> HttpResponse:
    # ALTERADO nesta SPEC: `eh_primeiro_login` lido só do model vira `dispensa_senha_atual`, com as
    # duas causas. O `contexto_fundo_admin()` e a constante do template continuam como estão.
    contexto = {"dispensa_senha_atual": _dispensa_senha_atual(request), **contexto_fundo_admin()}
    return render(request, TEMPLATE_DEFINIR_SENHA, contexto)


@login_required
@require_POST
def gravar_senha_view(request: HttpRequest) -> HttpResponse:
    perfil = cast(Perfil, request.user)
    # ALTERADO nesta SPEC: era `perfil.senha_provisoria`. A gravação segue delegada ao
    # `gravar_senha` de `apps/autenticacao/senha.py`, cujo parâmetro muda de nome junto.
    dispensa = _dispensa_senha_atual(request)
    desfecho = gravar_senha(perfil, dispensa, request.POST)
    if not desfecho.sucesso:
        contexto = {
            "dispensa_senha_atual": dispensa,
            "recusa": desfecho.recusa,
            **contexto_fundo_admin(),
        }
        return render(request, TEMPLATE_DEFINIR_SENHA, contexto, status=422)
    if dispensa:
        # `logout` esvazia a sessão inteira, e com ela a chave da recuperação: a sessão seguinte
        # nasce com senha definitiva e exigindo a senha atual, como qualquer outra.
        logout(request)
        return redirect("autenticacao:login")
    update_session_auth_hash(request, perfil)
    return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk}))
```

**`static/src/tema-dimap.dev.css`** — o acionador gravado que incha no hover, variante do
`.btn-etched` já existente.
```css
/* ÁTOMO. Variante do .btn-etched (SPEC autenticacao/003): sem crachá de botão, porque o gesto é
   secundário — a afordância é a gravação enchendo de água e o corpo crescendo um pouco sob o
   ponteiro. O .btn-etched segue intocado: quem incha é só quem pede esta classe. */
.btn-etched-swell {
  @apply transition-transform duration-300 origin-center;
}
.btn-etched-swell:hover {
  @apply scale-[1.06];
}
```

**`templates/autenticacao/partials/_envio_recuperacao.html`** — as faces da resposta do POST, alvo
HTMX do formulário de pedido.
```html
{# A espera vem do servidor em segundos e o contador só a consome: quem recusa o envio dentro da #}
{# janela é a rota, e o botão indisponível é afordância, não a regra.                            #}
{% if desfecho.recusa.mensagens %}
  <div class="tarja-vinculo tarja-vinculo-critica">…</div>
{% elif desfecho.espera_segundos %}
  <div class="card-well ..." data-contagem-reenvio="{{ desfecho.espera_segundos }}">
    A mensagem acabou de ser enviada para <strong>{{ desfecho.email }}</strong>. Se ela não chegar,
    peça outra em <span data-reenvio-relogio>{{ desfecho.espera_segundos }} s</span>.
  </div>
{% elif desfecho.link_a_exibir %}
  {# Envio desligado: o link em tela, com o .btn-copiar e a tarja de desenvolvimento (SPEC 007). #}
{% else %}
  <div class="card-well ...">Link enviado para <strong>{{ desfecho.email }}</strong>.</div>
{% endif %}
```

**`static/src/js/ui/contagem_reenvio.js`** — o relógio do acionador, no molde do `olhinho_senha.js`.
```js
// Contagem regressiva do reenvio (SPEC autenticacao/003): estado visual de um controle, aprovado
// pelo usuário. Nenhum estado de domínio mora aqui — a espera chega pronta do servidor, e é a rota
// que recusa o envio dentro da janela; o botão indisponível só evita o clique que já seria negado.
function correr(painel) {
  const acionador = document.querySelector("[data-reenvio-acionador]");
  const relogio = painel.querySelector("[data-reenvio-relogio]");
  let restante = Number(painel.dataset.contagemReenvio);
  acionador.disabled = true;
  const passo = setInterval(() => {
    // O painel é trocado por HTMX a cada pedido: sem esta guarda o relógio antigo segue correndo
    // contra um nó solto e reabilita um botão que o painel novo já governava.
    if (!painel.isConnected) return clearInterval(passo);
    restante -= 1;
    relogio.textContent = `${restante} s`;
    if (restante > 0) return;
    clearInterval(passo);
    acionador.disabled = false;
  }, 1000);
}

// A marca de montagem é a mesma do olhinho: `htmx:afterSwap` também alcança painel já montado.
function montar() {
  document
    .querySelectorAll("[data-contagem-reenvio]:not([data-contagem-montada])")
    .forEach((painel) => {
      painel.dataset.contagemMontada = "true";
      correr(painel);
    });
}

document.addEventListener("DOMContentLoaded", montar);
document.addEventListener("htmx:afterSwap", montar);
```

**`apps/autenticacao/services.py`** — a resolução do RF na tela de login, ALTERADA: o estado passa a
dizer se há link em aberto.
```python
def resolver_estado_rf(consulta: ConsultaRfInput) -> EstadoRfOutput:
    try:
        perfil = Perfil.objects.get(rf=consulta.rf, is_active=True)
        return EstadoRfOutput(
            rf=consulta.rf,
            eh_primeiro_login=perfil.senha_provisoria,
            rf_encontrado=True,
            # ALTERADO nesta SPEC: campo novo. Quem está em primeiro acesso nunca tem link em
            # aberto — a emissão o recusa —, e a consulta ao cache nem chega a acontecer.
            recuperacao_em_aberto=not perfil.senha_provisoria and ha_pedido_em_aberto(perfil),
        )
    except Perfil.DoesNotExist:
        # RF inexistente devolve o mesmo formato do RF já ativo (SPEC 001, anti-enumeração).
        return EstadoRfOutput(rf=consulta.rf, eh_primeiro_login=False, rf_encontrado=False)
```

**`templates/autenticacao/partials/_campo_login_dinamico.html`** — o acionador e o aviso no ramo de
senha.
```html
<button type="submit" class="btn btn-onsen w-full text-base font-bold shadow-md">Entrar</button>
{# O RF já resolvido viaja na query string: a tela de recuperação precisa dele para dizer para  #}
{# qual e-mail o link vai.                                                                      #}
<a href="{% url 'autenticacao:esqueci_senha' %}?rf={{ estado.rf }}"
   class="btn-etched btn-etched-swell etched self-center">
  Esqueci minha senha
</a>
{# Cor semântica de informação, que é o que o daisyUI reserva para estado do sistema: não é erro #}
{# nem alerta, é um recado. A peça final sai do mock.                                           #}
{% if estado.recuperacao_em_aberto %}
  <div class="alert alert-info alert-soft text-xs">
    Já pedimos uma redefinição de senha para este RF: o link está no seu e-mail institucional.
  </div>
{% endif %}
```

**`apps/autenticacao/views.py`** — a saída, agora com as duas guardas. `logout()` só sabe encerrar
a sessão de quem faz a requisição: a identidade não é conferida contra um `pk` no corpo — seria
teatro —, e sim pelo par sessão autenticada + token CSRF, que é o que prova que o POST saiu de uma
página servida àquela sessão.
```python
@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("autenticacao:login")
```

**`templates/user_admin/perfil.html`** — o acionador, irmão da fileira de ações e não parte dela:
sair é saída da sessão, não ação sobre o perfil. O `<form>` é quem recebe o `self-center` porque o
painel é `flex flex-col` — o alinhamento é do item, e a linha própria já vem da coluna; o
`.btn-etched` já nasce `inline-flex`, e vale igual em `<button>`.
```html
{% if request.user.pk == perfil.pk %}
  <form method="post"
        action="{% url 'autenticacao:logout' %}"
        class="self-center">
    {% csrf_token %}
    <button type="submit"
            class="btn-etched btn-etched-swell etched">Encerrar sessão</button>
  </form>
{% endif %}
```

## 7 · Caveats
A tela de recuperação mostra o e-mail institucional em texto claro a quem informar um RF de conta
ativa, e diz explicitamente quando o RF não tem conta. A decisão é do usuário e vale para um sistema
interno: sem ver o endereço, quem tem e-mail cadastrado errado fica esperando uma mensagem que nunca
chega. O custo é que a enumeração de RFs válidos que a SPEC 001 fecha na tela de login fica aberta
aqui, junto com o e-mail do servidor — e o aviso de link em aberto, no próprio login, conta a um
anônimo que aquele RF pediu redefinição.

Servidor em primeiro acesso não recupera senha por este caminho: a emissão e o consumo do link exigem
`senha_provisoria=False`. A decisão mantém uma porta por estado da conta — quem nunca entrou já tem
uma credencial de uso único emitida, e uma segunda porta para o mesmo estado dobra a superfície de
entrada sem dobrar a garantia. O custo é que quem perdeu o e-mail de cadastro não tem saída
self-service e depende de quem administra o cadastro, enquanto a reemissão da senha de uso único não
tiver dono.

O uso único não tem tabela nem coluna: o token do `default_token_generator` deriva também de
`last_login`, e o consumo do link autentica o servidor, muda esse carimbo e derruba o próprio token.
A decisão evita um model de token com data de expiração, limpeza e migração para um fluxo de dezenas
de usuários. O custo é depender de um detalhe do gerador do Django — se uma versão futura tirar
`last_login` do hash, o link deixa de ser de uso único e passa a valer até vencer o prazo, sem que
teste nenhum de tela acuse.

A contagem regressiva que reabilita o acionador de envio é estado visual de controle em JavaScript,
com aval explícito do usuário (CLAUDE.md §7.2). A decisão evita a tarja que congela — sem relógio, o
número renderizado envelhece na tela e o único jeito de saber quanto falta é clicar, que é o gesto
que a janela existe para conter. O custo é que o relógio não é coberto pela suíte, e quem editar o
DOM reabilita o botão antes da hora — sem consequência, porque a recusa do envio é da rota.

O token emitido e a janela de reenvio ficam no cache do Django — primeiro uso do cache no projeto,
sobre o `LocMemCache` padrão, que é por processo e não sobrevive a reinício. A decisão evita guardar
um token de portador e um carimbo de envio em colunas do `Perfil`, com a migração e a limpeza que
viriam junto. O custo é que as duas garantias são oportunistas: pedido que caia em outro worker, ou
depois de um restart, emite um segundo link válido e escapa da janela — os links todos continuam
morrendo no primeiro consumo, mas o limite de envio não é barreira contra quem insiste, e sim
proteção contra o clique repetido.

A dispensa da senha atual na tela de definição passa a ter duas causas: a marca `senha_provisoria` no
model e uma chave na sessão gravada pelo consumo do link. A decisão mantém o primeiro acesso e a
recuperação desembocando no mesmo template e na mesma view, sem duplicar formulário. O custo é que
quem alterar uma das causas precisa lembrar da outra, e o modo do formulário deixa de ser legível
apenas pelo banco.

O logout deixa de responder a GET, e com isso o snippet e o teste da SPEC 001 — que acionavam a
rota por `client.get` — passam a descrever um comportamento que não existe mais; o teste é reescrito
aqui, o snippet de lá fica desatualizado até a 001 ser versionada. A decisão é fechar a rota no
momento em que ela ganha gatilho na interface: enquanto era alcançável só digitando a URL, o GET não
tinha como ser disparado por terceiro, e um `<a href>` o entrega a qualquer `<img src="/logout/">` de
página alheia e a qualquer prefetch do navegador. O custo é a divergência entre duas SPECs do mesmo
épico até a próxima edição da 001.

Com o envio de e-mail desligado, o link aparece na tela de quem pediu, sem autenticação — mesmo
regime da SPEC criacao_usuarios/007 para a senha de cadastro. A decisão mantém o fluxo exercitável de
ponta a ponta em ambiente sem SMTP. O custo é que, em desenvolvimento, qualquer pessoa que informe um
RF válido redefine a senha daquele servidor.

## 8 · Testes (TDD)
- `test_pedido_com_rf_ativo_entrega_mensagem_com_o_link` — POST em `/esqueci-minha-senha/enviar/`
  monta a mensagem para o e-mail cadastrado e a entrega ao SMTP. *(marker `banco`)*
- `test_pedido_para_rf_nao_recuperavel_nao_entrega_nada` — RF inexistente, inativo ou em primeiro
  acesso não gera link nem chama o envio, e a tela devolve a tarja do caso. *(marker `banco`)*
- `test_login_avisa_pedido_de_redefinicao_em_aberto` — com link emitido e válido, o partial dinâmico
  do login traz o aviso para aquele RF, e deixa de trazê-lo depois de o link ser consumido.
  *(marker `banco`)*
- `test_email_de_recuperacao_diz_uso_unico_prazo_e_como_ignorar` — o `ConteudoEmail` montado traz o
  botão com o link, o aviso de uso único com o prazo e a instrução de ignorar.
- `test_link_valido_autentica_e_leva_a_definir_senha_sem_senha_atual` — GET no link redireciona para
  `/definir-senha/`, com sessão autenticada e o formulário sem o campo de senha atual.
  *(marker `banco`)*
- `test_link_reaberto_apos_consumo_responde_410_sem_autenticar` — o mesmo link, aberto uma segunda
  vez, cai na tela de link inválido e não abre sessão. *(marker `banco`)*
- `test_link_vencido_ou_adulterado_responde_410` — token além de `PASSWORD_RESET_TIMEOUT`, e token
  válido de um servidor com o `uidb64` de outro, são recusados. *(marker `banco`)*
- `test_pedido_repetido_segura_o_envio_na_janela_e_reaproveita_o_link_depois` — o segundo POST dentro
  de `JANELA_REENVIO_SEGUNDOS` não chama o envio e devolve a espera; vencida a janela, a mensagem sai
  com o mesmo token, e só depois de o link ser consumido é que o token muda. *(marker `banco`)*
- `test_gravar_senha_pela_recuperacao_encerra_a_sessao_e_leva_ao_login` — concluída a definição, a
  sessão é encerrada e a resposta redireciona para o login. *(marker `banco`)*
- `test_com_envio_desligado_o_link_aparece_na_tela_e_com_envio_ligado_nao` — a resposta do POST
  carrega o link no HTML só quando `EMAIL_ENVIO_HABILITADO` está desligado. *(marker `banco`)*
- `test_logout_encerra_a_sessao_por_post_e_recusa_get` — POST em `/logout/` encerra a sessão e
  redireciona ao login; GET responde 405 e a sessão continua de pé. Reescreve o teste homônimo da
  SPEC 001. *(marker `banco`)*
- `test_logout_sem_o_token_csrf_nao_encerra_a_sessao` — POST de cliente com CSRF exigido, sem o
  token, responde 403 e deixa a sessão intacta. *(marker `banco`)*
- `test_atalhos_da_propria_conta_so_aparecem_para_o_proprio_servidor` — a página do servidor traz os
  caminhos de redefinir senha e de encerrar sessão para o dono do perfil, e não os traz para um
  colega. Estende o teste da SPEC user_admin/017. *(marker `banco`)*
