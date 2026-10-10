// O panorama do Google na gaveta inferior e o pino que anda com ele no mapa (SPEC street_view/002).
// Estado de interface, e só dele: a posição da câmera vive aqui até ser selecionada, quando vira
// desenho da bancada pelo mesmo evento do traço feito à mão.
import { ferramentaAtiva, iconePonto } from "./desenho/ferramentas.js";

const URL_DO_GOOGLE = "https://maps.googleapis.com/maps/api/js";
const RETORNO_DO_GOOGLE = "__streetViewPronto";
const PALCO = "[data-street-view]";
const TEMPO_DO_AVISO_MS = 4000;
const Z_DO_PINO = 1000;
// Folga, em px, entre o pino e a borda do que as gavetas deixam de mapa à vista.
const FOLGA = { lado: 56, topo: 96, rodape: 40 };
// O desenho é o do #glifo-ponto, cheio: por <use> o tema não alcançaria o preenchimento do corpo.
const SVG_DO_PINO =
  '<svg class="pino-panorama" viewBox="0 0 24 24" aria-hidden="true">' +
  '<path class="pino-panorama__corpo" stroke-width="1.6" stroke-linejoin="round" d="M12 21.5s7-6.6 7-11.5a7 7 0 1 0-14 0c0 4.9 7 11.5 7 11.5z"/>' +
  '<circle class="pino-panorama__olho" cx="12" cy="9.8" r="2.6"/>' +
  "</svg>";

const ESTADO = { panorama: null, servico: null, pino: null, emTela: null, selecionada: false };

let mapa = null;
let resultado = null;
let googleMaps = null;
let sumicoDoAviso = null;

const paraLeaflet = (latLng) => [latLng.lat(), latLng.lng()];

// O script do Google entra uma vez, no primeiro panorama: quem não abre o Street View não o baixa.
function carregarGoogle(chave) {
  googleMaps ??= new Promise((pronto, falhou) => {
    window[RETORNO_DO_GOOGLE] = async () => {
      await Promise.all([google.maps.importLibrary("streetView"), google.maps.importLibrary("geometry")]);
      pronto(google.maps);
    };
    // Chave recusada só se descobre depois da carga, e é o Google quem chama.
    window.gm_authFailure = recusarChave;
    const script = document.createElement("script");
    script.src =
      URL_DO_GOOGLE + "?key=" + encodeURIComponent(chave) + "&v=weekly&loading=async&callback=" + RETORNO_DO_GOOGLE;
    script.onerror = () => {
      // Sem isto a falha ficaria guardada, e a próxima abertura nem tentaria de novo.
      googleMaps = null;
      script.remove();
      falhou(new Error("o script do Google não carregou"));
    };
    document.head.append(script);
  });
  return googleMaps;
}

function procurar(alvo, raio) {
  return ESTADO.servico
    .getPanorama({
      location: alvo,
      radius: raio,
      preference: google.maps.StreetViewPreference.NEAREST,
      // Só acervo oficial e de rua: foto esférica de usuário não tem por onde andar.
      sources: [google.maps.StreetViewSource.GOOGLE, google.maps.StreetViewSource.OUTDOOR],
    })
    .then((resposta) => resposta.data);
}

const botaoDeSelecionar = (palco) => palco.closest(".gaveta-inferior").querySelector("[data-selecionar-posicao]");

// As faltas chegam escritas e ocultas: aqui só se revela a que aconteceu, no lugar do palco. Sem
// imagem não há posição a selecionar, e o botão sai junto.
function revelarFalta(palco, motivo) {
  palco.hidden = true;
  botaoDeSelecionar(palco).hidden = true;
  palco.parentElement.querySelectorAll(":scope > [data-falta]").forEach((falta) => {
    falta.hidden = falta.dataset.falta !== motivo;
  });
}

function avisarDestino() {
  const aviso = ESTADO.emTela.querySelector('[data-falta="sem_imagem_no_destino"]');
  aviso.hidden = false;
  clearTimeout(sumicoDoAviso);
  sumicoDoAviso = setTimeout(() => { aviso.hidden = true; }, TEMPO_DO_AVISO_MS);
}

