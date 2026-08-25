---
spec: autenticacao/002
versao: v1
atualizado_em: 2026-08-25
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC autenticacao/002 — Definir e redefinir senha: template unificado, alternador de visibilidade e checklist reativo

## 1 · User story
O servidor da DIMAP define sua credencial no primeiro acesso ou altera a senha estando autenticado, validando em tempo real as regras de complexidade para manter sua conta protegida.

## 2 · Condições de pronto
- [ ] A tela de redefinição atende ao primeiro acesso e à alteração voluntária via template e rotas compartilhadas (`/definir-senha/` e `/redefinir-senha/`), diferenciadas pela flag `primeiro_login` no contexto e na validação.
- [ ] As rotas de definição e redefinição de senha exigem **servidor autenticado** (`@login_required`): anônimo é redirecionado para a tela de login.
- [ ] No **primeiro login** (`primeiro_login=True`), o formulário exibe os campos "Definir senha" e "Confirmar senha"; a gravação bem-sucedida salva a nova senha criptografada, desmarca `senha_provisoria = False`, encerra a sessão temporária e redireciona para a tela de login.
- [ ] Na **redefinição voluntária** (`primeiro_login=False`), o formulário exibe o campo "Senha atual" antes de "Nova senha" e "Confirmar senha"; a gravação confere a senha atual (`check_password`), salva a nova senha criptografada e mantém a sessão ativa via `update_session_auth_hash`.
- [ ] A nova senha exige cumprimento da **política de senha forte**: mínimo de 8 caracteres, pelo menos 1 letra maiúscula e pelo menos 1 caractere especial; violações voltam recusadas no formulário com o motivo em português e o controle realçado.
- [ ] O formulário contém validação visual em JavaScript que marca em tempo real (check verde) cada uma das 3 regras de complexidade conforme o usuário digita no campo de nova senha, e valida imediatamente a correspondência entre a nova senha e a confirmação, aplicando `.campo-realce-erro` em caso de divergência.
- [ ] Todos os campos de senha possuem o **alternador de visibilidade ("olhinho")**, permitindo alternar entre texto mascarado e plaintext pelo clique no botão acoplado.
- [ ] Submeter senhas divergentes ("Nova senha" e "Confirmar senha") devolve o formulário com o motivo em português na tarja e ambos os controles realçados com `campo-realce-erro`.
- [ ] A página do perfil do servidor (`user_admin:pagina_perfil`) exibe o botão "Redefinir senha" **apenas quando o servidor autenticado visualiza o seu próprio perfil** (`request.user.pk == perfil.pk`), omitindo-o na visualização de outros perfis.
- [ ] O design do template compartilhado, do alternador "olhinho", do checklist reativo e do match de confirmação foi aprovado no **mock** e portado para o tema e styleguide antes de qualquer template usá-lo.

## 3 · Domínio
A definição da credencial definitiva do servidor e a validação das regras de complexidade de senha.

```python
CARACTERES_ESPECIAIS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


class PoliticaSenhaForte(BaseModel):
    """As regras de complexidade exigidas para a senha definitiva do servidor."""

    model_config = ConfigDict(frozen=True)

    comprimento_minimo: int = 8
    exige_maiuscula: bool = True
    exige_especial: bool = True


class DefinicaoSenhaInput(BaseModel):
    """A gravação da senha definitiva no primeiro acesso (sem senha atual)."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    nova_senha: SecretStr = Field(min_length=8)
    confirmacao_senha: SecretStr = Field(min_length=8)


class RedefinicaoSenhaInput(BaseModel):
    """A alteração de senha por servidor autenticado (com senha atual)."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    senha_atual: SecretStr = Field(min_length=1)
    nova_senha: SecretStr = Field(min_length=8)
    confirmacao_senha: SecretStr = Field(min_length=8)
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Perfil`](../../apps/user_admin/models/user.py) — o servidor autenticado cuja senha é gravada via `set_password` e cuja flag `senha_provisoria` é desmarcada.
- [`FORMULARIO_SERVIDOR` e `TradutorDeRecusa`](../../services/utils/erros_formulario.py) — a tradução das recusas de divergência de senha, senha atual incorreta ou violação de política.
- [`SPEC autenticacao/001`](001-login-e-primeiro-acesso.md) — a sessão iniciada após a validação do OTP que conduz o servidor a esta tela no primeiro acesso.

