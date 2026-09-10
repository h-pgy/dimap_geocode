// Água sobre o fundo administrativo (SPEC design/017): um campo de altura simulado em WebGL2, do
// qual se extrai a cáustica e o brilho da crista. Exceção declarada ao §7.2 do CLAUDE.md — não há
// regra de negócio, estado de domínio nem UI montada a partir de JSON aqui dentro (Caveats).
const SELETOR = ".fundo-agua";
const MAX_GOTAS = 8;
const RESOLUCAO_SIM = 256;
const PASSO = 1 / 30;
const MAX_SUBPASSOS = 3;
const ESCALA_RENDER = 0.6;
const FONTES_AMBIENTES = 10;
// Teto do sorteio da abertura, em segundos. Cobre várias voltas do seno mais lento da deriva
// (~120s no preset), então duas cargas seguidas caem em pontos sem parentesco.
const DESLOCAMENTO_MAXIMO = 600;
// Cinco segundos simulados antes do primeiro quadro: é o que a superfície leva para sair do plano.
const PASSOS_DE_AQUECIMENTO = 150;
const TAU = Math.PI * 2;
const UNIFORMES_DE_PINTURA = [
  "caustica",
  "piso",
  "teto",
  "contraste",
  "ganho",
  "escalaNormal",
  "brilho",
  "dureza",
  "grao",
];

// O preset é o estado de repouso da peça: a água é textura do fundo, não assunto da tela.
export const PADRAO = Object.freeze({
  propagacao: 0.245, // abaixo de 0.25 é a condição de estabilidade da equação de onda
  amortecimento: 0.998,
  caustica: 7.0, // quanto o relevo comprime o mapa de raios
  piso: 0.3, // achata o pico da cáustica — é este número que tira a água "intensa"
  teto: 2.4,
  contraste: 1.0,
  ganho: 0.3, // desvio máximo em torno do neutro
  escalaNormal: 10.5,
  brilho: 0.13,
  dureza: 90,
  grao: 0.012,
  velocidadeDeriva: 0.75,
  baseDeriva: 0.012,
  ganhoDeriva: 0.9,
  tetoDeriva: 0.06,
  raioDeriva: 0.045,
  fontes: 4,
  forcaGota: 0.015,
  periodoGota: 2.4,
});

// Mutável de propósito: é o que a torre de ajustes escreve e o shader lê a cada quadro.
export const PARAMETROS = { ...PADRAO };

const VERT = `#version 300 es
out vec2 vUv;
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  vUv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

// O estado é um campo de altura em duas texturas alternadas: `r` é a altura atual, `g` é a do
// passo anterior — a equação de onda precisa das duas.
const FRAG_ATUALIZA = `#version 300 es
precision highp float;
uniform sampler2D uEstado;
uniform vec2 uTexel;
uniform float uAspecto;
uniform float uPropagacao;
uniform float uAmortecimento;
uniform int uQuantasGotas;
uniform vec4 uGotas[${MAX_GOTAS}];
in vec2 vUv;
out vec4 saida;
void main() {
  vec2 uv = vUv;
  float atual = texture(uEstado, uv).r;
  float anterior = texture(uEstado, uv).g;
  float e = texture(uEstado, uv - vec2(uTexel.x, 0.0)).r;
  float d = texture(uEstado, uv + vec2(uTexel.x, 0.0)).r;
  float c = texture(uEstado, uv + vec2(0.0, uTexel.y)).r;
  float b = texture(uEstado, uv - vec2(0.0, uTexel.y)).r;

  // Equação de onda discreta: extrapola a altura anterior e corrige pelo laplaciano dos vizinhos.
  float nova = (2.0 * atual - anterior) + (e + d + c + b - 4.0 * atual) * uPropagacao;
  nova *= uAmortecimento;

  // Cada gota é uma gaussiana somada ao relevo.
  for (int i = 0; i < ${MAX_GOTAS}; i++) {
    if (i >= uQuantasGotas) break;
    vec2 delta = uv - uGotas[i].xy;
    delta.x *= uAspecto;
    nova += uGotas[i].z * exp(-dot(delta, delta) / (uGotas[i].w * uGotas[i].w));
  }

  // A borda absorve em vez de refletir: onda que volta da parede vira padrão estacionário visível.
  vec2 margem = min(uv, 1.0 - uv);
  nova *= mix(0.9, 1.0, smoothstep(0.0, 0.045, min(margem.x, margem.y)));

  saida = vec4(clamp(nova, -1.6, 1.6), atual, 0.0, 1.0);
}`;

const FRAG_PINTA = `#version 300 es
precision highp float;
uniform sampler2D uEstado;
uniform vec2 uTexel;
uniform vec2 uResolucao;
uniform float uTempo;
uniform float uAspecto;
uniform float uCaustica;
uniform float uPiso;
uniform float uTeto;
uniform float uContraste;
uniform float uGanho;
uniform float uEscalaNormal;
uniform float uBrilho;
uniform float uDureza;
uniform float uGrao;
in vec2 vUv;
out vec4 cor;

