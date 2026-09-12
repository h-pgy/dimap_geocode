// A bancada de desenho (SPEC design/018): substitui a toolbar nativa do Leaflet-Geoman — addControls
// nunca é chamado. Orquestra catálogo, adaptador do plugin e arrasto; sai do ar sem o partial no DOM.
import { GEOMETRIAS } from "./catalogo.js";
import {
  CURSOR_DA_FERRAMENTA,
  CURSORES,
  acionar,
  categoriaDaFerramenta,
  desligarTudo,
  ferramentaAtiva,
  haGeometria,
  haPoligono,
  podeConcluir,
} from "./ferramentas.js";
import { inicializarArrasto } from "./arrasto.js";

// Largura/altura não interpolam a partir de `auto`: mede-se antes, aplica-se a mutação, mede-se
// depois, e só então se anima entre as duas medidas.
const DURACAO_CRESCER = 320;

// `aria-disabled`, nunca o `disabled` nativo: o atributo do HTML bloqueia até o hover e cala o
// title do botão — o tooltip precisa continuar dizendo o que o glifo é mesmo sem afordância. Quem
// barra o clique é o guard em cada handler, não o browser.
function indisponivel(botao) {
  return botao.getAttribute("aria-disabled") === "true";
}

export function inicializarBancadaDesenho(mapa) {
  const conjunto = document.getElementById("bancada-conjunto");
  if (!conjunto || !mapa) return;

  const telaMapa = mapa.getContainer().parentElement;
  const lonaDoMapa = mapa.getContainer();
  const alca = document.getElementById("bancada-alca");
  const barra = document.getElementById("bancada-barra");
  const submenu = document.getElementById("bancada-submenu");
  const btnCancelar = document.getElementById("btn-cancelar");
  const btnConcluir = document.getElementById("btn-concluir");
  const btnApagar = document.getElementById("btn-apagar");
  const btnEditar = document.getElementById("btn-editar");
  const btnSnap = document.getElementById("btn-snap");
  const torreSnap = document.getElementById("torre-snap");
  const snapToggle = document.getElementById("snap-toggle");
  const linhaFerramentas = conjunto.querySelector(".bancada-desenho__ferramentas");
  const poco = conjunto.querySelector(".bancada-desenho__poco");
  const categorias = Array.from(conjunto.querySelectorAll("[data-categoria]"));

  // Nasce desligado: repouso em madeira, a torrezinha é quem liga.
  mapa.pm.setGlobalOptions({ snappable: false, snapDistance: 20 });

  let categoriaAberta = null;
  let formaEmDesenho = null;

  // ── Render ─────────────────────────────────────────────────────────────────────────────────
  function montarTrilha(categoria) {
    const ativa = ferramentaAtiva(mapa, formaEmDesenho);
    submenu.innerHTML = "";

    GEOMETRIAS[categoria].forEach((ferramenta) => {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "bancada-submenu__tool";
      botao.title = ferramenta.rotulo;
      botao.setAttribute("aria-label", ferramenta.rotulo);
      botao.setAttribute("role", "menuitemradio");
      // Recortar só opera sobre área: com ponto e linha no mapa, a ferramenta não tem alvo.
      botao.setAttribute("aria-disabled", String(ferramenta.id === "cut" && !haPoligono(mapa)));
      const eAtiva = ferramenta.id === ativa;
      botao.classList.toggle("bancada-submenu__tool--ativa", eAtiva);
      botao.setAttribute("aria-checked", String(eAtiva));
      botao.innerHTML = '<svg viewBox="0 0 24 24"><use href="' + ferramenta.glifo + '"/></svg>';
      botao.addEventListener("click", () => {
        if (indisponivel(botao)) return;
        acionar(mapa, ferramenta.id, formaEmDesenho);
        renderizar();
      });
      submenu.appendChild(botao);
    });
  }

  function renderizar() {
    const ativa = ferramentaAtiva(mapa, formaEmDesenho);
    const dona = ativa ? categoriaDaFerramenta(ativa) : null;

    categorias.forEach((botao) => {
      const nome = botao.dataset.categoria;
      // O lápis mora no poço e usa a marca do controle; as geometrias, a da categoria.
      const marcaAtiva = botao.classList.contains("bancada-desenho__controle")
        ? "bancada-desenho__controle--ativo"
        : "bancada-desenho__categoria--ativa";
      botao.classList.toggle(marcaAtiva, nome === dona);
      botao.setAttribute("aria-expanded", String(nome === categoriaAberta));
    });

    // Sem nada desenhado não há o que editar: o estado de falta é o lápis apagado, não uma
    // bandeja aberta com um aviso dentro.
    btnEditar.setAttribute("aria-disabled", String(!haGeometria(mapa)));

    btnCancelar.setAttribute("aria-disabled", String(!ativa));
    btnCancelar.classList.toggle("bancada-desenho__controle--armado", Boolean(ativa));

    const concluivel = podeConcluir(mapa, formaEmDesenho);
    btnConcluir.setAttribute("aria-disabled", String(!concluivel));
    btnConcluir.classList.toggle("bancada-desenho__controle--armado", concluivel);

    btnApagar.setAttribute("aria-disabled", String(!haGeometria(mapa)));
    btnApagar.classList.toggle("bancada-desenho__controle--armado-apagar", ativa === "remove");

    const cursor = ativa ? CURSOR_DA_FERRAMENTA[ativa] : null;
    CURSORES.forEach((nome) => lonaDoMapa.classList.toggle("mapa-cursor--" + nome, nome === cursor));

    if (categoriaAberta) montarTrilha(categoriaAberta);
  }

  // ── Submenu: a linha que nasce DENTRO do corpo ────────────────────────────────────────────────
  function animarCorpo(mutacao) {
    const antes = barra.getBoundingClientRect();
    mutacao();
    const depois = barra.getBoundingClientRect();
    if (Math.abs(antes.width - depois.width) < 1 && Math.abs(antes.height - depois.height) < 1) return;

    barra.classList.add("bancada-desenho--crescendo");
    barra.style.width = antes.width + "px";
    barra.style.height = antes.height + "px";
    barra.getBoundingClientRect();
    barra.style.width = depois.width + "px";
    barra.style.height = depois.height + "px";

    window.setTimeout(() => {
      barra.style.width = "";
      barra.style.height = "";
      barra.classList.remove("bancada-desenho--crescendo");
    }, DURACAO_CRESCER);
  }

  // O submenu abre sempre imediatamente acima da linha de quem o abriu — daí ele mudar de lugar
  // no DOM em vez de existir duas vezes.
  function abrirBandeja(categoria) {
    animarCorpo(() => {
      categoriaAberta = categoria;
      montarTrilha(categoria);
      const vizinha = categoria === "modificar" ? poco : linhaFerramentas;
      barra.insertBefore(submenu, vizinha);
      submenu.classList.remove("bancada-submenu--fechado");
    });
  }

  function fecharBandeja() {
    if (!categoriaAberta) return;
    animarCorpo(() => {
      categoriaAberta = null;
      submenu.classList.add("bancada-submenu--fechado");
    });
  }

  // ── Torrezinha do encaixe ──────────────────────────────────────────────────────────────────
  function fecharTorreSnap() {
    torreSnap.classList.add("torre-snap--fechada");
    btnSnap.setAttribute("aria-expanded", "false");
  }

  btnSnap.addEventListener("click", () => {
    const aberta = torreSnap.classList.toggle("torre-snap--fechada");
    btnSnap.setAttribute("aria-expanded", String(!aberta));
  });

  snapToggle.addEventListener("change", () => {
    mapa.pm.setGlobalOptions({ snappable: snapToggle.checked });
    btnSnap.classList.toggle("bancada-desenho__controle--ligado", snapToggle.checked);
  });

  // ── Categorias de geometria ────────────────────────────────────────────────────────────────
  categorias.forEach((botao) => {
    botao.addEventListener("click", () => {
      if (indisponivel(botao)) return;
      const nome = botao.dataset.categoria;
      fecharTorreSnap();

      if (GEOMETRIAS[nome].length === 1) {
        fecharBandeja();
        acionar(mapa, GEOMETRIAS[nome][0].id, formaEmDesenho);
        renderizar();
        return;
      }
      if (categoriaAberta === nome) fecharBandeja();
      else abrirBandeja(nome);
      renderizar();
    });
  });

  btnCancelar.addEventListener("click", () => {
    if (indisponivel(btnCancelar)) return;
    desligarTudo(mapa);
    renderizar();
  });

  // O mesmo caminho do Enter do plugin (finishOnEnter), pelo botão. `_finishShape` é API privada
  // do Geoman: não há caminho público para encerrar a forma em desenho de fora (SPEC §7 Caveats).
  btnConcluir.addEventListener("click", () => {
    if (!podeConcluir(mapa, formaEmDesenho)) return;
    mapa.pm.Draw[formaEmDesenho]._finishShape();
    renderizar();
  });

  btnApagar.addEventListener("click", () => {
    if (indisponivel(btnApagar)) return;
    fecharTorreSnap();
    acionar(mapa, "remove", formaEmDesenho);
    renderizar();
  });

  // ── A bancada anda pela tela ───────────────────────────────────────────────────────────────
  inicializarArrasto(
    { conjunto, alca, barra, telaMapa },
    {
      fecharSubmenus: () => {
        fecharBandeja();
        fecharTorreSnap();
      },
      recolherFerramentas: () => {
        desligarTudo(mapa);
        renderizar();
      },
      renderizar,
    },
  );

  // ── Sincronia com o plugin ─────────────────────────────────────────────────────────────────
  mapa.on("pm:globaldrawmodetoggled", (evento) => {
    formaEmDesenho = evento.enabled ? evento.shape : null;
    renderizar();
  });
  [
    "pm:globaleditmodetoggled",
    "pm:globaldragmodetoggled",
    "pm:globalrotatemodetoggled",
    "pm:globalcutmodetoggled",
    "pm:globalremovalmodetoggled",
  ].forEach((evento) => mapa.on(evento, renderizar));

  // O Ok arma conforme os vértices caem. O pm:vertexadded do plugin dispara na WORKING LAYER, e
  // não no mapa — escutá-lo no mapa deixava o botão morto durante o desenho inteiro.
  mapa.on("pm:drawstart", (evento) => {
    evento.workingLayer.on("pm:vertexadded", renderizar);
    renderizar();
  });
  mapa.on("pm:drawend", renderizar);

  // Círculo não existe em GeoJSON: vira polígono antes de qualquer coisa depender dele.
  mapa.on("pm:create", (evento) => {
    if (evento.shape === "Circle") L.PM.Utils.circleToPolygon(evento.layer, 60);
    renderizar();
  });
  mapa.on("pm:remove", renderizar);

  // O Esc do Geoman (exitModeOnEscape) já larga a ferramenta; aqui ele só fecha o que é UI.
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") return;
    fecharTorreSnap();
    renderizar();
  });

  document.addEventListener("click", (evento) => {
    if (!barra.contains(evento.target)) fecharTorreSnap();
  });

  renderizar();
}