**Mock:** [002-mock-definir-e-redefinir-senha.html](002-mock-definir-e-redefinir-senha.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Histórico de senhas anteriores para impedir reutilização das últimas N senhas — sem dono ainda.
- Expiração periódica compulsória de senha (troca a cada 90 dias) — sem dono ainda.
- Recuperação de senha por link assinado no e-mail (esqueci minha senha) — sem dono ainda.
- Inclusão do atalho de redefinição no menu global de administração — SPEC de menu de administração.

## 5 · Peças de referência a compor
- `@apps/user_admin/models/user.py` → `Perfil`, `senha_provisoria`.
- `@services/utils/erros_formulario` → `Formulario`, `CampoDeFormulario`, `ErroBruto`, `TradutorDeRecusa`, `RecusaDeFormulario`.
- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.input-glass`, `.btn-onsen`, `.tarja-vinculo-critica`, `.campo-realce-erro`, `.checklist-senha`, `.input-olhinho-wrap`.
- `django.contrib.auth` → `update_session_auth_hash`, `logout`.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `erros-de-formulario`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o §7.2 do CLAUDE.md.

**`services/domain/autenticacao/politica_senha.py`** — validação de complexidade da senha.
```python
ERRO_SENHAS_DIVERGENTES = "As senhas digitadas não coincidem: confira a confirmação."
ERRO_SENHA_FRACA_COMPRIMENTO = "A nova senha deve ter no mínimo 8 caracteres."
ERRO_SENHA_FRACA_MAIUSCULA = "A nova senha deve conter pelo menos uma letra maiúscula."
ERRO_SENHA_FRACA_ESPECIAL = "A nova senha deve conter pelo menos um caractere especial (!@#$%...)."
ERRO_SENHA_ATUAL_INCORRETA = "A senha atual informada está incorreta."


def validar_complexidade_senha(senha: str) -> list[str]:
    """Retorna a lista de motivos caso a senha não atenda à política forte."""
    erros = []
    if len(senha) < 8:
        erros.append(ERRO_SENHA_FRACA_COMPRIMENTO)
    if not any(c.isupper() for c in senha):
        erros.append(ERRO_SENHA_FRACA_MAIUSCULA)
    if not any(c in CARACTERES_ESPECIAIS for c in senha):
        erros.append(ERRO_SENHA_FRACA_ESPECIAL)
    return erros
```

**`apps/autenticacao/urls.py`** — rotas para definir e redefinir senha.
```python
urlpatterns += [
    path("definir-senha/", views.definir_senha_view, name="definir_senha"),
    path("redefinir-senha/", views.redefinir_senha_view, name="redefinir_senha"),
    path("gravar-senha/", views.gravar_senha_view, name="gravar_senha"),
]
```

**`apps/autenticacao/views.py`** — views de definição e gravação de senha.
```python
@login_required
def definir_senha_view(request: HttpRequest) -> HttpResponse:
    """Apresenta o formulário no modo Primeiro Login se o usuário tiver senha_provisoria=True."""
    eh_primeiro_login = request.user.senha_provisoria
    return render(
        request,
        "autenticacao/definir_senha.html",
        {"eh_primeiro_login": eh_primeiro_login},
    )


@login_required
def redefinir_senha_view(request: HttpRequest) -> HttpResponse:
    """Apresenta o formulário no modo Redefinição Voluntária (com senha atual)."""
    return render(
        request,
        "autenticacao/definir_senha.html",
        {"eh_primeiro_login": False},
    )


@login_required
@require_POST
def gravar_senha_view(request: HttpRequest) -> HttpResponse:
    perfil: Perfil = request.user
    eh_primeiro_login = perfil.senha_provisoria
    nova_senha = request.POST.get("nova_senha", "")
    confirmacao = request.POST.get("confirmacao_senha", "")
    senha_atual = request.POST.get("senha_atual", "")

    if not eh_primeiro_login:
        if not perfil.check_password(senha_atual):
            recusa = traduzir_recusa_senha((ErroBruto(controle="senha_atual", tipo="invalido", mensagem=ERRO_SENHA_ATUAL_INCORRETA),))
            return render(request, "autenticacao/definir_senha.html", {"eh_primeiro_login": False, "recusa": recusa}, status=422)

    if nova_senha != confirmacao:
        recusa = traduzir_recusa_senha((
            ErroBruto(controle="nova_senha", tipo="divergente", mensagem=ERRO_SENHAS_DIVERGENTES),
            ErroBruto(controle="confirmacao_senha", tipo="divergente", mensagem=ERRO_SENHAS_DIVERGENTES),
        ))
        return render(request, "autenticacao/definir_senha.html", {"eh_primeiro_login": eh_primeiro_login, "recusa": recusa}, status=422)

    erros_complexidade = validar_complexidade_senha(nova_senha)
    if erros_complexidade:
        recusa = traduzir_recusa_senha((ErroBruto(controle="nova_senha", tipo="complexidade", mensagem=erros_complexidade[0]),))
        return render(request, "autenticacao/definir_senha.html", {"eh_primeiro_login": eh_primeiro_login, "recusa": recusa}, status=422)

    perfil.set_password(nova_senha)
    if eh_primeiro_login:
        perfil.senha_provisoria = False
        perfil.save(update_fields=["password", "senha_provisoria"])
        logout(request)
        return redirect("autenticacao:login")

    perfil.save(update_fields=["password"])
    update_session_auth_hash(request, perfil)
    return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk}))
