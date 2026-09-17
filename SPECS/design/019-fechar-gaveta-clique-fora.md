---
spec: design/019
versao: v3
atualizado_em: 2026-09-17
testes_tdd: false
implementado: true
changelog:
  - v1: versão inicial
  - v2: gatilho passa de duplo clique para clique único — duplo clique colidia com o zoom do Leaflet
  - v3: arrasto (ex. navegar o mapa) deixa de recolher a gaveta, só o clique parado
---

# SPEC design/019 — Fechar a gaveta lateral com um clique fora

## 1 · User story
O servidor da DIMAP, com a gaveta lateral aberta sobre o mapa, dá um clique fora dela para recolhê-la
sem procurar a paleta.

## 2 · Condições de pronto
- [ ] Com a gaveta lateral aberta, um clique **fora** da sua casca — mapa de fundo, UI flutuante ou
      qualquer área que não seja a gaveta — a recolhe.
- [ ] Um clique **dentro** da gaveta (painel, paleta ou segunda gaveta aberta) não a recolhe.
- [ ] Com a gaveta já recolhida, um clique em qualquer lugar não tem efeito sobre ela.
- [ ] Um clique que **começa com arrasto** — como navegar o mapa de fundo — não recolhe a gaveta,
      mesmo terminando fora dela.
- [ ] Fechar por clique fora reacomoda a bancada de desenho do mesmo jeito que fechar pela paleta já
      faz hoje.

## 3 · Domínio
SPEC de interface pura: não introduz domínio. Consome só a casca `.gaveta-lateral` e o checkbox
`.gaveta-lateral-toggle` entregues pela [SPEC design/013](013-gaveta-lateral-e-paleta.md), que
continuam sendo a única fonte de estado — este JS lê e altera esse checkbox, nunca guarda estado
próprio.

## 4 · Fora de escopo
- Fechar a gaveta com a tecla `Esc` — sem dono ainda.
- Clique fora fechando a segunda gaveta **sem** fechar a primeira — não é este comportamento; as
  duas continuam viajando juntas, como já rege a SPEC design/013.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.gaveta-lateral` / `.gaveta-lateral-toggle`: a casca e o
  interruptor que já leem o estado aberto/recolhido.
- `@static/src/js/mapa/desenho/bancada.js` → lê `:checked` do mesmo checkbox e reage ao evento
  `change` disparado nele: o contrato que este JS novo precisa honrar.
- `@templates/core/home.html` → onde a gaveta da busca vive e onde o script novo é incluído.
- Skills: `componentes-frontend`.

## 6 · Snippets

**`static/src/js/ui/fechar_gaveta_clique_fora.js`**
```javascript
// Cada gaveta aberta é um checkbox .gaveta-lateral-toggle filho direto de .gaveta-lateral (SPEC
// design/013). "Fora" é qualquer clique cujo alvo não esteja dentro dessa casca.
const LIMIAR_ARRASTO_PX = 6;

function gavetasAbertas() {
  return document.querySelectorAll(".gaveta-lateral > .gaveta-lateral-toggle:checked");
}

// O DOM não distingue "clique" de "clique que terminou em outro lugar" — arrastar o mapa é
// mousedown + mousemove + mouseup, e o navegador ainda dispara "click" ao final. Guardamos onde o
// gesto começou para medir o deslocamento até o clique.
let origemClique = null;

document.addEventListener("pointerdown", (evento) => {
  origemClique = { x: evento.clientX, y: evento.clientY };
});

document.addEventListener("click", (evento) => {
  const arrastou =
    origemClique &&
    Math.hypot(evento.clientX - origemClique.x, evento.clientY - origemClique.y) > LIMIAR_ARRASTO_PX;
  if (arrastou) return;

  gavetasAbertas().forEach((toggle) => {
    if (toggle.parentElement.contains(evento.target)) return;
    toggle.checked = false;
    // bancada.js só reacomoda a régua ao ouvir "change" — setar checked por JS não dispara sozinho.
    toggle.dispatchEvent(new Event("change", { bubbles: true }));
  });
});
```

**`templates/core/home.html`** — inclusão do script novo
```html
{% block scripts %}
  <script type="module" src="{% static 'js/busca/feedback_selecao.js' %}"></script>
  <script type="module" src="{% static 'js/busca/atalho_foco_busca.js' %}"></script>
  <script type="module" src="{% static 'js/ui/fechar_gaveta_clique_fora.js' %}"></script>
{% endblock %}
```

## 7 · Caveats
Esta SPEC não traz mock, o que tensiona a regra geral de que toda SPEC de interface exige um. Nenhum
estado visual novo é introduzido — a gaveta só ganha um segundo gatilho para a mesma transição que a
SPEC design/013 já validou. O custo é confiar nessa validação anterior em vez de repetir o percurso
visual num mock novo.

O `dispatchEvent` manual existe porque `bancada.js` só reage ao evento `change`, nunca à leitura
direta de `:checked`. A razão é que setar `.checked` via JS não dispara `change` sozinho — só a
interação do usuário faz isso. O custo é este módulo precisar conhecer, ainda que superficialmente,
que existe um consumidor do evento além do CSS.

O clique fora não interrompe a propagação, então um clique sobre o mapa de fundo fecha a gaveta **e**
segue disparando o comportamento nativo do Leaflet para aquele clique (seleção, pan). A razão é que
impedir a propagação exigiria listar exceções por elemento, o que é mais frágil do que aceitar os
dois efeitos juntos. O custo é o mapa reagir ao mesmo clique que fecha a gaveta.

O limiar que separa clique de arrasto é um número arbitrário (`LIMIAR_ARRASTO_PX`), não uma medida
tirada do Leaflet. A razão é que o DOM não expõe a distância que o próprio Leaflet usa internamente
para decidir se um gesto foi arrasto. O custo é um valor que pode precisar de ajuste fino se algum
dispositivo de entrada mostrar falsos positivos.

## 8 · Testes (TDD)
_Sem teste automatizado._ O que aprova esta SPEC é a conferência manual, com a gaveta de lote ou de
endereço aberta: clique parado no mapa de fundo ou na UI flutuante recolhe a gaveta; clique dentro do
painel, na paleta ou na segunda gaveta aberta não recolhe; arrastar o mapa (pan) soltando o botão
fora da gaveta **não** a recolhe; com a gaveta já recolhida, clique em qualquer lugar não tem efeito;
e, depois do fechamento por clique fora, a bancada de desenho reacomoda a régua esquerda como já faz
ao fechar pela paleta.
