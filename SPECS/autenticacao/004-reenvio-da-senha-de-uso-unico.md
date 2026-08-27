---
spec: autenticacao/004
versao: v1
atualizado_em: 2026-08-27
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC autenticacao/004 — Reenvio da senha de uso único do primeiro acesso

## 1 · User story
O servidor da DIMAP que não recebeu ou perdeu o e-mail do cadastro pede, da própria tela de login,
que a senha de uso único seja enviada de novo ao seu e-mail institucional, para concluir o primeiro
acesso sem depender de quem administra o cadastro.

## 2 · Condições de pronto
- [ ] O ramo de **primeiro acesso** do partial dinâmico do login exibe o acionador **"Reenviar senha
      de uso único"**, na mesma forma e no mesmo lugar em que o ramo de senha exibe "Esqueci minha
      senha", levando o RF já digitado para a tela de recuperação.
- [ ] A tela de recuperação, no estado de primeiro acesso, mantém em **destaque** o acionador de
      ativar a conta e passa a **enviar de fato** pelo acionador de reenvio, que deixa de nascer
      indisponível; a tela do **código de uso único** (`/primeiro-login/`) oferece o mesmo reenvio
      **sem sair dela**, e o servidor digita ali mesmo o código recebido.
- [ ] Pedido repetido **reenvia a mesma senha** ao **e-mail cadastrado** do servidor, sem escrever
      nada no cadastro, enquanto ela continuar sendo a credencial da conta e o pedido anterior tiver
      sido feito nos últimos **5 minutos**; fora disso emite uma **senha nova** de oito dígitos,
      gravada como provisória, e só então a anterior **deixa de autenticar** — quem troca a
      credencial é o pedido, nunca o relógio.
- [ ] Digitado na tela do código um OTP que **foi substituído** por um reenvio, a recusa diz que
      aquele código foi trocado e manda usar a mensagem mais recente; erro de digitação continua
      recebendo a recusa genérica de código inválido.
- [ ] Falha na entrega — servidor SMTP indisponível ou destinatário recusado — devolve o motivo em
      português na tela e **não troca a senha**: a anterior segue valendo.
- [ ] RF **sem conta ativa**, com **senha definitiva** ou **sem e-mail cadastrado** não envia
      mensagem nem toca em credencial alguma: a recusa é da rota, não da ausência do acionador na
      tela.
- [ ] Pedido repetido dentro de **2 minutos** de um envio bem-sucedido **não chama o SMTP**: a tela
      diz que a mensagem acabou de sair, o acionador fica indisponível e a **contagem regressiva**
      corre até liberá-lo sozinho.
- [ ] Com `EMAIL_ENVIO_HABILITADO` **desligado**, a senha enviada aparece no **mesmo modal** do
      cadastro de servidor, em texto claro, com o botão de copiar e a tarja de desenvolvimento; com
      o envio **ligado**, a senha **não existe no HTML** da resposta.
- [ ] A senha enviada continua **fora do banco em texto claro**, fora dos logs e fora do registro de
      qualquer ato.
- [ ] O design das duas telas e do acionador foi aprovado no **mock**, e as peças novas foram
      portadas para `static/src/tema-dimap.dev.css` e para o styleguide antes de qualquer template
      usá-las.

## 3 · Domínio
Nenhuma ontologia nova: a credencial reenviada é a mesma senha temporária do cadastro, e o estado
que a autoriza é o `senha_provisoria` do servidor. O que nasce aqui é o pedido — e a cópia da senha
enviada, que sobrevive à resposta para que o pedido seguinte a repita em vez de trocá-la (§6).

```python
class ReenvioSenhaInput(BaseModel):
    """O pedido de reenvio da senha de uso único, submetido pela tela de recuperação ou pela tela
    do código."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    # O host de onde o convite parte é da orquestração, como no cadastro: o e-mail de acesso leva
    # a URL do sistema, e nem o domínio nem o cadastro sabem em que host ele roda.
    url_acesso: HttpUrl
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Perfil`](../../apps/user_admin/models/user.py) — "este RF está ativo, em primeiro acesso e com
  e-mail para onde mandar?"; é o mesmo campo `senha_provisoria` que o login já lê.
- [`gerar_senha_temporaria` e `PoliticaSenhaTemporaria`](../../services/utils/senha.py) — os oito
  dígitos sorteados, idênticos aos do cadastro.