// O que as gavetas deixam de mapa à vista: é para dentro disso que o pino é trazido.
function areaLivre() {
  const lateral = document.querySelector("#gaveta-entidade > .gaveta-lateral:has(> .gaveta-lateral-toggle:checked)");
  const placa = document.querySelector(".gaveta-toggle:checked + .gaveta-inferior");
  const recolhida = placa?.querySelector(":scope > .gaveta-inferior-recolher:checked");
  return {
    paddingTopLeft: [(lateral ? lateral.offsetWidth : 0) + FOLGA.lado, FOLGA.topo],
    paddingBottomRight: [FOLGA.lado, (placa && !recolhida ? placa.offsetHeight : 0) + FOLGA.rodape],
  };
}

function acompanhar() {
  if (ESTADO.pino === null) return;
  // Recém-criado, o panorama ainda não tem posição: o pino fica onde nasceu.
  const posicao = ESTADO.panorama.getPosition();
  if (posicao) ESTADO.pino.setLatLng(paraLeaflet(posicao));
  mapa.panInside(ESTADO.pino.getLatLng(), areaLivre());
}

// A gaveta foi puxada: o palco mudou de tamanho, e a área livre do mapa também.
function acomodar() {
  if (ESTADO.panorama === null) return;
  google.maps.event.trigger(ESTADO.panorama, "resize");
  acompanhar();
}

// Recolher e reabrir uma gaveta muda a área livre sem mudar a altura de nenhuma.
function reacomodar(evento) {
  if (evento.target.matches(".gaveta-inferior-recolher, .gaveta-lateral-toggle")) acompanhar();
}

async function soltar(raio) {
  const destino = ESTADO.pino.getLatLng();
  const achado = await procurar({ lat: destino.lat, lng: destino.lng }, raio).catch(() => null);
  // A gaveta pode ter fechado enquanto o Google respondia.
  if (ESTADO.pino === null) return;
  if (achado === null) {
    acompanhar();
    avisarDestino();
    return;
  }
  // Trocar pelo mesmo panorama não dispara position_changed: o pino volta à imagem por aqui.
  if (achado.location.pano === ESTADO.panorama.getPano()) {
    acompanhar();
    return;
  }
  ESTADO.panorama.setPano(achado.location.pano);
}

function criarPino(posicao, raio) {
  const pino = L.marker(paraLeaflet(posicao), {
    icon: L.divIcon({ className: "", html: SVG_DO_PINO, iconSize: [36, 36], iconAnchor: [18, 32] }),
    draggable: true,
    zIndexOffset: Z_DO_PINO,
    // Sem isto o Geoman o conta como desenho da bancada: repintado, listado e apagado como um.
    pmIgnore: true,
  }).addTo(mapa);
  const desenho = () => pino.getElement().querySelector(".pino-panorama");
  pino.on("dragstart", () => desenho().classList.add("pino-panorama--arrastando"));
  pino.on("dragend", () => {
    desenho().classList.remove("pino-panorama--arrastando");
    soltar(raio);
  });
  return pino;
}

