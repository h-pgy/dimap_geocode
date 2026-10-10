---
spec: documentos_oficiais/010
versao: v2
atualizado_em: 2026-09-09
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial implementada
  - v2: código inexistente devolve formulário com erro e realce semântico sem alertar letras ausentes
---

# SPEC documentos_oficiais/010 — UX da validação de documento

## 1 · User story
Quem recebeu um documento da DIMAP escolhe o caminho de conferência (arquivo ou código) na tela de validação para conferir a autenticidade da via que tem em mãos.

## 2 · Condições de pronto
- [x] Clicar em "Validar documento" na home abre uma **página de escolha** com dois cards: "Tenho o documento em mãos" e "Tenho o código em mãos".
- [x] Selecionar "Tenho o documento em mãos" leva à tela de upload.
- [x] Selecionar "Tenho o código em mãos" mostra um formulário com campo de código (12 caixas OTP).
- [x] O campo de código aceita qualquer caractere alfanumérico e **não informa** nem restringe letras ausentes no alfabeto interno dos identificadores gerados.
- [x] Digitar um código não localizado no acervo devolve o **mesmo formulário** com status 422, mensagem "Código errado" e realce semântico de erro (`.campo-realce-erro`) nas caixas do OTP.
- [x] Digitar um código válido e existente no acervo redireciona para a conferência do documento (`/d/{codigo}`).
- [x] Na tela de upload, **antes** de enviar um arquivo, o botão "Conferir documento" **não aparece**.
- [x] Depois de escolher um arquivo, o botão "Conferir documento" aparece.
- [x] Depois de conferir, o resultado **substitui** o widget de upload; o botão vira "Carregar novo documento".
- [x] O design foi aprovado no mock e as peças portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A conferência por código consome a busca no acervo da SPEC [documentos_oficiais/008](008-acervo-e-conferencia.md) para verificar se o identificador existe. A submissão do formulário adota o contrato da skill `erros-de-formulario` para retorno de recusa com realce de controle.

```python
class ConferenciaCodigoInput(BaseModel):
    codigo: str = Field(min_length=12, max_length=12)
```

**Mock:** [010-mock-ux-validar-documento.html](010-mock-ux-validar-documento.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Prévia local do arquivo (miniatura, nome exibido) — JS de estado; sem dono ainda.
- Validação client-side do formato/tamanho antes de enviar — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/documentos/acervo.py` → `buscar_registro`: consulta ao acervo de documentos emitidos.
- `@templates/documentos/conferencia.html` → tela de upload com fluxo progressivo.
- `@templates/documentos/conferencia_codigo.html` → formulário de digitação do código.
- `@templates/documentos/conferencia_por_codigo.html` → tela da ficha do documento localizado.
- `@static/src/js/ui/otp_onsen.js` → módulo do OTP: navegação e preenchimento das 12 caixas.
- `@services/utils/erros_formulario` → tradução de erro e mapeamento de realce semântico.
- Skills: `mock`, `componentes-frontend`, `daisyui`, `erros-de-formulario`.

## 6 · Snippets
**`apps/documentos/formularios.py`**
```python
# Catálogo do formulário de conferência por código (skill erros-de-formulario).
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    TradutorDeRecusa,
)

FORMULARIO_CODIGO = Formulario(
    campos=(
        CampoDeFormulario(controle="codigo", rotulo="Código do documento"),
    )
)

traduzir_recusa_codigo = TradutorDeRecusa(FORMULARIO_CODIGO)
```

**`apps/documentos/views.py`**
```python
# A view valida o código recebido via POST: se inexistente, devolve o formulário com status 422 e recusa traduzida.
def pagina_conferencia(request: HttpRequest) -> HttpResponse:
    via = request.GET.get("via") or request.POST.get("via")
    if via == "codigo":
        if request.method == "POST":
            codigo = request.POST.get("codigo", "").strip().upper()
            registro = buscar_registro(codigo) if len(codigo) == 12 else None
            if registro is None:
                recusa = traduzir_recusa_codigo(
                    (ErroBruto(controle="codigo", tipo="invalido", mensagem="Código errado"),)
                )
                contexto = {
                    "recusa": recusa,
                    "valores": {"codigo": codigo},
                    **contexto_fundo_admin(),
                }
                return render(request, "documentos/conferencia_codigo.html", contexto, status=422)
            return redirect("documentos:conferir", codigo=codigo)
        return render(request, "documentos/conferencia_codigo.html", contexto_fundo_admin())
    ...