- [`montar_email_acesso` e `EmailAcessoInput`](../criacao_usuarios/003-email-de-acesso.md) — "o que a
  mensagem diz?"; a mesma do cadastro, com a senha nova.
- [`entregar_email`](../autenticacao/003-recuperacao-de-senha-por-email.md) — a conversa com o SMTP,
  com a guarda de `EMAIL_ENVIO_HABILITADO`.
- [SPEC autenticacao/003](003-recuperacao-de-senha-por-email.md) — a tela de recuperação, o desvio
  para o primeiro acesso e a janela de 2 minutos entre envios.
- [SPEC criacao_usuarios/007](../criacao_usuarios/007-senha-em-tela-sem-envio.md) — o modal que
  mostra em tela o que a caixa de entrada receberia quando o envio está desligado.

**Mock:** [004-mock-reenvio-da-senha-de-uso-unico.html](004-mock-reenvio-da-senha-de-uso-unico.html) —
leia a skill `mock`.

## 4 · Fora de escopo
- Reenviar a senha a pedido de quem administra o cadastro, a partir da página do servidor, como ato
  registrado — sem dono ainda.
- Registro em banco das mensagens enviadas (para quem, quando, com que desfecho) — sem dono ainda.
- Bloqueio por excesso de pedidos vindos do mesmo endereço, além da janela entre envios — sem dono
  ainda.
- Queimar a senha de uso único no instante em que ela é validada, e não quando a senha definitiva é
  gravada: hoje quem valida o código e abandona a tela seguinte volta a entrar com ele — sem dono
  ainda.

## 5 · Peças de referência a compor
- `@apps/autenticacao/recuperacao.py` → `_espera_do_reenvio` e `_armar_janela`: a janela entre envios; `resolver_destino_recuperacao`: o estado que a tela lê; `_token_vigente` e `_token_do_pedido`: repetir o que está guardado em vez de emitir outro, conferindo contra a fonte e não contra o cache.
- `django.contrib.auth.hashers` → `check_password`: conferir um código contra um hash solto, fora do `Perfil`.
- `@apps/core/entrega_email.py` → `entregar_email`: o envio com a guarda de `EMAIL_ENVIO_HABILITADO`.
- `@apps/user_admin/cadastro.py` → `_entregar_senha`: a montagem do e-mail de acesso a partir do servidor e da senha.
- `@services/utils/senha.py` → `gerar_senha_temporaria`: o sorteio criptográfico dos oito dígitos.
- `@templates/user_admin/partials/_modal_senha_desenvolvimento.html` → o modal da senha em tela, com a tarja de desenvolvimento e o `.btn-copiar`.
- `@templates/autenticacao/partials/_envio_recuperacao.html` → as faces da resposta de um pedido de envio: recusa, espera com contagem, exibição em tela, sucesso.
- `@static/src/js/ui/contagem_reenvio.js` e `@static/src/js/ui/copiar_senha.js` → o relógio do acionador e a cópia para a área de transferência.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `erros-de-formulario`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`config/settings.py`** e **`.env.example`** — os três prazos, no molde das demais chaves. Nenhum
deles tem valor diferente por ambiente hoje; ficam configuráveis porque são os números que se
ajustam quando o SMTP ou a caixa de entrada real disserem outra coisa.
```python
    # Reenvio de credencial de primeiro acesso (SPEC autenticacao/004).
    janela_reenvio_segundos: int = Field(default=120, alias="JANELA_REENVIO_SEGUNDOS")
    prazo_mesma_senha_segundos: int = Field(default=300, alias="PRAZO_MESMA_SENHA_SEGUNDOS")
    prazo_senha_anterior_segundos: int = Field(
        default=24 * 3600,
        alias="PRAZO_SENHA_ANTERIOR_SEGUNDOS",
    )


# Reenvio de credencial (apps.autenticacao.janela_envio e apps.autenticacao.reenvio).
JANELA_REENVIO_SEGUNDOS = _env.janela_reenvio_segundos
PRAZO_MESMA_SENHA_SEGUNDOS = _env.prazo_mesma_senha_segundos
PRAZO_SENHA_ANTERIOR_SEGUNDOS = _env.prazo_senha_anterior_segundos
```
```sh
# Reenvio da senha de uso único (opcional; sem a chave vale o default ao lado). Número vazio não
# entra num int — opcional aqui se escreve comentado, como as demais chaves numéricas.
# JANELA_REENVIO_SEGUNDOS=120
# PRAZO_MESMA_SENHA_SEGUNDOS=300
# PRAZO_SENHA_ANTERIOR_SEGUNDOS=86400
```

