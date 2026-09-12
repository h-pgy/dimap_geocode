// A bancada que anda pela tela (SPEC design/018): limiar do clique, faixa de captura das bordas e
// a transmutação de eixo. Não sabe nada de ferramenta de desenho — só do corpo físico da bancada;
// o que precisa acontecer no domínio das ferramentas ao abrir/fechar chega por `ganchos`.

// Abaixo deste deslocamento o gesto ainda é clique: sem isso, todo toque na alça viraria arrasto
// de um pixel e a bancada nunca abriria.
const LIMIAR_ARRASTO = 4;
// Faixa de captura das bordas, generosa de propósito: errar por pouco deixaria a bancada boiando
// colada na borda, que é o pior dos dois mundos.
const MARGEM_ENCAIXE = 110;
// A transmutação: esvaziar, esticar, repovoar. Os tempos somam o que o olho lê como UM gesto.
const DURACAO_ESVAZIAR = 170;
const DURACAO_ESTICAR = 430;

// Encaixe à esquerda e à direita partilham o eixo: ir de um ao outro não transmuta nada.
const EIXO = { bottom: "deitada", left: "empe", right: "empe" };

function limitar(valor, minimo, maximo) {
  return Math.max(minimo, Math.min(maximo, valor));
}

// refs: os elementos do organismo. ganchos: o que o domínio das ferramentas precisa saber quando
// a bancada abre, fecha ou muda de encaixe — a bancada nunca chama desligarTudo/renderizar direto.
export function inicializarArrasto(refs, ganchos) {
  const { conjunto, alca, barra, telaMapa } = refs;
  const { fecharSubmenus, recolherFerramentas, renderizar } = ganchos;

  // Sem isto, arrastar a bancada arrasta o mapa e a roda sobre ela dá zoom.
  L.DomEvent.disableClickPropagation(conjunto);
  L.DomEvent.disableScrollPropagation(conjunto);

  let arrasto = null;

  function guardarBancada() {
    conjunto.classList.add("bancada-conjunto--fechada");
    alca.setAttribute("aria-expanded", "false");
    fecharSubmenus();
    recolherFerramentas();
  }

  function alternarBancada() {
    const fechada = conjunto.classList.toggle("bancada-conjunto--fechada");
    alca.setAttribute("aria-expanded", String(!fechada));
    if (fechada) {
      fecharSubmenus();
      recolherFerramentas();
    }
  }

  // Passa para posicionamento livre SEM pular: o lugar de agora vira left/top explícitos.
  function soltarNoPonto() {
    const caixa = conjunto.getBoundingClientRect();
    const limite = telaMapa.getBoundingClientRect();
    conjunto.classList.add("bancada-conjunto--solta");
    conjunto.style.left = caixa.left - limite.left + "px";
    conjunto.style.top = caixa.top - limite.top + "px";
    // Inline porque a âncora do dock tem especificidade maior que a da classe: sem zerar as duas
    // bordas opostas, o conjunto fica esticado entre `top` e `bottom` e a barra cresce.
    conjunto.style.right = "auto";
    conjunto.style.bottom = "auto";
  }

  function posicionarLivre(x, y) {
    const limite = telaMapa.getBoundingClientRect();
    const caixa = conjunto.getBoundingClientRect();
    conjunto.style.left = limitar(x - limite.left, 0, limite.width - caixa.width) + "px";
    conjunto.style.top = limitar(y - limite.top, 0, limite.height - caixa.height) + "px";
  }

  function reancorar(dock) {
    conjunto.dataset.dock = dock;
    conjunto.classList.remove("bancada-conjunto--solta");
    conjunto.style.left = "";
    conjunto.style.top = "";
    conjunto.style.right = "";
    conjunto.style.bottom = "";
  }

  function transmutarPara(dock, manterSolta) {
    const antes = barra.getBoundingClientRect();
    conjunto.classList.add("bancada-conjunto--transmutando");
    fecharSubmenus();

    window.setTimeout(() => {
      if (manterSolta) conjunto.dataset.dock = dock;
      else reancorar(dock);

      // Largura e altura não interpolam a partir de `auto`: mede-se o destino já com o layout
      // novo, volta-se para a medida antiga em px e só então se troca o alvo.
      const depois = barra.getBoundingClientRect();
      barra.style.width = antes.width + "px";
      barra.style.height = antes.height + "px";
      barra.getBoundingClientRect();
      barra.style.width = depois.width + "px";
      barra.style.height = depois.height + "px";

      window.setTimeout(() => {
        barra.style.width = "";
        barra.style.height = "";
        conjunto.classList.remove("bancada-conjunto--transmutando");
        // Encostar no rodapé é guardar a bancada, como empurrar a gaveta de volta. Solta no meio
        // da tela ela só se deita — não há gaveta para onde empurrar. guardarBancada já recolhe
        // as ferramentas e renderiza; nos demais casos isso fica por conta do chamador.
        if (dock === "bottom" && !manterSolta) guardarBancada();
        else renderizar();
      }, DURACAO_ESTICAR);
    }, DURACAO_ESVAZIAR);
  }

  // Quem decide o encaixe é o PONTEIRO, não o centro da bancada: presa dentro do mapa, uma caixa
  // de ~200px nunca leva o próprio centro até a margem, e o encaixe da borda mais distante não
  // dispararia nunca. O ponteiro é onde o usuário disse que quer, e não depende do tamanho da peça.
  function encaixarNaBorda(ponteiroX, ponteiroY) {
    const limite = telaMapa.getBoundingClientRect();
    const x = ponteiroX - limite.left;
    const y = ponteiroY - limite.top;

    let dock = null;
    if (x < MARGEM_ENCAIXE) dock = "left";
    else if (limite.width - x < MARGEM_ENCAIXE) dock = "right";
    else if (limite.height - y < MARGEM_ENCAIXE) dock = "bottom";
    // Fora de qualquer borda a bancada fica onde foi largada, mas deitada: em pé ela só existe
    // encaixada na lateral, que é o que justifica a coluna.
    if (!dock) {
      if (EIXO[conjunto.dataset.dock] === "empe") transmutarPara("bottom", true);
      return;
    }

    // Encaixar no mesmo eixo é só reancorar: transmutar exige a placa mudar de eixo.
    if (EIXO[dock] === EIXO[conjunto.dataset.dock]) {
      reancorar(dock);
      if (dock === "bottom") guardarBancada();
      else renderizar();
      return;
    }
    transmutarPara(dock);
  }

  alca.addEventListener("pointerdown", (evento) => {
    const caixa = conjunto.getBoundingClientRect();
    arrasto = {
      id: evento.pointerId,
      partiuX: evento.clientX,
      partiuY: evento.clientY,
      pegaX: evento.clientX - caixa.left,
      pegaY: evento.clientY - caixa.top,
      moveu: false,
    };
    alca.setPointerCapture(evento.pointerId);
  });

  alca.addEventListener("pointermove", (evento) => {
    if (!arrasto || evento.pointerId !== arrasto.id) return;
    const andou = Math.hypot(evento.clientX - arrasto.partiuX, evento.clientY - arrasto.partiuY);
    if (!arrasto.moveu && andou < LIMIAR_ARRASTO) return;
    if (!arrasto.moveu) {
      arrasto.moveu = true;
      conjunto.classList.remove("bancada-conjunto--fechada");
      alca.setAttribute("aria-expanded", "true");
      soltarNoPonto();
      conjunto.classList.add("bancada-conjunto--arrastando");
      alca.classList.add("bancada-alca--pega");
    }
    posicionarLivre(evento.clientX - arrasto.pegaX, evento.clientY - arrasto.pegaY);
  });

  function largarAlca(evento) {
    if (!arrasto || evento.pointerId !== arrasto.id) return;
    if (alca.hasPointerCapture(evento.pointerId)) alca.releasePointerCapture(evento.pointerId);
    conjunto.classList.remove("bancada-conjunto--arrastando");
    alca.classList.remove("bancada-alca--pega");
    if (arrasto.moveu) encaixarNaBorda(evento.clientX, evento.clientY);
    else alternarBancada();
    arrasto = null;
  }
  alca.addEventListener("pointerup", largarAlca);
  alca.addEventListener("pointercancel", largarAlca);
}