```

**`templates/documentos/conferencia_codigo.html`**
```html
{# O formulário submete via POST; em caso de erro, exibe a mensagem e aplica .campo-realce-erro nas caixas #}
<form method="post" action="{% url 'documentos:pagina' %}?via=codigo" class="flex flex-col gap-6" id="form-codigo">
  {% csrf_token %}
  <input type="hidden" name="via" value="codigo" />
  <input type="hidden" name="codigo" id="codigo-valor" value="{{ valores.codigo|default:'' }}" />

  {% if recusa %}
    <div class="p-3 bg-error/10 border border-error/30 text-xs text-error rounded-lg font-medium text-center">
      {% for mensagem in recusa.mensagens %}{{ mensagem }}{% endfor %}
    </div>
  {% endif %}

  <div class="flex flex-col gap-2">
    <label class="text-xs font-bold uppercase tracking-wider text-center text-base-content/70">Código do documento:</label>
    <div class="otp-onsen otp-onsen-12 my-2 flex-wrap"
         data-otp-alvo="#codigo-valor"
         data-otp-auto-submit="#form-codigo"
         data-otp-botao-verificar="#btn-verificar-codigo">
      {% for _ in "123456789012" %}
        <input type="text" inputmode="text" maxlength="1" class="otp-caixa {{ recusa.realce.codigo }}" />
      {% endfor %}
    </div>
  </div>

  <button type="submit" id="btn-verificar-codigo" class="btn btn-onsen w-full">Verificar</button>
  <a href="{% url 'documentos:pagina' %}" class="btn-etched btn-etched-swell etched etched-deeper self-center">Voltar</a>
</form>
```

**`static/src/js/ui/otp_onsen.js`**
```javascript
// Aceita qualquer caractere alfanumérico sem restrição client-side de letras e limpa realce de erro na digitação.
const regex = isNumeric ? /\D/g : /[^a-zA-Z0-9]/g;

caixa.addEventListener("input", () => {
  caixas.forEach((c) => c.classList.remove("campo-realce-erro"));
  ...
});
```

## 7 · Caveats
A interface aceita qualquer caractere alfanumérico no campo de código sem filtrar letras fora do alfabeto de emissão (I, L, O e U). Essa escolha evita revelar publicamente a regra interna de formação dos identificadores. O custo é postergar a rejeição de caracteres incompatíveis para a consulta ao acervo no backend, respondendo com erro uniforme.

A submissão de código inexistente ou inválido devolve sempre a mesma resposta no formulário com status 422. Essa uniformidade impede aferir se determinado formato de código chegou a existir no acervo. O custo é não orientar o usuário sobre a natureza específica de uma eventual falha de digitação.

## 8 · Testes (TDD)
- `test_pagina_escolha_conferencia_mostra_dois_caminhos` — valida status 200, links e cards na rota `/d/`.
- `test_pagina_conferencia_por_codigo_mostra_12_caixas_otp_sem_aviso_de_letras` — valida tela de digitação com 12 caixas e ausência de texto sobre exclusão de letras.
- `test_conferencia_codigo_inexistente_devolve_mesmo_formulario_com_status_422_e_realce_erro` — código inexistente devolve o mesmo formulário com status 422, mensagem "Código errado" e realce semântico nas caixas. *(marker `banco`)*
- `test_conferencia_codigo_com_letras_omitidas_submete_e_devolve_erro` — código contendo caracteres como I, L, O ou U é aceito no input e recusado na validação com status 422. *(marker `banco`)*
- `test_conferencia_codigo_existente_redireciona_para_tela_do_documento` — código válido e existente no acervo responde redirecionamento (302) para `/d/{codigo}`. *(marker `banco`)*
- `test_pagina_upload_mostra_formulario_com_botao_oculto_e_link_voltar` — valida tela de upload com botão inicialmente oculto.
- `test_carregar_novo_documento_devolve_formulario_limpo` — valida recarga do formulário via HTMX.
- `test_resultado_conferencia_arquivo_inclui_botao_carregar_novo_documento` — valida que a resposta traz o botão para carregar novo documento direcionado para `#area-upload`. *(marker `banco`)*