**`apps/autenticacao/janela_envio.py`** — a janela entre envios, hoje privada da recuperação, com o
nome do que ela protege: a caixa de entrada de um servidor, não um fluxo. `recuperacao.py` passa a
compô-la, sem mudança de comportamento.
```python
CHAVE_JANELA = "janela_envio_credencial:{pk}"
# Reextraído de settings, como toda configuração: o módulo referencia a constante, não o objeto.
JANELA_REENVIO_SEGUNDOS = settings.JANELA_REENVIO_SEGUNDOS


def espera_do_reenvio(perfil: Perfil) -> int:
    """O valor guardado é o instante em que o envio libera, e não um sinalizador: sem ele a tela
    diria "aguarde" sem saber quanto, e o cache do Django não conta o tempo que falta para uma
    chave expirar."""
    liberado_em = cache.get(CHAVE_JANELA.format(pk=perfil.pk))
    if liberado_em is None:
        return 0
    return max(0, int(liberado_em - time.time()))


def armar_janela(perfil: Perfil) -> None:
    # Só depois de a mensagem sair de fato: com o envio desligado não há caixa de entrada a
    # proteger, e segurar ali só atrapalharia o desenvolvimento.
    cache.set(
        CHAVE_JANELA.format(pk=perfil.pk),
        time.time() + JANELA_REENVIO_SEGUNDOS,
        timeout=JANELA_REENVIO_SEGUNDOS,
    )
```

**`apps/core/entrega_email.py`** — a montagem do e-mail de acesso deixa de ser privada do cadastro e
passa a ser composta pelos dois atos que entregam senha de primeiro acesso. Recebe o DTO, e não o
`Perfil`: é o que mantém `apps/core` sem conhecer os models de `user_admin`.
```python
def entregar_email_de_acesso(pedido: EmailAcessoInput) -> bool:
    """True quando a mensagem foi de fato entregue ao SMTP; False quando o envio está desligado por
    configuração."""
    conteudo = montar_email_acesso(pedido)
    return entregar_email(montar_mensagem(conteudo, destinatarios=(pedido.destinatario,)))
```

