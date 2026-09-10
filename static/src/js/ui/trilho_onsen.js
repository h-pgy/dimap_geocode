// O fio entintado da bandeja do .range-onsen (SPEC design/017): quanto do trilho já foi percorrido.
// É a única coisa que o CSS não lê sozinho — a posição do polegar não existe como seletor. Dono
// único do --preenchimento: o gesto do ponteiro chega pelo `input` delegado, e quem muda o valor
// por código chama pintarTrilho.
export function pintarTrilho(barra) {
  const min = Number(barra.min || 0);
  const max = Number(barra.max || 100);
  const fracao = max === min ? 0 : (Number(barra.value) - min) / (max - min);
  barra.style.setProperty("--preenchimento", `${(fracao * 100).toFixed(2)}%`);
}

document.addEventListener("input", (evento) => {
  const barra = evento.target.closest(".range-onsen");
  if (barra) pintarTrilho(barra);
});

document.querySelectorAll(".range-onsen").forEach(pintarTrilho);
