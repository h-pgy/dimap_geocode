---
spec: criacao_usuarios/007
versao: v1
atualizado_em: 2026-08-26
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC criacao_usuarios/007 — A senha em tela quando o envio de e-mail está desligado

## 1 · User story
**Requisito não-funcional** — o cadastro de servidor fica exercitável de ponta a ponta em ambiente
sem SMTP: quem cadastra recebe na tela a senha de primeiro acesso que a caixa de entrada receberia.

## 2 · Condições de pronto
- [ ] Com `EMAIL_ENVIO_HABILITADO` **desligado**, concluir o cadastro abre um **modal sobre o painel
      de sucesso** com o RF e a senha temporária **em texto claro**, e uma tarja declarando que a
      exibição existe só para desenvolvimento.
- [ ] Com o envio **ligado**, modal nenhum aparece e a senha **não existe no HTML** da resposta — nem
      no corpo, nem em atributo.
- [ ] A senha exibida é **a mesma que autentica**: o servidor recém-cadastrado entra com o que está
      na tela.
- [ ] O **botão de copiar** põe a senha na área de transferência e confirma na própria face; falhando
      a cópia, o botão diz que falhou e a senha segue selecionável.
- [ ] O modal **chega aberto** com a resposta do cadastro, e **fechá-lo deixa o painel de sucesso
      íntegro** — "Cadastrar outro" e "Abrir a página do servidor" funcionando, mais um botão que
      **reabre o modal** com a mesma senha, sem novo request.
- [ ] O painel de sucesso afirma que a senha **foi enviada por e-mail** só quando ela de fato foi;
      com o envio desligado, diz que ela precisa ser entregue a mão.
- [ ] **Cadastro recusado não expõe senha alguma**: a resposta 422 do formulário não a carrega, nem
      quando o envio está desligado.
- [ ] Nada muda no que já era proibido: a senha continua **fora do registro do ato**, fora do banco em
      texto claro e fora dos logs.
- [ ] O design foi aprovado no **mock**, e as peças novas estão no tema antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
Nenhuma ontologia nova. O que muda é o recado que o ato de cadastrar dá à orquestração: a senha
temporária, que hoje nasce e morre dentro de `criar_servidor`, passa a **sobreviver ao ato quando não
foi entregue** — e é a ausência da entrega, não a leitura de um flag, que a faz aparecer.

**`apps/user_admin/cadastro.py`**
```python
@dataclass(frozen=True)
class DesfechoCadastro:
    perfil: Perfil | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()
    marca_alterada: bool = False
    # ALTERADO nesta SPEC: campo novo. Preenchido SÓ quando a senha não saiu por e-mail —
    # `None` é a etiqueta de "foi entregue", e é ela que a tela lê para decidir tudo.
    senha_a_exibir: SecretStr | None = None
```

O cadastro do servidor e a entrega da credencial estão em
[criacao_usuarios/004](004-criar-servidor.md), que entrega `criar_servidor`, a senha temporária de
oito dígitos e o painel de sucesso. A pergunta desta SPEC a ele: **quando a entrega não acontece,
quem fica com a senha?**