**`apps/autenticacao/reenvio.py`** — o ato: repetir a senha guardada, ou sortear e gravar uma.
```python
ERRO_ENTREGA = "Não foi possível enviar a senha para {email}. Tente novamente em instantes."

CHAVE_SENHA = "senha_uso_unico:{pk}"
CHAVE_SENHA_ANTERIOR = "senha_uso_unico_anterior:{pk}"
# Por quanto tempo o pedido seguinte reenvia a MESMA senha em vez de emitir outra. Não é prazo de
# validade: a senha provisória autentica até ser substituída ou usada (SPEC criacao_usuarios/004),
# e o que expira aqui é só a cópia em texto claro que permite reenviá-la.
PRAZO_MESMA_SENHA_SEGUNDOS = settings.PRAZO_MESMA_SENHA_SEGUNDOS
# O hash substituído sobrevive muito mais: a mensagem que a pessoa tem aberta na caixa de entrada
# pode ser de ontem, e é ela que a tela do código precisa reconhecer.
PRAZO_SENHA_ANTERIOR_SEGUNDOS = settings.PRAZO_SENHA_ANTERIOR_SEGUNDOS

# Sem controle nesta tela para realçar: o pedido nasce de um botão, não de um campo.
traduzir_recusa_reenvio = TradutorDeRecusa(Formulario(campos=()))


@dataclass(frozen=True)
class DesfechoReenvio:
    """Recado do ato para a view, no molde do `DesfechoRecuperacao`: não é DTO de domínio, não cruza
    fronteira de serviço e carrega o próprio model, que é de quem o modal mostra o RF."""

    perfil: Perfil | None = None
    email: str = ""
    enviado: bool = False
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    # Segundos que faltam para o próximo envio; maior que zero é a etiqueta de "nada saiu agora
    # porque a mensagem anterior acabou de sair".
    espera_segundos: int = 0
    # Preenchido SÓ quando a senha não saiu por e-mail — `None` é a etiqueta de "foi entregue", e é
    # ela que a tela lê para decidir se abre o modal (SPEC criacao_usuarios/007).
    senha_a_exibir: SecretStr | None = None


def _perfil_com_senha_a_reenviar(rf: str) -> Perfil | None:
    """`senha_provisoria=True` é a metade que importa da regra: quem já tem senha definitiva entra
    pela recuperação, que é a porta do outro estado da conta. Sem e-mail não há para onde mandar, e
    o desfecho é o mesmo do RF que não existe."""
    return (
        Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=True)
        .exclude(email="")
        .first()
    )


def reenviar_senha_uso_unico(pedido: ReenvioSenhaInput) -> DesfechoReenvio:
    """Reenviar é o caso comum, e emitir é a exceção: enquanto a senha guardada ainda for a
    credencial da conta, o pedido repete a mesma mensagem — trocar a cada clique deixaria na caixa
    de entrada uma pilha de códigos em que só o último funciona.

    A senha nova só passa a valer se chegou: a gravação e a entrega são a mesma transação — a mesma
    regra do cadastro (SPEC criacao_usuarios/004), pelo motivo inverso. Lá, servidor gravado sem
    receber a senha é conta que ninguém usa; aqui, senha trocada sem chegar tira do servidor a que
    ele ainda tinha na caixa de entrada."""
    perfil = _perfil_com_senha_a_reenviar(pedido.rf)
    if perfil is None:
        return DesfechoReenvio()
    espera = espera_do_reenvio(perfil)
    if espera:
        # Sai antes de sortear: dentro da janela o pedido não produz nada — nem mensagem, nem
        # senha nova, nem a troca da que está valendo.
        return DesfechoReenvio(perfil=perfil, email=perfil.email, enviado=True, espera_segundos=espera)
    guardada = _copia_guardada(perfil)
    senha = guardada or gerar_senha_temporaria()
    try:
        with transaction.atomic():
            # Repetir a cópia guardada não escreve no cadastro: só a emissão grava.
            if guardada is None:
                _gravar_senha(perfil, senha)
            entregue = entregar_email_de_acesso(
                EmailAcessoInput(
                    nome=perfil.nome,
                    rf=perfil.rf,
                    destinatario=perfil.email,
                    senha_temporaria=senha,
                    url_acesso=pedido.url_acesso,
                )
            )
    except SmtpEnvioError:
        return DesfechoReenvio(perfil=perfil, email=perfil.email, recusa=_recusa_da_entrega(perfil.email))
    # Depois do commit, e nunca antes: o cache não participa da transação, e uma entrada gravada
    # sobre uma troca desfeita ofereceria para sempre uma senha que não autentica.
    _guardar_senha(perfil, senha)
    if entregue:
        armar_janela(perfil)
    # A senha só escapa do ato por este caminho, e só depois de a transação ter fechado.
    return DesfechoReenvio(
        perfil=perfil,
        email=perfil.email,
        enviado=entregue,
        senha_a_exibir=None if entregue else senha,
    )


def _copia_guardada(perfil: Perfil) -> SecretStr | None:
    """O cache é palpite, não autoridade: quem diz se a cópia guardada ainda é a credencial da
    conta é o hash do próprio servidor. A senha de uso único não vence — não há carimbo a conferir,
    e o que o cache perde por reinício, por outro processo ou pelo próprio prazo é a cópia, não a
    credencial: some a chance de repetir a mesma, e o pedido seguinte emite outra."""
    guardada = cache.get(CHAVE_SENHA.format(pk=perfil.pk))
    if guardada is None or not perfil.check_password(guardada):
        return None
    return SecretStr(guardada)


def _guardar_senha(perfil: Perfil, senha: SecretStr) -> None:
    cache.set(
        CHAVE_SENHA.format(pk=perfil.pk),
        senha.get_secret_value(),
        timeout=PRAZO_MESMA_SENHA_SEGUNDOS,
    )


def _guardar_hash_anterior(perfil: Perfil) -> None:
    """O hash que sai de cena, guardado antes de ser sobrescrito — é hash, não senha, e é o mesmo
    valor que estava no banco um instante atrás. Transação desfeita deixa aqui o hash que continua
    valendo, o que é inofensivo: código que casasse com ele já teria autenticado."""
    cache.set(
        CHAVE_SENHA_ANTERIOR.format(pk=perfil.pk),
        perfil.password,
        timeout=PRAZO_SENHA_ANTERIOR_SEGUNDOS,
    )


def codigo_foi_substituido(rf: str, codigo: SecretStr) -> bool:
    """A pergunta que a tela do código faz depois de o `check_password` recusar: o que a pessoa
    digitou é a senha ANTERIOR desta conta? Para o hash em vigor, código de mensagem antiga e erro
    de digitação são a mesma recusa — quem os separa é o hash guardado pelo reenvio."""
    perfil = Perfil.objects.filter(rf=rf, is_active=True, senha_provisoria=True).first()
    if perfil is None:
        return False
    anterior = cache.get(CHAVE_SENHA_ANTERIOR.format(pk=perfil.pk))
    return anterior is not None and check_password(codigo.get_secret_value(), anterior)


def _gravar_senha(perfil: Perfil, senha: SecretStr) -> None:
    """`update_fields` porque este ato mexe numa coisa só: a credencial. `senha_provisoria` já está
    ligada — é o que autorizou o pedido — e nada mais do cadastro é reescrito por um pedido feito
    por quem não está autenticado."""
    _guardar_hash_anterior(perfil)
    perfil.set_password(senha.get_secret_value())
    perfil.save(update_fields=["password"])


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa_reenvio(
        (ErroBruto(controle="email", tipo="entrega", mensagem=ERRO_ENTREGA.format(email=email)),)
    )
```