async function abrir(palco) {
  const alvo = { lat: Number(palco.dataset.lat), lng: Number(palco.dataset.lon) };
  const raio = Number(palco.dataset.raio);
  const maps = await carregarGoogle(palco.dataset.chave).catch(() => null);
  // A cada espera a gaveta pode ter fechado: o palco que pediu já não é o que está em tela.
  if (ESTADO.emTela !== palco) return;
  if (maps === null) {
    revelarFalta(palco, "indisponivel");
    return;
  }
  ESTADO.servico = new maps.StreetViewService();
  const achado = await procurar(alvo, raio).catch(() => null);
  if (ESTADO.emTela !== palco) return;
  if (achado === null) {
    revelarFalta(palco, "sem_imagem");
    return;
  }
  ESTADO.panorama = new maps.StreetViewPanorama(palco.querySelector("[data-tela]"), {
    pano: achado.location.pano,
    // Sem o rumo o Google escolhe o sentido da via, e a câmera nasce de costas para o endereço.
    pov: { heading: maps.geometry.spherical.computeHeading(achado.location.latLng, alvo), pitch: 0 },
    addressControl: false,
    fullscreenControl: false,
  });
  palco.querySelector("[data-espera]").hidden = true;
  botaoDeSelecionar(palco).disabled = false;
  // Só agora o ponto do endereço sai de cena: na falta, ele fica como estava.
  resultado.ocultar();
  ESTADO.pino = criarPino(achado.location.latLng, raio);
  ESTADO.panorama.addListener("position_changed", acompanhar);
  // Com o pino no mapa o duplo clique deixa de ser do zoom: na falta, ele segue aproximando.
  mapa.doubleClickZoom.disable();
  acompanhar();
}

// Tira o panorama e o pino de cena e diz onde o pino estava; sem pino, não havia o que desfazer.
function desmontar() {
  if (ESTADO.panorama !== null) google.maps.event.clearInstanceListeners(ESTADO.panorama);
  ESTADO.panorama = null;
  if (ESTADO.pino === null) return null;
  const posicao = ESTADO.pino.getLatLng();
  mapa.removeLayer(ESTADO.pino);
  ESTADO.pino = null;
  mapa.doubleClickZoom.enable();
  return posicao;
}

function recusarChave() {
  const palco = ESTADO.emTela;
  if (palco === null) return;
  if (desmontar() !== null) resultado.devolver();
  revelarFalta(palco, "indisponivel");
}

// A gaveta saiu do DOM. Selecionada, a posição vira ponto desenhado; fechada pelo ✕, o ponto do
// endereço volta.
function encerrar() {
  const posicao = desmontar();
  if (posicao !== null && ESTADO.selecionada) {
    const ponto = L.marker(posicao, { icon: iconePonto("normal") }).addTo(mapa);
    mapa.fire("pm:create", { shape: "Marker", layer: ponto, selecionado: String(L.Util.stamp(ponto)) });
  } else if (posicao !== null) {
    resultado.devolver();
  }
  ESTADO.selecionada = false;
}

// O "Selecionar esta posição" e o ✕ fecham pela mesma rota: o último acionado diz se a posição fica.
function marcarSelecao(evento) {
  const fecho = evento.target.closest?.("#gaveta-inferior-conteudo [hx-post]");
  if (fecho) ESTADO.selecionada = fecho.matches("[data-selecionar-posicao]");
}

// Callback de evento do HTMX: o palco que chegou abre, o que sumiu encerra.
function conferir() {
  const palco = document.querySelector(PALCO);
  if (palco === ESTADO.emTela) return;
  if (ESTADO.emTela !== null) encerrar();
  ESTADO.emTela = palco;
  if (palco !== null) abrir(palco);
}

// Registrado no dblclick do mapa pelo init.js: o pino vai ao lugar clicado e segue o caminho de quem
// foi arrastado e solto ali.
export function levarPino(evento) {
  // Sem pino não há Street View aberto, e o duplo clique é do zoom.
  if (ESTADO.pino === null) return;
  // Com ferramenta na mão os dois cliques já são do traço.
  if (mapa.pm.globalDrawModeEnabled() || ferramentaAtiva(mapa)) return;
  const raio = Number(ESTADO.emTela.dataset.raio);
  ESTADO.pino.setLatLng(evento.latlng);
  soltar(raio);
}

// `camadaDeResultado` é o par { ocultar, devolver } do init.js, dono da camada de resultado: tirar
// de cena não é destruir.
export function inicializarStreetView(mapaDaHome, camadaDeResultado) {
  mapa = mapaDaHome;
  resultado = camadaDeResultado;
  htmx.on("htmx:afterSettle", conferir);
  document.addEventListener("click", marcarSelecao);
  document.addEventListener("change", reacomodar);
  document.addEventListener("gaveta-inferior:puxada", acomodar);
}