**Mock:** [007-mock-senha-em-desenvolvimento.html](007-mock-senha-em-desenvolvimento.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Reemitir a senha de um servidor já cadastrado, com ou sem envio — sem dono ainda.
- Exibir a senha nos cadastros que não passam pela tela (`createsuperuser`, shell, `servidores_ficticios`) — sem dono ainda.
- Editar servidor: não gera senha, e não ganha modal — permanece como a [005](005-editar-servidor.md) entrega.

## 5 · Peças de referência a compor
- `@templates/user_admin/partials/_modal_encerrar.html` → o padrão de modal do projeto: `modal-toggle` marcado, `.modal-glass`, `.modal-box-glass` e `.modal-backdrop`.
- `@templates/user_admin/partials/_cadastro_concluido.html` → o painel de sucesso que o modal cobre.
- `@static/src/tema-dimap.dev.css` → `.tarja-vinculo` + `.tarja-vinculo-critica`: a tarja de aviso; `.text-code`: o átomo do valor monoespaçado.
- `@static/src/js/ui/select_onsen.js` → o formato de módulo ES dos controles do projeto.
- `@apps/user_admin/context.py` → `contexto_cadastro_concluido`: o contexto do painel.
- `@templates/user_admin/perfil.html` → `#poco-modal`: o poço fora da casca administrativa, onde o modal chega por oob.
- Skills: `mock`, `componentes-frontend`, `erros-de-formulario`, `escrever-testes`.

## 6 · Snippets

**`apps/user_admin/cadastro.py`**
```python
# A guarda do flag já morava aqui. O que muda é o retorno: quem chama precisa saber se a senha
# saiu, e essa é a ÚNICA leitura de `EMAIL_ENVIO_HABILITADO` em todo o caminho até a tela.
def _entregar_senha(perfil: Perfil, senha: SecretStr, url_acesso: HttpUrl) -> bool:
    """Devolve True quando a mensagem foi de fato entregue ao SMTP."""
    conteudo = montar_email_acesso(...)
    mensagem = montar_mensagem(conteudo, destinatarios=(perfil.email,))
    if not settings.EMAIL_ENVIO_HABILITADO:
        print(f"[SMTP desligado] para={mensagem.destinatarios} assunto={mensagem.assunto}")
        return False
    enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
    resultado = enviador(mensagem)
    if resultado.destinatarios_recusados:
        raise SmtpEnvioError(f"Destinatário recusado: {perfil.email}.")
    return True


# Em criar_servidor, no lugar da chamada atual:
    senha = gerar_senha_temporaria()
    try:
        with transaction.atomic():
            perfil = _gravar(novo, senha, foto)
            entregue = _entregar_senha(perfil, senha, novo.url_acesso)
    except ValidationError as recusa:
        ...
    except SmtpEnvioError:
        ...
    # A senha só escapa do ato por este caminho, e só depois de a transação ter fechado: cadastro
    # recusado sai pelos `except` acima, que devolvem desfecho sem perfil e sem senha.
    senha_a_exibir = None if entregue else senha
    return DesfechoCadastro(perfil=perfil, senha_a_exibir=senha_a_exibir)
```

**`apps/user_admin/context.py`**
```python
def contexto_cadastro_concluido(desfecho: DesfechoCadastro) -> dict[str, Any]:
    # `.get_secret_value()` é obrigatório: o SecretStr renderiza como `**********` no template, e o
    # modal sairia com asteriscos no lugar da senha, sem erro nenhum para denunciar.
    # `None` quando a senha foi entregue — e é esse `None` que apaga o modal E troca a frase do
    # painel, sem o template precisar conhecer o flag de envio.
    senha = desfecho.senha_a_exibir
    return {
        "perfil": desfecho.perfil,
        "senha_temporaria": senha.get_secret_value() if senha is not None else None,
    }
```

**`static/src/js/ui/copiar_senha.js`**
```javascript
// Terceiro caso do §7.2 do CLAUDE.md — estado visual de um controle, aprovado pelo usuário.
// Nenhum estado de domínio: a senha já está no DOM, e o botão só a move para o clipboard.
export function ligarCopiaDeSenha(raiz) {
  const botao = raiz.querySelector("[data-copiar-senha]");
  if (botao === null) return;
  botao.addEventListener("click", async () => {
    // `navigator.clipboard` não existe fora de contexto seguro (HTTP em IP de rede) — o catch é
    // o caminho real, não defensivo, e por isso o botão precisa saber dizer que falhou.
    try {
      await navigator.clipboard.writeText(botao.dataset.copiarSenha);
      trocarFace(botao, "copiado");
    } catch {
      trocarFace(botao, "falhou");
    }
  });
}
```

**`apps/user_admin/views.py`** — a view segue fina: entrega o desfecho ao contexto e não conhece o
flag de envio.
```python
    return render(request, TEMPLATE_CADASTRO_CONCLUIDO, contexto_cadastro_concluido(desfecho))
```

**`templates/user_admin/partials/_cadastro_concluido.html`** — o modal não é irmão do painel: sai
por **out-of-band** para um poço que vive fora da casca administrativa.
```html
{# O swap normal cai dentro da .admin-shell, que é `z-10` posicionada e portanto contexto de
   empilhamento: um modal `z-50` nascido ali fica sob os chips fixos `z-20` do base.html. O oob o
   entrega no #poco-modal, irmão da casca — mesmo poço que a perfil.html já usa. #}
{% if senha_temporaria %}
  <div id="poco-modal" hx-swap-oob="innerHTML">
    {% include "user_admin/partials/_modal_senha_desenvolvimento.html" %}
  </div>
{% endif %}
```

**`templates/user_admin/partials/_modal_senha_desenvolvimento.html`** — o toggle chega marcado, e é
só isso que abre o modal; o botão do painel de sucesso é um `<label for>` que o remarca depois de
fechado, sem novo request.
```html
<input type="checkbox" id="modal-senha" class="modal-toggle" checked />
```

## 7 · Caveats

A condição da [004](004-criar-servidor.md) que mantém a senha fora de toda tela passa a valer
enquanto `EMAIL_ENVIO_HABILITADO` estiver ligado — que é o único regime em que a 004 opera, já que
sem envio não há credencial entregue. Com o flag desligado a senha atravessa a resposta HTTP em texto
claro, porque sem isso o cadastro é inexercitável sem SMTP. O custo é que o flag vira, sozinho, a
fronteira entre desenvolvimento e exposição de credencial na tela, no histórico do navegador e em
qualquer cache no caminho — e a tarja de aviso é o que sinaliza de que lado dela se está.

`DesfechoCadastro` passa a carregar credencial até a view, quando antes carregava só o model gravado.
A alternativa — a view reler o flag e o ato devolver a senha sempre — espalharia a decisão por dois
módulos. O custo é que qualquer consumidor futuro do desfecho ganha acesso à senha sem pedir por ela.

O botão de copiar depende de `navigator.clipboard`, que não existe em contexto inseguro: por
`localhost` funciona, servido por IP de rede em HTTP, não. O fallback com `document.execCommand`
fica de fora porque a senha está em texto claro na tela de qualquer forma — quem não copiar pelo
botão copia a mão. O custo é um botão que falha em parte dos ambientes, e por isso a face de falha
é condição de pronto: sem ela o botão fica mudo e parece ter copiado.

## 8 · Testes (TDD)
Comportamento:
- `test_envio_desligado_devolve_senha_no_desfecho` — com o flag desligado, `criar_servidor` volta com `senha_a_exibir` preenchida *(marker `banco`)*
- `test_envio_ligado_nao_devolve_senha_no_desfecho` — com o flag ligado e SMTP respondendo, `senha_a_exibir` é `None` *(marker `banco`)*
- `test_senha_exibida_autentica_o_servidor` — a senha que sai no desfecho passa no `check_password` do perfil gravado *(marker `banco`)*
- `test_modal_da_senha_no_html_com_envio_desligado` — o POST de cadastro responde com a senha em texto claro e a tarja de aviso *(marker `banco`)*
- `test_senha_ausente_do_html_com_envio_ligado` — o mesmo POST, com envio ligado, não traz a senha em lugar nenhum da resposta *(marker `banco`)*
- `test_painel_de_sucesso_nao_promete_email_sem_envio` — com o flag desligado, o painel não afirma que a senha foi enviada *(marker `banco`)*
- `test_cadastro_recusado_nao_expoe_senha` — RF repetido com envio desligado devolve 422 sem senha alguma no corpo *(marker `banco`)*