**`apps/autenticacao/views.py`** — a validação do código, ALTERADA: duas recusas onde havia uma. O
`autenticar_primeiro_login` da SPEC autenticacao/001 segue intocado — o que muda é quem escolhe a
mensagem depois de ele recusar.
```python
ERRO_OTP_SUBSTITUIDO = (
    "Esta senha de uso único foi substituída por um reenvio. Use o código da mensagem mais recente "
    "que chegou no seu e-mail institucional."
)


@require_POST
def validar_otp_view(request: HttpRequest) -> HttpResponse:
    ...
    if perfil is None:
        # A pergunta só é feita DEPOIS da recusa, e só ela: acertar o código nunca passa por aqui.
        mensagem = (
            ERRO_OTP_SUBSTITUIDO
            if codigo_foi_substituido(rf, validacao.codigo_otp)
            else ERRO_OTP
        )
        recusa = traduzir_recusa_otp((ErroBruto(controle="otp", tipo="invalido", mensagem=mensagem),))
        ...
```

**`apps/autenticacao/urls.py`** — a rota de escrita, aberta como as demais desta tela.
```python
urlpatterns += [
    path(
        "esqueci-minha-senha/reenviar-senha/",
        views.reenviar_senha_unico_view,
        name="reenviar_senha_unico",
    ),
]
```

**`apps/autenticacao/views.py`** — a view fina: entrega o desfecho ao partial e desembrulha a senha.
```python
@require_POST
def reenviar_senha_unico_view(request: HttpRequest) -> HttpResponse:
    desfecho = reenviar_senha_uso_unico(
        ReenvioSenhaInput(
            rf=request.POST.get("rf", "").strip(),
            url_acesso=request.build_absolute_uri("/"),
        )
    )
    senha = desfecho.senha_a_exibir
    contexto = {
        # `.get_secret_value()` é obrigatório: o SecretStr renderiza como `**********` no template,
        # e o modal sairia com asteriscos no lugar da senha, sem erro nenhum para denunciar.
        "desfecho": desfecho,
        "senha_temporaria": senha.get_secret_value() if senha is not None else None,
    }
    status = 422 if desfecho.recusa.mensagens else 200
    return render(request, "autenticacao/partials/_envio_senha_unico.html", contexto, status=status)
```