float ruido(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

void main() {
  vec2 uv = vUv, t = uTexel;
  float h   = texture(uEstado, uv).r;
  float he  = texture(uEstado, uv - vec2(t.x, 0.0)).r;
  float hd  = texture(uEstado, uv + vec2(t.x, 0.0)).r;
  float hc  = texture(uEstado, uv + vec2(0.0, t.y)).r;
  float hb  = texture(uEstado, uv - vec2(0.0, t.y)).r;
  float hdc = texture(uEstado, uv + t).r;
  float heb = texture(uEstado, uv - t).r;
  float hdb = texture(uEstado, uv + vec2(t.x, -t.y)).r;
  float hec = texture(uEstado, uv + vec2(-t.x, t.y)).r;

  float hx = (hd - he) * 0.5;
  float hy = (hc - hb) * 0.5;
  float hxx = hd - 2.0 * h + he;
  float hyy = hc - 2.0 * h + hb;
  float hxy = (hdc - hdb - hec + heb) * 0.25;

  // Cáustica: a luz que atravessa a superfície chega ao fundo comprimida na razão do jacobiano do
  // mapa de raios refratados. |det| < 1 concentra luz; superfície plana dá det = 1.
  float jxx = 1.0 - uCaustica * hxx;
  float jyy = 1.0 - uCaustica * hyy;
  float jxy = -uCaustica * hxy;
  float det = jxx * jyy - jxy * jxy;
  float ca = pow(clamp(1.0 / max(abs(det), uPiso), 0.0, uTeto), uContraste);

  // O glint que a crista acende, sob um sol frio e alto.
  vec3 normal = normalize(vec3(-hx * uEscalaNormal, -hy * uEscalaNormal, 1.0));
  vec3 meio = normalize(vec3(0.30, 0.45, 0.82) + vec3(0.0, 0.0, 1.0));
  float glint = pow(max(dot(normal, meio), 0.0), uDureza) * uBrilho;

  // O invariante: 0.5 é o neutro do soft-light. Água em repouso ⇒ det = 1 ⇒ ca = 1 ⇒ 0.5 exato, e
  // a camada some. A água só sabe desviar a luz do que já está atrás; ela não pinta nada.
  float luz = 0.5 + (ca - 1.0) * uGanho + glint;

  // A borda volta ao neutro: é onde a simulação tem artefato, e nenhum deles pode chegar à tela.
  luz = mix(luz, 0.5, smoothstep(0.55, 1.05, length((uv - 0.5) * vec2(uAspecto, 1.0))));

  luz += (ruido(uv * uResolucao + fract(uTempo)) - 0.5) * uGrao;

  cor = vec4(vec3(luz), 1.0);
}`;

function compilar(gl, tipo, fonte) {
  const shader = gl.createShader(tipo);
  gl.shaderSource(shader, fonte);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader));
  }
  return shader;
}

function programa(gl, vertice, fragmento) {
  const compilado = gl.createProgram();
  gl.attachShader(compilado, compilar(gl, gl.VERTEX_SHADER, vertice));
  gl.attachShader(compilado, compilar(gl, gl.FRAGMENT_SHADER, fragmento));
  gl.linkProgram(compilado);
  if (!gl.getProgramParameter(compilado, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(compilado));
  }
  return compilado;
}

function criarAlvo(gl) {
  const textura = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, textura);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, RESOLUCAO_SIM, RESOLUCAO_SIM, 0, gl.RGBA, gl.HALF_FLOAT, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, textura, 0);
  gl.clearColor(0, 0, 0, 1);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  return { textura, fbo };
}

const limitar = (valor) => Math.min(Math.max(valor, 0.06), 0.94);

// Soma de senos incomensuráveis: os períodos não têm razão racional entre si, então o traço nunca
// se fecha e a deriva não repete o caminho.
function derivaEm(tempo) {
  const s = PARAMETROS.velocidadeDeriva;
  const x = 0.5 + 0.30 * Math.sin(tempo * 0.037 * TAU * s) + 0.12 * Math.sin(tempo * 0.011 * TAU * s + 1.7);
  const y = 0.5 + 0.28 * Math.cos(tempo * 0.043 * TAU * s) + 0.13 * Math.cos(tempo * 0.017 * TAU * s + 4.1);
  return [limitar(x), limitar(y)];
}

function sortearFontes() {
  const fontes = [];
  for (let i = 0; i < FONTES_AMBIENTES; i++) {
    fontes.push({
      px: 0.2 + 0.6 * Math.random(),
      py: 0.2 + 0.6 * Math.random(),
      ax: 0.1 + 0.1 * Math.random(),
      ay: 0.1 + 0.1 * Math.random(),
      sx: 0.05 + 0.08 * Math.random(),
      sy: 0.05 + 0.08 * Math.random(),
      fx: Math.random() * TAU,
      fy: Math.random() * TAU,
      proxima: Math.random() * 1.2,
    });
  }
  return fontes;
}

function criarAgua(tela) {
  const gl = tela.getContext("webgl2", { alpha: false, antialias: false, depth: false });
  if (!gl) return null;
  // Sem alvo de ponto flutuante o campo de altura não tem onde ser guardado com sinal.
  if (!gl.getExtension("EXT_color_buffer_float") && !gl.getExtension("EXT_color_buffer_half_float")) {
    return null;
  }
  gl.getExtension("OES_texture_half_float_linear");

  const progAtualiza = programa(gl, VERT, FRAG_ATUALIZA);
  const progPinta = programa(gl, VERT, FRAG_PINTA);
  const vao = gl.createVertexArray();
  const alvos = [criarAlvo(gl), criarAlvo(gl)];

  gl.bindFramebuffer(gl.FRAMEBUFFER, alvos[0].fbo);
  const completo = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (!completo) return null;

  const gotas = new Float32Array(MAX_GOTAS * 4);
  const fontes = sortearFontes();
  const inicio = performance.now();
  // A abertura é sorteada: sem isto a deriva entra sempre no mesmo ponto e percorre sempre o mesmo
  // traço, e navegar entre telas mostra a mesma cena toda vez. O aquecimento soma aqui também —
  // adiantar o relógio é o que mantém a passagem para o tempo real contínua, sem salto.
  let defasagem = Math.random() * DESLOCAMENTO_MAXIMO;
  const agora = () => (performance.now() - inicio) / 1000 + defasagem;

  let leitura = 0;
  let aspecto = 1;
  let fila = [];
  let derivaX = 0.5;
  let derivaY = 0.5;
  let derivaIniciada = false;

  function redimensionar() {
    const dpr = Math.min(devicePixelRatio || 1, 2) * ESCALA_RENDER;
    const largura = tela.clientWidth || 1;
    const altura = tela.clientHeight || 1;
    aspecto = largura / altura;
    tela.width = Math.max(1, Math.round(largura * dpr));
    tela.height = Math.max(1, Math.round(altura * dpr));
  }
  new ResizeObserver(redimensionar).observe(tela);
  redimensionar();

  function enfileirar(x, y, forca, raio) {
    if (fila.length < MAX_GOTAS) fila.push([x, y, forca, raio]);
  }

  // Quem mexe a água é a deriva invisível: a camada não é alcançável pelo ponteiro, então não há
  // gesto nenhum para escutar.
  function coletarDeriva(tempo) {
    const [x, y] = derivaEm(tempo);
    if (!derivaIniciada) {
      derivaX = x;
      derivaY = y;
      derivaIniciada = true;
    }
    const distancia = Math.hypot(x - derivaX, y - derivaY);
    const forca = Math.min(PARAMETROS.baseDeriva + distancia * PARAMETROS.ganhoDeriva, PARAMETROS.tetoDeriva);
    if (forca > 1e-4) enfileirar(x, y, forca, PARAMETROS.raioDeriva);
    derivaX = x;
    derivaY = y;
  }

  function coletarAmbiente(tempo, passo) {
    for (let i = 0; i < Math.min(PARAMETROS.fontes, fontes.length); i++) {
      const fonte = fontes[i];
      fonte.proxima -= passo;
      if (fonte.proxima > 0) continue;
      fonte.proxima = PARAMETROS.periodoGota * (0.7 + Math.random() * 0.6);
      const x = limitar(fonte.px + fonte.ax * Math.sin(tempo * fonte.sx * TAU + fonte.fx));
      const y = limitar(fonte.py + fonte.ay * Math.cos(tempo * fonte.sy * TAU + fonte.fy));
      enfileirar(x, y, PARAMETROS.forcaGota, 0.03 + Math.random() * 0.02);
    }
  }

  function simular() {
    const tempo = agora();
    coletarDeriva(tempo);
    coletarAmbiente(tempo, PASSO);

    const quantas = Math.min(fila.length, MAX_GOTAS);
    gotas.fill(0);
    for (let i = 0; i < quantas; i++) gotas.set(fila[i], i * 4);
    fila = [];

    const origem = alvos[leitura];
    const destino = alvos[leitura ^ 1];
    gl.useProgram(progAtualiza);
    gl.bindVertexArray(vao);
    gl.bindFramebuffer(gl.FRAMEBUFFER, destino.fbo);
    gl.viewport(0, 0, RESOLUCAO_SIM, RESOLUCAO_SIM);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, origem.textura);
    gl.uniform1i(gl.getUniformLocation(progAtualiza, "uEstado"), 0);
    gl.uniform2f(gl.getUniformLocation(progAtualiza, "uTexel"), 1 / RESOLUCAO_SIM, 1 / RESOLUCAO_SIM);
    gl.uniform1f(gl.getUniformLocation(progAtualiza, "uAspecto"), aspecto);
    gl.uniform1f(gl.getUniformLocation(progAtualiza, "uPropagacao"), PARAMETROS.propagacao);
    gl.uniform1f(gl.getUniformLocation(progAtualiza, "uAmortecimento"), PARAMETROS.amortecimento);
    gl.uniform1i(gl.getUniformLocation(progAtualiza, "uQuantasGotas"), quantas);
    gl.uniform4fv(gl.getUniformLocation(progAtualiza, "uGotas"), gotas);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    leitura ^= 1;
  }

  function pintar() {
    gl.useProgram(progPinta);
    gl.bindVertexArray(vao);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, tela.width, tela.height);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, alvos[leitura].textura);
    gl.uniform1i(gl.getUniformLocation(progPinta, "uEstado"), 0);
    gl.uniform2f(gl.getUniformLocation(progPinta, "uTexel"), 1 / RESOLUCAO_SIM, 1 / RESOLUCAO_SIM);
    gl.uniform2f(gl.getUniformLocation(progPinta, "uResolucao"), tela.width, tela.height);
    gl.uniform1f(gl.getUniformLocation(progPinta, "uTempo"), agora());
    gl.uniform1f(gl.getUniformLocation(progPinta, "uAspecto"), aspecto);
    for (const nome of UNIFORMES_DE_PINTURA) {
      const uniforme = "u" + nome[0].toUpperCase() + nome.slice(1);
      gl.uniform1f(gl.getUniformLocation(progPinta, uniforme), PARAMETROS[nome]);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  // A tela não abre com a água parada: o campo nasce plano, e sem aquecer não há relevo para a
  // cáustica ler nos primeiros segundos.
  for (let i = 0; i < PASSOS_DE_AQUECIMENTO; i++) {
    defasagem += PASSO;
    simular();
  }

  // Um quadro antes de qualquer coisa: com `alpha: false` o backbuffer intocado compõe como preto
  // opaco, e sob soft-light isso é um piscar escuro na tela inteira.
  pintar();

  return { simular, pintar };
}

const tela = document.querySelector(SELETOR);
// Lido uma vez, no boot: reagir à troca em tempo real pediria destruir e reconstruir o contexto
// WebGL para um ajuste que se faz nas preferências do sistema operacional (Caveats da SPEC).
const parado = matchMedia("(prefers-reduced-motion: reduce)").matches;
const agua = tela && !parado ? criarAgua(tela) : null;

// Três motivos derrubam a água, e o desfecho dos três é o mesmo: o canvas sai do documento, em vez
// de ficar como camada de blend inerte custando composição por nada.
if (tela && !agua) tela.remove();

let ligada = false;
let acumulado = 0;
let ultimo = 0;
let pedido = null;

// Passo fixo com acumulador e teto de sub-passos: a simulação não acelera nem estoura quando o
// navegador atrasa um quadro.
function quadro(instante) {
  const decorrido = Math.min((instante - ultimo) / 1000, 0.25);
  ultimo = instante;
  acumulado += decorrido;

  let feitos = 0;
  while (acumulado >= PASSO && feitos < MAX_SUBPASSOS) {
    agua.simular();
    acumulado -= PASSO;
    feitos += 1;
  }
  agua.pintar();
  pedido = requestAnimationFrame(quadro);
}

function rodar() {
  if (!agua || !ligada || document.hidden || pedido !== null) return;
  ultimo = performance.now();
  acumulado = 0;
  pedido = requestAnimationFrame(quadro);
}

function parar() {
  cancelAnimationFrame(pedido);
  pedido = null;
}

export function existe() {
  return agua !== null;
}

export function ligar() {
  ligada = true;
  if (tela) tela.hidden = false;
  rodar();
}

export function desligar() {
  ligada = false;
  if (tela) tela.hidden = true;
  parar();
}

// O rAF já é estrangulado em aba oculta, mas não parado em todo navegador — e um fundo decorativo
// não pode custar GPU numa aba que ninguém está vendo.
document.addEventListener("visibilitychange", () => (document.hidden ? parar() : rodar()));
