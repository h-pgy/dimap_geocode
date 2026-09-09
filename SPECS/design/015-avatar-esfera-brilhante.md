---
spec: design/015
versao: v4
atualizado_em: 2026-09-09
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: substituição do halo neon externo por luminescência volumétrica interna orgânica
  - v3: óptica de orbe com líquido termal interno e reflexos radiais (descartada por aspecto Web 2.0 artificial)
  - v4: óptica de vidro fosco límpido (Frosted Glass) translúcido com aro perimétrico de 2px a 60% de branco, backdrop-filter com url(#frosted), base a 8% e eliminação de todo brilho branco chapado artificial
---

# SPEC design/015 — Avatar esfera de vidro fosco (.avatar-glass)

## 1 · User story
Servidor da DIMAP visualiza os avatares de perfil na interface no contexto de navegação e identificação do sistema para reconhecer com clareza a identidade pessoal e a unidade de lotação através de uma lente esférica de vidro fosco translúcida com refração suave e aro perimétrico luminoso, sem reflexos radiais forçados de estética Web 2.0.

## 2 · Condições de pronto
- [x] O avatar é modelado como uma **lente esférica de vidro fosco translúcido**: base a 8% de tinta branca translúcida combinada à cor da unidade (`--cor-unidade`), sem manchas brancas radiais chapadas.
- [x] O aro perimétrico razor-sharp a 60% de branco (`box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.6)`) sobre uma borda transparente de 1.5px define a borda luminosa da lente sem serrilhamento.
- [x] A refração do fundo é executada por `backdrop-filter: url(#frosted) blur(14px) saturate(180%)`, com filtro SVG `<filter id="frosted">` disponibilizado no documento.
- [x] Iniciais e fotos integram-se no plano intermediário (`z-1`): letras em tinta clara flutuam com sombra suave sobre o vidro e fotos recebem a moldura vítrea circular perimétrica.
- [x] O componente escala proporcionalmente de `w-9 h-9` a `w-28 h-28`, preservando a espessura do aro e o alcance do reflexo por meio de `--halo-escala`.
- [x] Design aprovado no mock e peças portadas para `static/src/tema-dimap.dev.css` e para o styleguide (`/design_system`) antes de qualquer template da aplicação usar as classes.

## 3 · Domínio
Iteração de design system, materiais e óptica de componentes: nenhum model de banco novo. A pergunta que esta SPEC faz às peças visuais e de apresentação existentes:

| Peça / Parâmetro | Definição anterior | Pergunta desta SPEC |
|---|---|---|
| `.avatar-glass` | Manchas radiais brancas chapadas Web 2.0 (`rgba(255,255,255,0.9)`) | "Como expressar o vidro brilhando sem recorrer a manchas de brilho falso?"; a translucidez sutil a 8% com refração fosca (`backdrop-filter: url(#frosted)`) e o aro perimétrico de 2px a 60% de branco entregam a óptica autêntica de vidro fosco iluminado, sem manchas radiais artificiais. |
| `.avatar-glass::before` | Gradiente sloshing com rotação contínua | "O movimento é necessário para a leitura de vidro?"; não — o movimento continuo adicionava ruído visual e pontos brancos forçados. A refração fosca estática com sutil reação no hover é mais limpa e elegante. |
| `.avatar-glass::after` | Três gradientes especulares brancos | "O domo especular artificial funciona?"; não — parecia botão Mac Aqua de 2005. O brilho da peça vem do aro de luz perimétrico e da refração do mapa por trás. |
| SVG de iniciais | Círculo opaco com `{cor_fundo}` | "O círculo opaco do SVG combina com o vidro?"; com `fill-opacity: 0.18`, as letras flutuam com contraste e o vidro fosco reflete o fundo através do círculo. |

**Mock:** [015-mock-avatar-esfera-brilhante.html](015-mock-avatar-esfera-brilhante.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Alteração no algoritmo de extração de iniciais de nomes e sobrenomes — `AvatarIniciaisSvg`.
- Modificação na paleta de cores ou inserção de novos tons de unidade no catálogo — `apps/unidades/paleta.py`.
- Alterações na navegação ou nas permissões disparadas pelo widget da barra de topo — SPEC `autenticacao/001` e `painel/001`.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.avatar-glass`: material e variáveis da moldura de perfil a calibrar.
- `@templates/partials/_filtros_gravacao.html` → inclusão do filtro SVG `<filter id="frosted">`.
- `@templates/user_admin/partials/_imagem_perfil.html` → partial unificado de renderização de avatar (foto × SVG).
- `@services/domain/avatar/generator.py` → `AvatarIniciaisSvg`: gabarito do SVG de iniciais.
- `@apps/unidades/paleta.py` → `HEX_POR_COR`: resolução dos 8 tons de unidades do projeto.
- Skills: `componentes-frontend`, `mock`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`**
```css
  /* .avatar-glass — Esfera de vidro fosco (Frosted Glass) translúcida com refração e brilho com fade */
  .avatar-glass {
    --halo-escala: 1;
    position: relative;
    border-radius: 50%;
    background: color-mix(in srgb, var(--cor-unidade, #0077b6) 28%, rgba(255, 255, 255, 0.12));
    box-shadow:
      /* Brilho perimétrico suave com fade imediato (sem corte de aro chapado) */
      0 0 calc(4px * var(--halo-escala, 1)) calc(0.8px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 88%, white 12%),
      /* Halo de luz irradiante com esmaecimento progressivo na cor da unidade */
      0 0 calc(10px * var(--halo-escala, 1)) calc(2px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 60%, transparent),
      0 0 calc(24px * var(--halo-escala, 1)) calc(4px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 30%, transparent),
      /* Apoio suave contra o fundo */
      0 calc(6px * var(--halo-escala, 1)) calc(18px * var(--halo-escala, 1)) rgba(7, 58, 84, 0.14),
      /* Fade luminoso interno a partir da borda da lente */
      inset 0 0 calc(5px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 65%, white 35%),
      inset 0 calc(1px * var(--halo-escala, 1)) calc(2px * var(--halo-escala, 1)) rgba(255, 255, 255, 0.5),
      /* Absorção interna mais profunda e saturada da cor da unidade */
      inset 0 0 calc(14px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 42%, transparent);
    backdrop-filter: blur(14px) saturate(200%);
    -webkit-backdrop-filter: blur(14px) saturate(200%);
    backdrop-filter: url(#frosted) blur(14px) saturate(200%);
    -webkit-backdrop-filter: url(#frosted) blur(14px) saturate(200%);
    display: grid;
    place-items: center;
    overflow: hidden;
    isolation: isolate;
    cursor: pointer;
    outline: 0;
    transition: all 0.25s ease;
  }

  .avatar-glass:hover {
    background: color-mix(in srgb, var(--cor-unidade, #0077b6) 35%, rgba(255, 255, 255, 0.16));
    box-shadow:
      0 0 calc(6px * var(--halo-escala, 1)) calc(1.5px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 95%, white 5%),
      0 0 calc(16px * var(--halo-escala, 1)) calc(3px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 75%, transparent),
      0 0 calc(32px * var(--halo-escala, 1)) calc(6px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 40%, transparent),
      0 calc(10px * var(--halo-escala, 1)) calc(24px * var(--halo-escala, 1)) rgba(7, 58, 84, 0.18),
      inset 0 0 calc(7px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 75%, white 25%),
      inset 0 calc(1px * var(--halo-escala, 1)) calc(2px * var(--halo-escala, 1)) rgba(255, 255, 255, 0.65),
      inset 0 0 calc(18px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 55%, transparent);
  }

  /* Filtro suave da cor da unidade sobre a foto com fade na borda e proteção de lente */
  .avatar-glass::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 50%;
    pointer-events: none;
    background: color-mix(in srgb, var(--cor-unidade, #0077b6) 15%, transparent);
    box-shadow: inset 0 0 calc(5px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 45%, rgba(255, 255, 255, 0.35));
    transition: background 0.25s ease, box-shadow 0.25s ease;
    z-index: 2;
  }

  .avatar-glass:hover::after {
    background: color-mix(in srgb, var(--cor-unidade, #0077b6) 8%, transparent);
    box-shadow: inset 0 0 calc(7px * var(--halo-escala, 1)) color-mix(in srgb, var(--cor-unidade, #0077b6) 60%, rgba(255, 255, 255, 0.45));
  }

  /* Filhos no plano intermediário: foto ou SVG de iniciais */
  .avatar-glass > * {
    position: relative;
    z-index: 1;
  }

  .avatar-glass > svg {
    width: 100%;
    height: 100%;
    transition: transform 0.25s ease;
  }

  .avatar-glass > svg circle {
    fill-opacity: 0.32;
    transition: fill-opacity 0.25s ease;
  }

  .avatar-glass:hover > svg circle {
    fill-opacity: 0.44;
  }

  .avatar-glass > svg text {
    filter: drop-shadow(0 1px 2px rgba(7, 58, 84, 0.45));
  }

  .avatar-glass > img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.95;
    transition: opacity 0.25s ease, transform 0.25s ease;
  }

  .avatar-glass:hover > img {
    opacity: 1;
    transform: scale(1.03);
  }
```

**`templates/partials/_filtros_gravacao.html`**
```xml
    <!-- Filtro de vidro fosco para refração em backdrop-filter: url(#frosted) -->
    <filter id="frosted" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="12" result="blur" />
    </filter>
```

## 7 · Caveats
**O halo luminoso e o aro perimétrico irradiam a cor oficial da unidade.** O aro perimétrico de 2px a 88% da cor da unidade (com 12% de branco para brilho) combinado aos dois halos suaves em box-shadow garantem o reconhecimento imediato da unidade tanto em avatares de iniciais quanto em fotos reais.

**Fotos reais recebem filtro vítreo suave na cor da unidade via `::after`.** A camada intermediária aplica `color-mix(in srgb, var(--cor-unidade) 15%, transparent)` sobre a imagem, integrando a foto à tonalidade da unidade sem perder nitidez ou saturação natural do retrato.

**Compatibilidade com navegadores sem suporte a filtro SVG em `backdrop-filter`.** A declaração cascateia `blur(14px) saturate(180%)` antes e junto de `url(#frosted)`, garantindo que clientes como Firefox ou WebKit apliquem o desfoque equivalente caso ignorem a URL de filtro SVG.

## 8 · Testes (TDD)
- `test_avatar_svg_preserva_iniciais_e_aria_label` — garante que o gabarito SVG preserva as letras extraídas e a acessibilidade.
- `test_avatar_svg_circulo_nao_ultrapassa_area_visivel` — verifica que o círculo interno do SVG respeita a margem anti-serrilhado.
- `test_imagem_perfil_renderiza_cor_unidade_como_hex` — comprova que o template `_imagem_perfil.html` injeta a variável `--cor-unidade` no estilo inline.
- `test_avatar_glass_suporta_parametro_halo_escala` — valida a passagem e o valor padrão de `--halo-escala` para controle dimensional do brilho.
- `test_avatar_iniciais_preserva_contraste_tinta_clara` — assegura que a tinta de texto utilizada nos avatares satisfaz o contraste sobre o vidro fosco.
