---
spec: autenticacao/001
versao: v6
atualizado_em: 2026-08-26
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: ponto de entrada no widget de topo e renderização da foto/avatar do usuário logado
  - v3: RF com os sete dígitos do cadastro e realce do campo ao exceder
  - v4: campo de RF mascarado no cliente, com os dígitos seguindo sozinhos para a view
  - v5: acionador de logout na interface fica fora de escopo
  - v6: recusa de credenciais inválidas limpa o campo de RF, em vez de preservar o valor digitado
---

# SPEC autenticacao/001 — Login, detecção de primeiro acesso, validação de OTP e ponto de entrada no topo

## 1 · User story
O servidor da DIMAP clica no widget de usuário no canto superior direito para acessar a rota de login e se autenticar com RF e senha definitiva, ou para confirmar o e-mail institucional via código OTP no primeiro acesso.

## 2 · Condições de pronto
- [ ] O widget de usuário no canto superior direito (`#widget-area-usuario`), quando anônimo, exibe o ícone padrão com o rótulo "Entrar" e o clique direciona para a rota de login (`/login/`); quando autenticado, a bolinha exibe a foto ou avatar de iniciais com anel na cor da unidade, o nome do servidor, e o clique direciona para a página do seu perfil (`user_admin:pagina_perfil`).
- [ ] A tela de login é renderizada como modal compacto de vidro sobre o mapa administrativo vivo com deriva suave, mantendo o campo de RF permanentemente visível e editável em repouso e após retorno de erro de autenticação (status 422).
- [ ] O campo de RF exibe o que se digita na forma `123.456-7` e leva ao servidor só os sete dígitos: completos os sete, a consulta HTMX resolve o estado do servidor — primeiro acesso (`senha_provisoria=True`) exibe o botão com aura **"Primeiro Login"**, senão abre o campo de senha oculta com alternador de visibilidade ("olhinho") e o botão "Entrar"; passar de sete dígitos realça o campo de RF em erro e não dispara consulta alguma.
- [ ] Digitar um RF não cadastrado devolve o campo de senha padrão: a recusa ocorre apenas na submissão com a mensagem "RF ou senha incorretos", impedindo a enumeração de RFs válidos por força bruta.
- [ ] Digitar um novo RF quando a tela exibe mensagem de recusa (status 422) limpa a tarja de erro e reavalia dinamicamente o novo RF digitado.
- [ ] Clicar no botão "Primeiro Login" redireciona para a tela de primeiro acesso com confirmação por código de uso único (`/primeiro-login/`), renderizando o **átomo OTP** com 8 caixas no padrão daisyUI e o botão com aura "Primeiro Login".
- [ ] Digitar o código OTP de 8 dígitos correto valida a senha temporária, inicia a sessão autenticada do servidor com `senha_provisoria=True` e o redireciona para a tela de definição de senha; código inválido devolve status 422 com o OTP realçado em erro e mensagem em português na tarja.
- [ ] Submeter RF e senha válidos no fluxo normal autentica o servidor via `django.contrib.auth` e o redireciona para a página do perfil; credenciais inválidas ou servidor inativo (`is_active=False`) recebem recusa com status 422 e mensagem "RF ou senha incorretos", **limpando** o campo de RF para nova digitação.
- [ ] O acionamento de logout (`/logout/`) encerra a sessão ativa no Django e redireciona para a tela de login.
- [ ] O design da tela de login (modal compacto), da tela de primeiro login, do átomo OTP, do alternador de senha e dos estados do widget de usuário foi aprovado no **mock**, e as peças novas foram portadas para `static/src/tema-dimap.dev.css` e styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A identificação do servidor na entrada do sistema, o consumo da credencial provisória emitida no cadastro e a representação visual da identidade autenticada no topo da interface.