**`templates/autenticacao/partials/_envio_senha_unico.html`** — as faces da resposta, no molde do
`_envio_recuperacao.html`. O modal sai por **out-of-band**, como no cadastro.
```html
{% if desfecho.recusa.mensagens %}
  {# A senha antiga continua valendo: a transação desfez a troca. #}
  {% include "partials/_tarja_recusa.html" with erros=desfecho.recusa.mensagens titulo="Não foi possível enviar a senha" %}
{% elif desfecho.espera_segundos %}
  <div class="card-well ..." data-contagem-reenvio="{{ desfecho.espera_segundos }}">…</div>
{% elif desfecho.enviado %}
  <div class="alert alert-success alert-soft text-xs">
    Senha de uso único enviada para <strong>{{ desfecho.email }}</strong>.
  </div>
{% elif senha_temporaria is not None %}
  <div class="alert alert-warning alert-soft text-xs">Envio desligado: a senha aparece no modal.</div>
{% else %}
  {# RF sem conta em primeiro acesso, alcançado só por POST direto: nenhuma mensagem que confirme #}
  {# ou negue a conta.                                                                            #}
  <div class="card-well ...">Nada a fazer para este pedido.</div>
{% endif %}
{% if senha_temporaria is not None %}
  <div id="poco-modal" hx-swap-oob="innerHTML">
    {% include "user_admin/partials/_modal_senha_desenvolvimento.html" with perfil=desfecho.perfil instrucao="Nenhum e-mail foi enviado. Anote a senha e use-a agora para ativar sua conta." %}
  </div>
{% endif %}
```

**`templates/user_admin/partials/_modal_senha_desenvolvimento.html`** — ALTERADO: a única linha que
muda de dono é o subtítulo, que passa a vir de quem inclui. O painel de conclusão do cadastro não
passa nada e continua com o texto que já tem.
```html
<p class="text-sm text-base-content/70 mt-1">
  {{ instrucao|default:"Nenhum e-mail foi enviado. Copie agora e entregue a senha a quem foi cadastrado." }}
</p>
```

**`templates/autenticacao/partials/_campo_login_dinamico.html`** — o acionador no ramo de primeiro
acesso, na mesma forma e no mesmo lugar do "Esqueci minha senha" do ramo de senha.
```html
<a href="{% url 'autenticacao:esqueci_senha' %}?rf={{ estado.rf }}"
   class="btn-etched btn-etched-swell etched self-center">
  Reenviar senha de uso único
</a>
```

**`templates/autenticacao/esqueci_senha.html`** e **`templates/autenticacao/primeiro_login.html`** —
o mesmo acionador, o mesmo alvo e o mesmo poço nas duas telas; o que muda é o destaque em volta.
```html
{# O acionador fica FORA do alvo do POST: o `hx-post` só troca a resposta abaixo dele, e é ela que #}
{# decide se ele volta a ficar disponível. Em `primeiro_login.html` ele fica fora do <form> do     #}
{# código, porque formulário aninhado não existe em HTML.                                          #}
<button type="button" class="btn btn-glass w-full font-bold"
        hx-post="{% url 'autenticacao:reenviar_senha_unico' %}"
        hx-vals='{"rf": "{{ rf }}"}'
        hx-target="#resultado-reenvio-senha"
        data-reenvio-acionador>
  Reenviar senha de uso único
</button>
<div id="resultado-reenvio-senha" class="min-h-[1rem]"></div>
...
<div id="poco-modal" class="poco-modal"></div>
```

## 7 · Caveats
A senha emitida fica no cache em texto claro pelo prazo configurado — cinco minutos por padrão —, e é
ela que o pedido seguinte reenvia. O hash é a única forma da senha que o cadastro guarda, então sem
essa cópia todo reenvio seria uma emissão, e cada clique repetido deixaria na caixa de entrada mais
um código em que só o último funciona. O custo é uma credencial viva em memória do processo por esse
prazo, onde antes ela só existia entre a gravação e o SMTP.

O hash da senha substituída fica no cache pelo prazo configurado, 24 horas por padrão, para a tela do
código poder dizer "esta foi trocada" em vez da recusa genérica. Sem ele, quem digita corretamente o código de uma mensagem antiga
recebe a mesma resposta de quem errou a digitação, e não tem como saber que o problema não é ele. O
custo é uma leitura de cache e uma conferência de hash a cada código recusado, e um recado que some
sozinho — reinício do processo apaga a entrada, e a recusa volta a ser a genérica.

Não havendo cópia guardada, o pedido emite uma senha nova, e é essa emissão que derruba a anterior —
a senha de uso único não vence sozinha, e sem pedido algum ela vale indefinidamente. É o caso de quem
perdeu justamente a mensagem do cadastro, cujo código não fica guardado em lugar nenhum. O custo é
que um anônimo que saiba um RF em primeiro acesso derruba, uma vez, o código do e-mail de cadastro
daquele servidor — e a partir daí só faz chegar de novo, na caixa dele, o mesmo código.