```

**`static/src/tema-dimap.dev.css`** — o checklist reativo de senha e alternador olhinho.
```css
/* ÁTOMO. Alternador de visibilidade acoplado ao input. */
.input-olhinho-wrap {
  @apply relative flex items-center w-full;
}

.input-olhinho-btn {
  @apply absolute right-3 p-1.5 text-base-content/50 hover:text-agua-600 focus:outline-none transition-colors cursor-pointer;
}

/* MOLÉCULA. Checklist de requisitos de complexidade da senha. */
.checklist-senha {
  @apply flex flex-col gap-1.5 p-3 rounded-lg bg-base-100/60 border border-base-300/60 text-xs;
}

.checklist-item {
  @apply flex items-center gap-2 text-base-content/60 transition-colors;
}

.checklist-item.atendido {
  @apply text-success font-medium;
}

.checklist-icone {
  @apply w-4 h-4 rounded-full flex items-center justify-center text-[10px] bg-base-300 text-base-content/60 transition-all;
}

.checklist-item.atendido .checklist-icone {
  @apply bg-success text-success-content font-bold;
}
```

**`templates/user_admin/partials/_secao_identificacao.html`** — o botão na página do servidor condicionado ao próprio usuário.
```html
{# Só exibe o botão de redefinir senha se o usuário autenticado for o próprio servidor exibido #}
{% if request.user.is_authenticated and request.user.pk == perfil.pk %}
  <a href="{% url 'autenticacao:redefinir_senha' %}" class="btn btn-outline btn-sm">
    Redefinir senha
  </a>
{% endif %}
```

## 7 · Caveats
Definir e redefinir senha não são configurados como atos administrativos com registro no `apps.competencias`. A decisão decorre de ser uma gestão de credencial estritamente pessoal do próprio usuário autenticado sobre sua própria conta. O custo é que a auditoria da troca de credencial não compõe a tabela de atos administrativos, ficando restrita ao log da aplicação.

No primeiro login, o encerramento forçado da sessão temporária após a definição da senha exige que o servidor faça login novamente com sua nova credencial. A decisão assegura que o fluxo completo de autenticação seja exercitado e que a sessão definitiva nasça sem vestígios do estado temporário. O custo é um passo extra de login para o usuário recém-cadastrado.

A validação de complexidade e a correspondência (match) entre a nova senha e a confirmação são executadas em tempo real via JavaScript no navegador para oferecer feedback imediato sem recarregamento ou ida ao servidor. A validação autoritativa no backend é mantida para garantir a integridade dos dados e prevenir persistência de credenciais inválidas.

## 8 · Testes (TDD)
- `test_definir_senha_primeiro_login_grava_senha_e_desmarca_provisoria` — POST válido com senha nova e confirmação iguais grava a nova senha criptografada e deixa `senha_provisoria=False`. *(marker `banco`)*
- `test_definir_senha_primeiro_login_desloga_e_redireciona_ao_login` — após definir a senha no primeiro login, o usuário tem a sessão encerrada e é redirecionado ao login. *(marker `banco`)*
- `test_redefinir_senha_com_senha_atual_correta_grava_nova_e_mantem_sessao` — redefinição com senha atual válida atualiza a senha e preserva a sessão autenticada. *(marker `banco`)*
- `test_redefinir_senha_com_senha_atual_incorreta_recusa_sem_alterar` — POST com senha atual errada responde 422, realça o controle `senha_atual` e não altera a senha. *(marker `banco`)*
- `test_senhas_divergentes_devolvem_recusa_no_formulario` — nova senha e confirmação diferentes respondem 422 com ambos os campos realçados. *(marker `banco`)*
- `test_senha_que_viola_politica_forte_e_recusada` — senha sem maiúscula, sem caractere especial ou menor que 8 caracteres é recusada com motivo em português. *(marker `banco`)*
- `test_anonimo_acessando_definir_ou_redefinir_e_redirecionado_ao_login` — GET ou POST anônimo em `/definir-senha/` ou `/redefinir-senha/` redireciona para o login. *(marker `banco`)*
- `test_botao_redefinir_so_aparece_para_o_proprio_servidor_na_pagina_de_perfil` — o HTML da página do perfil renderiza o botão de redefinir senha se `request.user.pk == perfil.pk` e o omite para outro usuário logado. *(marker `banco`)*
- `test_servidor_com_senha_definitiva_acessando_definir_senha_exige_senha_atual` — usuário que já realizou primeiro login não consegue alterar senha sem fornecer a senha atual. *(marker `banco`)*