```python
class ConsultaRfInput(BaseModel):
    """A consulta dinâmica de estado do RF digitado na tela de login."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional


class LoginInput(BaseModel):
    """A submissão de credenciais para autenticação padrão."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    senha: SecretStr = Field(min_length=1)


class ValidacaoOtpInput(BaseModel):
    """A validação do código OTP de uso único no primeiro login."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    codigo_otp: SecretStr = Field(min_length=8, max_length=8)


class EstadoRfOutput(BaseModel):
    """O estado resolvido do RF para renderização do partial do login."""

    model_config = ConfigDict(frozen=True)

    rf: str
    eh_primeiro_login: bool
    rf_encontrado: bool
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`RegistroFuncional` e `PADRAO_RF`](../../apps/user_admin/schemas.py) — "que forma tem o RF?": os sete dígitos do `USERNAME_FIELD`, com os não-dígitos descartados na entrada; é ele que define o limite que o campo da tela conta.
- [`Perfil`](../../apps/user_admin/models/user.py) — "o servidor existe, está ativo e com `senha_provisoria` ligada?"; a leitura decide se renderiza o botão de aura ou o campo de senha, e fornece nome e lotação do usuário logado.
- [`imagem_do_perfil` e `resolver_imagem_perfil`](../../apps/user_admin/apresentacao.py) — entrega a foto ou avatar SVG de iniciais com anel na cor da unidade para renderizar na bolinha do widget quando autenticado.
- [`PoliticaSenhaTemporaria`](../../services/utils/senha.py) — o comprimento de 8 dígitos numéricos que define o número de caixas do átomo OTP.
- [`FORMULARIO_SERVIDOR` e `TradutorDeRecusa`](../../services/utils/erros_formulario.py) — "como a recusa do OTP se diz e qual controle ela realça?".
- [`.botao-aura` e `.aura-onsen`](../../apps/user_admin/022-tornar-administrador.md) — o botão de peso com aura reusado para "Primeiro Login".

**Mock:** [001-mock-login-e-primeiro-acesso.html](001-mock-login-e-primeiro-acesso.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Menu do widget de usuário, com o **acionador de logout** e os atalhos administrativos — SPEC `autenticacao/003`, a escrever: a rota `/logout/` sai desta SPEC sem gatilho na interface, alcançável só pela URL.
- A definição da senha definitiva após validar o OTP — SPEC [autenticacao/002](002-definir-e-redefinir-senha.md).
- Redefinição voluntária de senha por usuário logado — SPEC [autenticacao/002](002-definir-e-redefinir-senha.md).
- Reenvio da senha temporária ou recuperação de senha esquecida — sem dono ainda.
- Rate limiting / bloqueio por excesso de tentativas incorretas — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/user_admin/models/user.py` → `Perfil`, `senha_provisoria`.
- `@apps/user_admin/schemas.py` → `RegistroFuncional`, `PADRAO_RF`: a forma única do RF nos DTOs.
- `@apps/user_admin/apresentacao.py` → `imagem_do_perfil`: resolução de foto/avatar e cor da unidade.
- `@templates/base.html` → `#widget-area-usuario`: ponto de entrada no topo direito com estados anônimo e autenticado.
- `@templates/user_admin/partials/_imagem_perfil.html` → renderização do avatar/foto na bolinha do widget.
- `@services/utils/erros_formulario` → `Formulario`, `CampoDeFormulario`, `ErroBruto`, `TradutorDeRecusa`, `RecusaDeFormulario`.
- `@static/src/js/ui/scroll_etched.js` → o padrão de módulo de UI opt-in por atributo `data-`.
- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.input-glass`, `.btn-onsen`, `.botao-aura`, `.aura-onsen`, `.tarja-vinculo-critica`, `.campo-realce-erro`, `.avatar-glass`.
- `django.contrib.auth` → `authenticate`, `login`, `logout`.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `erros-de-formulario`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o §7.2 do CLAUDE.md.

**`apps/autenticacao/urls.py`** — as rotas de entrada, verificação, validação de OTP e saída.
```python
app_name = "autenticacao"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/checar-rf/", views.checar_rf_view, name="checar_rf"),
    path("primeiro-login/", views.primeiro_login_otp_view, name="primeiro_login"),
    path("primeiro-login/validar/", views.validar_otp_view, name="validar_otp"),
    path("logout/", views.logout_view, name="logout"),
]
```

**`apps/autenticacao/services.py`** — a regra de resolução de RF e validação de OTP.
```python
def resolver_estado_rf(consulta: ConsultaRfInput) -> EstadoRfOutput:
    """Verifica se o RF é de primeiro acesso sem revelar inexistência."""
    try:
        perfil = Perfil.objects.get(rf=consulta.rf, is_active=True)
        return EstadoRfOutput(
            rf=consulta.rf,
            eh_primeiro_login=perfil.senha_provisoria,
            rf_encontrado=True,
        )
    except Perfil.DoesNotExist:
        return EstadoRfOutput(
            rf=consulta.rf,
            eh_primeiro_login=False,
            rf_encontrado=False,
        )