A rota é aberta e diz, pelo desfecho, que aquele RF está em primeiro acesso e para qual e-mail a
senha foi. A tela de recuperação já mostra o endereço em texto claro por decisão da SPEC 003, e o
partial do login já revela o estado de primeiro acesso desde a SPEC 001. O custo é mais uma
superfície repetindo o que aquelas duas abriram, agora com efeito de escrita.

A janela entre envios é uma só por servidor, compartilhada com a recuperação de senha. Os dois
pedidos são de estados excludentes da conta e protegem a mesma caixa de entrada, e separá-los daria
a quem quisesse insistir duas cotas em vez de uma. O custo é que o servidor que conclui o primeiro
acesso e pede recuperação em seguida pode cair numa espera armada pelo reenvio anterior.

A troca da senha e a conversa com o SMTP ficam na mesma transação. Senha trocada sem a mensagem
chegar deixaria o servidor sem nenhuma credencial válida, que é o oposto do que ele pediu. O custo é
o `UPDATE` ficar aberto durante a conversa SMTP, como já acontece no cadastro.

O modal da senha em tela ganha o subtítulo por variável de contexto, com o texto atual como padrão.
As duas telas mostram a mesma credencial e falam com leitores diferentes — quem cadastrou, e o
próprio servidor. O custo é que o texto do modal deixa de ser legível apenas no arquivo dele.

Com o envio de e-mail desligado, a senha de primeiro acesso aparece na tela de quem informou o RF,
sem autenticação alguma — mesmo regime das SPECs criacao_usuarios/007 e autenticacao/003. A decisão
mantém o fluxo exercitável de ponta a ponta em ambiente sem SMTP. O custo é que, em desenvolvimento,
qualquer pessoa que informe um RF em primeiro acesso ativa a conta daquele servidor.

`apps/core/entrega_email.py` passa a conhecer o e-mail de acesso, que antes era montado só dentro do
cadastro. É o módulo que os dois atos já compõem para falar com o SMTP, e duplicar a montagem
deixaria duas versões da mesma mensagem livres para divergir. O custo é `apps/core` ganhar
dependência de `services.domain.email`.

## 8 · Testes (TDD)
- `test_sem_copia_guardada_o_pedido_emite_uma_senha_nova` — o POST grava oito dígitos novos como
  provisórios e os entrega ao e-mail cadastrado; a senha do cadastro passa a ser recusada pelo
  `check_password`, e a nova passa. *(marker `banco`)*
- `test_pedido_seguinte_reenvia_a_mesma_senha` — vencida a janela, o segundo pedido não escreve no
  cadastro e a mensagem leva a senha do pedido anterior; com a entrada de cache perdida, emite outra.
  *(marker `banco`)*
- `test_falha_na_entrega_nao_troca_a_senha` — enviador que levanta e destinatário recusado devolvem o
  motivo na tela, a senha anterior continua autenticando e a emitida não fica guardada.
  *(marker `banco`)*
- `test_rf_sem_primeiro_acesso_nao_envia_nada` — RF inexistente, inativo, com senha definitiva ou
  sem e-mail cadastrado não chama o envio nem altera credencial alguma. *(marker `banco`)*
- `test_pedido_repetido_segura_o_envio_na_janela` — o segundo POST dentro de
  `JANELA_REENVIO_SEGUNDOS` não chama o envio, devolve a espera e não troca a senha; vencida a
  janela, a mensagem sai. *(marker `banco`)*
- `test_com_envio_desligado_a_senha_sai_no_modal_e_com_envio_ligado_nao` — a resposta do POST carrega
  a senha em texto claro e a tarja de desenvolvimento só quando `EMAIL_ENVIO_HABILITADO` está
  desligado. *(marker `banco`)*
- `test_codigo_substituido_recusa_dizendo_que_foi_trocado` — digitado o código da mensagem
  anterior, a tela devolve 422 dizendo que ele foi substituído; código simplesmente errado recebe a
  recusa genérica, e o código em vigor autentica. *(marker `banco`)*
- `test_login_em_primeiro_acesso_oferece_o_reenvio` — o partial dinâmico do login traz o acionador
  com o RF consultado, e o ramo de senha definitiva segue sem ele. *(marker `banco`)*
- `test_telas_de_recuperacao_e_de_codigo_oferecem_o_reenvio_ativo` — nas duas telas o acionador chega
  disponível e apontando para a rota de reenvio. *(marker `banco`)*