def autenticar_primeiro_login(validacao: ValidacaoOtpInput) -> Perfil | None:
    """Valida a senha provisória contra o hash do model sem derrubar a marca ainda."""
    try:
        perfil = Perfil.objects.get(rf=validacao.rf, is_active=True, senha_provisoria=True)
    except Perfil.DoesNotExist:
        return None
    if not perfil.check_password(validacao.codigo_otp.get_secret_value()):
        return None
    return perfil
```

**`apps/autenticacao/context_processors.py`** — contexto global para renderizar o avatar do usuário logado no base.html.
```python
def contexto_usuario_autenticado(request: HttpRequest) -> dict[str, Any]:
    """Injeta a imagem de perfil e a cor da unidade quando o usuário está logado."""
    if not request.user.is_authenticated:
        return {}
    return {
        "imagem_perfil_usuario": imagem_do_perfil(request.user),
        "cor_unidade_hex": hex_da_cor(request.user.cor_unidade),
    }
```

**`templates/base.html`** — widget de usuário no canto superior direito com chaveamento anônimo / autenticado.
```html
{# Widget da área do usuário: anônimo aponta para login; autenticado exibe avatar e aponta para perfil #}
{% if request.user.is_authenticated %}
  <a id="widget-area-usuario"
     href="{% url 'user_admin:pagina_perfil' pk=request.user.pk %}"
     class="fixed top-6 right-4 lg:right-6 z-20 glass-panel rounded-full! p-1.5 flex items-center lg:gap-3 cursor-pointer transition-glass hover:bg-white/60">
    <div class="w-9 h-9 lg:w-11 lg:h-11 shrink-0">
      {% include "user_admin/partials/_imagem_perfil.html" with imagem=imagem_perfil_usuario cor_unidade_hex=cor_unidade_hex tamanho="w-full h-full" perfil=request.user %}
    </div>
    <div class="hidden lg:block pr-4">
      <p class="text-sm font-bold m-0 leading-tight">{{ request.user.nome }}</p>
      <p class="text-[10px] uppercase tracking-wide font-medium m-0 leading-tight mt-0.5 text-madeira-600">{{ request.user.unidade.sigla|default:"Área do Usuário" }}</p>
    </div>
  </a>
{% else %}
  <a id="widget-area-usuario"
     href="{% url 'autenticacao:login' %}"
     class="fixed top-6 right-4 lg:right-6 z-20 glass-panel rounded-full! p-1.5 flex items-center lg:gap-3 cursor-pointer transition-glass hover:bg-white/60">
    <div class="w-9 h-9 lg:w-11 lg:h-11 rounded-full bg-rocha-800 border border-white/40 flex items-center justify-center shadow-[inset_0_2px_4px_rgba(7,58,84,0.3)]">
      <svg class="w-5 h-5 text-agua-300 drop-shadow-[0_0_6px_rgba(72,202,228,0.6)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    </div>
    <div class="hidden lg:block pr-4">
      <p class="text-sm font-bold m-0 leading-tight">Entrar</p>
      <p class="text-[10px] uppercase tracking-wide font-medium m-0 leading-tight mt-0.5 text-madeira-600">Área do Usuário</p>
    </div>
  </a>
{% endif %}
```

**`apps/autenticacao/views.py`** — orquestração das views de login e primeiro acesso.
```python
ERRO_LOGIN = "RF ou senha incorretos."
ERRO_OTP = "Senha de uso único inválida: confira o código recebido no e-mail institucional."


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": request.user.pk}))
    if request.method == "POST":
        rf = request.POST.get("rf", "").strip()
        senha = request.POST.get("password", "")
        user = authenticate(request, username=rf, password=senha)
        if user is None or not user.is_active:
            recusa = traduzir_recusa_login((ErroBruto(controle="rf", tipo="invalido", mensagem=ERRO_LOGIN),))
            return render(request, "autenticacao/login.html", {"recusa": recusa, "rf": rf}, status=422)
        login(request, user)
        return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": user.pk}))
    return render(request, "autenticacao/login.html")


@require_POST
def checar_rf_view(request: HttpRequest) -> HttpResponse:
    rf = request.POST.get("rf", "").strip()
    estado = resolver_estado_rf(ConsultaRfInput(rf=rf))
    return render(
        request,
        "autenticacao/partials/_campo_login_dinamico.html",
        {"estado": estado},
    )


def primeiro_login_otp_view(request: HttpRequest) -> HttpResponse:
    rf = request.GET.get("rf", "").strip()
    return render(request, "autenticacao/primeiro_login.html", {"rf": rf})


@require_POST
def validar_otp_view(request: HttpRequest) -> HttpResponse:
    rf = request.POST.get("rf", "").strip()
    otp = request.POST.get("otp", "").strip()
    validacao = ValidacaoOtpInput(rf=rf, codigo_otp=SecretStr(otp))
    perfil = autenticar_primeiro_login(validacao)
    if perfil is None:
        recusa = traduzir_recusa_otp((ErroBruto(controle="otp", tipo="invalido", mensagem=ERRO_OTP),))
        return render(
            request,
            "autenticacao/primeiro_login.html",
            {"rf": rf, "recusa": recusa},
            status=422,
        )
    # Autentica na sessão para permitir acesso à rota de definir senha.
    login(request, perfil)
    return redirect("autenticacao:definir_senha")


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("autenticacao:login")
```

**`static/src/js/ui/campo_mascarado.js`** — a máscara do campo e o valor que segue para a view.
```js
// Opt-in por [data-mascara], no padrão dos demais módulos de UI. O gabarito diz onde entram os
// separadores e, pela contagem dos seus slots, quantos dígitos o campo tem; [data-mascara-alvo]
// aponta o campo oculto que leva ao servidor só os dígitos.
const SLOT_DE_DIGITO = "0";

function contarDigitos(texto) {
  return texto.replace(/\D/g, "").length;
}

// O excesso não é truncado: sai formatado à direita do gabarito e acende o campo — engolir a tecla
// a mais esconderia da pessoa que ela digitou um RF errado.
function formatar(digitos, gabarito) {
  let saida = "";
  let lidos = 0;
  for (const marca of gabarito) {
    if (lidos >= digitos.length) return saida;
    if (marca === SLOT_DE_DIGITO) {
      saida += digitos[lidos];
      lidos += 1;
    } else {
      saida += marca;
    }
  }
  return saida + digitos.slice(lidos);
}

// Reformatar move o texto sob o cursor; o que o mantém no lugar é a contagem de dígitos à esquerda
// dele, que a máscara não altera.
function posicaoAposDigitos(texto, quantidade) {
  if (quantidade === 0) return 0;
  let vistos = 0;
  for (let i = 0; i < texto.length; i += 1) {
    if (!/\d/.test(texto[i])) continue;
    vistos += 1;
    if (vistos === quantidade) return i + 1;
  }
  return texto.length;
}

function aplicar(campo) {
  const gabarito = campo.dataset.mascara;
  const limite = contarDigitos(gabarito);
  const cursor = campo.selectionStart ?? campo.value.length;
  const digitosAEsquerda = contarDigitos(campo.value.slice(0, cursor));
  const digitos = campo.value.replace(/\D/g, "");

  campo.value = formatar(digitos, gabarito);
  if (document.activeElement === campo) {
    const posicao = posicaoAposDigitos(campo.value, digitosAEsquerda);
    campo.setSelectionRange(posicao, posicao);
  }

  const excede = digitos.length > limite;
  campo.classList.toggle("campo-realce-erro", excede);
  campo.setAttribute("aria-invalid", excede ? "true" : "false");
  campo.dataset.digitosCompletos = digitos.length === limite ? "sim" : "nao";

  const alvo = document.querySelector(campo.dataset.mascaraAlvo);
  if (alvo) alvo.value = digitos;
}

function montar(raiz) {
  raiz.querySelectorAll("[data-mascara]").forEach((campo) => {
    campo.addEventListener("input", () => aplicar(campo));
    aplicar(campo);
  });
}

document.addEventListener("DOMContentLoaded", () => montar(document));
// A recusa 422 devolve o formulário inteiro, e com ele um campo de RF que ainda não foi montado.
document.body.addEventListener("htmx:load", (evento) => montar(evento.detail.elt));
```

**`templates/autenticacao/login.html`** — o campo de RF, sempre visível e editável.
```html
{# O oculto é o que se chama `rf`: o visível só mostra a máscara e dispara a consulta. #}
<input type="hidden" name="rf" id="rf-valor" value="{{ rf|default:'' }}" />
<input type="text"
       inputmode="numeric"
       value="{{ rf|default:'' }}"
       class="input input-glass w-full {{ realce.rf|default:'' }}"
       data-mascara="000.000-0"
       data-mascara-alvo="#rf-valor"
       hx-post="{% url 'autenticacao:checar_rf' %}"
       hx-trigger="keyup[this.dataset.digitosCompletos === 'sim'] changed delay:400ms"
       hx-include="#rf-valor"
       hx-target="#slot-dinamico-login" />
```

**`static/src/tema-dimap.dev.css`** — os átomos OTP e alternador olhinho.
```css
/* ÁTOMO. O campo OTP com 8 caixas monoespaçadas, fundo de vidro e destaque em foco. */
.otp-onsen {
  @apply flex items-center justify-center gap-2;
}

.otp-onsen .otp-caixa {
  @apply w-10 h-13 sm:w-11 sm:h-14 text-center text-xl font-bold font-mono rounded-lg border border-base-300 bg-base-100/90 text-agua-700 focus:border-agua-500 focus:outline-none focus:ring-2 focus:ring-agua-400/30 transition-all;
}

.otp-onsen .otp-caixa.campo-realce-erro {
  @apply border-error bg-error/10 text-error focus:ring-error/30;
}

/* ÁTOMO. Alternador de visibilidade acoplado ao input de senha. */
.input-olhinho-wrap {
  @apply relative flex items-center w-full;
}

.input-olhinho-btn {
  @apply absolute right-3 p-1.5 text-base-content/50 hover:text-agua-600 focus:outline-none transition-colors cursor-pointer;
}
```

## 7 · Caveats
A verificação dinâmica de RF via HTMX revela a condição de primeiro login para quem digita um RF cadastrado e válido. A decisão privilegia a fluidez da experiência do servidor recém-cadastrado no primeiro acesso, e a revelação é inócua porque o código de uso único permanece protegido na caixa de e-mail institucional. O custo é que quem testa RFs válidos consegue saber quais ainda não realizaram o primeiro acesso.

RFs inexistentes recebem o partial idêntico ao de quem já possui senha definitiva. A decisão impede ataques de enumeração de RFs cadastrados por força bruta na tela de login. O custo é uma submissão de formulário adicional antes de o usuário que digitou o próprio RF errado saber que a autenticação falhou.

A permanência do campo de RF editável na tela de erro (status 422) assegura que o usuário corrija erros de digitação no RF diretamente no formulário sem necessidade de recarregar a página.

A validação bem-sucedida do OTP inicia uma sessão de autenticação com `senha_provisoria=True`. A decisão permite que a rota seguinte (`/definir-senha/`) seja protegida por `@login_required` sem criar tokens ou cookies ad hoc fora do motor de sessões do Django. O custo é manter uma sessão autenticada restrita que precisa ser finalizada ou regularizada na definição da senha definitiva.

O campo de RF é mascarado no cliente e acende em erro por um módulo de UI que reformata o valor a cada `input`. O que o módulo decide é estado visual de um controle, não regra: a recusa que vale continua sendo a do servidor, que revalida o RF no DTO. O custo é a classe `.campo-realce-erro` passar a ter dois donos no mesmo campo — o `realce` da recusa 422, vindo do servidor, e o módulo, que a apaga assim que a contagem volta aos sete dígitos.

Quem se chama `rf` na submissão é um campo oculto que o módulo escreve; o campo visível não tem `name`. A separação é o que entrega ao servidor os sete dígitos limpos, sem os separadores da máscara. O custo é o formulário depender de JavaScript para ter valor — com o módulo fora do ar o login não sai, ainda que `RegistroFuncional` descartasse os separadores sozinho.

A consulta dinâmica de RF só dispara com os sete dígitos completos, por filtro no `hx-trigger`. Consultar a cada tecla faria o DTO recusar toda digitação parcial e o `PydanticValidationMiddleware` responder erro no meio da digitação. O custo é o gatilho depender de um atributo escrito por JavaScript, e não do valor do campo.

O avatar e a cor da unidade do usuário autenticado são injetados via context processor para alimentar o widget de topo em todas as páginas que herdam `base.html`. A decisão centraliza a apresentação da identidade no cabeçalho sem repetição de chamadas nas views. O custo é a resolução da imagem em requisições de usuários autenticados.

## 8 · Testes (TDD)
- `test_widget_usuario_anonimo_exibe_link_login_e_icone_padrao` — usuário não autenticado enxerga o link para `/login/` e o ícone de usuário no widget de topo. *(marker `banco`)*
- `test_widget_usuario_autenticado_exibe_avatar_e_link_perfil` — usuário autenticado renderiza sua foto ou avatar de iniciais na bolinha com a cor da unidade e link para a página de perfil. *(marker `banco`)*
- `test_checar_rf_com_senha_provisoria_devolve_botao_primeiro_login` — o partial renderiza o botão com aura "Primeiro Login" e o link para a rota do OTP. *(marker `banco`)*
- `test_checar_rf_com_senha_definitiva_devolve_campo_senha` — o partial renderiza o campo de senha com olhinho e o botão "Entrar". *(marker `banco`)*
- `test_checar_rf_inexistente_devolve_campo_senha_sem_revelar_inexistencia` — RF não encontrado responde com o mesmo partial de login padrão. *(marker `banco`)*
- `test_login_com_credenciais_validas_autentica_e_redireciona` — POST válido autentica o usuário no Django e redireciona para a página do perfil. *(marker `banco`)*
- `test_login_com_senha_invalida_recusa_com_mensagem_em_portugues_e_limpa_rf` — POST com senha errada responde status 422, exibe a tarja de erro com a mensagem em português e renderiza o campo RF vazio e editável. *(marker `banco`)*
- `test_validar_otp_correto_autentica_sessao_e_redireciona_para_definir_senha` — código de 8 dígitos coincidente com a senha provisória inicia sessão e redireciona para `definir_senha`. *(marker `banco`)*
- `test_validar_otp_incorreto_devolve_recusa_com_campo_realcado` — código incorreto responde status 422 com o campo OTP realçado em erro e sem autenticar sessão. *(marker `banco`)*
- `test_logout_encerra_a_sessao_e_redireciona_ao_login` — acionar a rota de logout desloga o usuário e direciona para a tela de login. *(marker `banco`)*
