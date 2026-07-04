---
name: componentes-frontend
description: Princípios de design, UX e padronização dos componentes de front-end do DIMAP GeoCoder. Sempre ative ao trabalhar na interface web, views ou templates HTML.
---

# Princípios de Design e Front-end (DIMAP GeoCoder)

Esta skill define as diretrizes arquiteturais de UI/UX e a padronização do código front-end (HTML, CSS, HTMX) do projeto DIMAP GeoCoder.

## 1. O Tema "Onsen de Inverno" (Cores, Essência e Poesia Visual)
O design system do projeto transcende paletas estáticas para abraçar uma experiência sensorial: a de estar em um **"Onsen de Inverno"**. O usuário deve sentir como se estivesse *observando as montanhas geladas sob a luz fria de um dia encoberto de inverno, através de um vidro espesso e levemente embaçado, enquanto a iluminação ciana da água quente pulsa logo abaixo de si*. 
A interface materializa essa poesia contrastando o mapa geográfico denso e escurecido (a paisagem fria/água profunda) com componentes de UI maciços, feitos de vidro grosso esculpido que captura e refrata a luz ambiente.
- **O Mapa (Água Fria):** Escuro, dessaturado e com um tom azulado constante. 
- **Primária (`#48CAE4` - Ciano/Água):** Cor de energia. Usada puramente para luz, sombras (tintadas) e brilho de elementos ativos.
- **Secundária (`#5E412F` - Madeira escurecida):** Traz calor orgânico. Usada ESTRITAMENTE para tipografia (fontes) e ícones. **Jamais** use a cor secundária como *background* de preenchimento de painéis ou botões, pois destrói o contraste com o fundo escuro.
- **Accent (`#0F766E` - Dark Teal/Verde):** Cor de suporte fria para dar leitura em badges, tags e rótulos menores, sem quebrar o clima gélido.
*(Consulte `references/paleta.json` e a visualização `wireframes/paleta_onsen_inverno.html` para as escalas exatas)*.

### 1.1 A Paleta Base (Configuração Tailwind)
Esta é a assinatura exata de cores que deve guiar a configuração do Tailwind no projeto. 
*(Nota: No ambiente de produção com Tailwind v4, essas variáveis serão mapeadas nativamente via `@theme` no CSS).*

```javascript
// Configuração do Tema - Onsen de Inverno
tailwind.config = {
  theme: {
    extend: {
      colors: {
        primary: "#48CAE4",
        secondary: "#5E412F",
        accent: "#0F766E",
        neutral: "#0D1B2A",
        "base-100": "#F8F9FA",
        "base-content": "#0D1B2A",
        "primary-content": "#0D1B2A",
        "secondary-content": "#F8F9FA"
      }
    }
  }
}
```

### 1.2 Progressive Disclosure (Arquivos de Referência)
Para garantir que outros desenvolvedores e agentes de IA compreendam a construção da interface em camadas (do conceito abstrato ao código exato), os seguintes artefatos oficiais devem ser consultados na seguinte ordem:
1. **Moodboard Conceitual:** `references/onsen_inverno_moodboard.jpg` (A visão sensorial da iluminação ciana sobre água fria).
2. **Imagens de Inspiração:** `references/referencia_original_ui_1.jpg` e `references/referencia_original_ui_2.jpg` (As referências brutas fornecidas na concepção, ditando o nível de transparência, vidro e polimento esperado).
3. **Utilitárias CSS Base:** `references/design_system.css` (O arquivo contendo as abstrações `@apply` das regras visuais do vidro espesso, prontas para inclusão em produção).
4. **Mockup Funcional Original:** `examples/mock_ui_initial.html` (A prova de conceito HTML inicial onde todas as classes foram testadas de forma inline).
5. **Mockup Componentizado:** `examples/mock_ui.html` (A prova de conceito final, refatorada com o bloco CSS de `@apply` abstraído para fácil visualização e compartilhamento).

## 2. Padronização: Partials (Domínio) vs `@apply` (Design Coeso)
A divisão de responsabilidades na montagem da UI deve seguir a regra:
- **Partials do Django/HTMX resolvem DOMÍNIO:** Crie arquivos HTML separados (`card_imovel.html`, `card_logradouro.html`) encapsulando a lógica de cada entidade de negócio. Não misture domínios com `if/elses` no mesmo HTML.
- **`@apply` no CSS resolve DESIGN:** Para garantir o "mesmo DNA" visual nas diferentes entidades, crie classes unificadas no CSS do Tailwind (ex: `.card-resultado { @apply ...; }`).
- **NÃO crie classes via `@utility`** para bordas/cores avulsas. Confie nas variáveis semânticas do tema (`bg-base-100`, `text-primary`).

### 2.1 CSS Base (Referência de `@apply`)
Para garantir a consistência do design system, as seguintes classes devem ser declaradas no arquivo CSS principal do projeto (`index.css` ou `global.css`) usando a diretiva `@apply` do Tailwind:

```css
/* A Base do Vidro Espesso (3px) com Sombra Tintada Ciana */
.glass-panel {
  @apply backdrop-blur-[2px] border-[3px] border-t-white/10 border-l-white/5 border-r-white/5 border-b-transparent shadow-[0_20px_40px_-10px_rgba(72,202,228,0.35)];
}

/* Gradiente da Gaveta (Brilha na direita, esmaece na esquerda) */
.glass-drawer-bg {
  @apply bg-gradient-to-l from-base-100/50 via-base-100/20 to-base-100/10;
}

/* Gradiente de Painéis Flutuantes Centrais (ex: Barra de Busca) */
.glass-float-bg {
  @apply bg-gradient-to-br from-base-100/10 to-base-100/20;
}

/* Ícones em Alto Relevo de Vidro */
.glass-icon {
  @apply !bg-transparent stroke-white/50 text-white/10 drop-shadow-[0_4px_8px_rgba(72,202,228,0.4)];
}

/* Badges e Tags (Cristalinas) */
.glass-badge {
  @apply bg-accent/10 text-accent font-medium rounded-md px-2 py-1 border border-accent/20;
}

/* Transições e Coreografia de Foco */
.transition-glass {
  @apply transition-all duration-500 ease-in-out;
}

/* Ocultação cinematográfica (ex: Barra de Busca sumindo quando gaveta abre) */
.glass-hide-up {
  @apply opacity-0 -translate-y-5 scale-95 pointer-events-none;
}

/* Camada de Desfoque Dinâmico (Lente) */
.cinematic-blur-layer {
  @apply absolute inset-0 z-10 pointer-events-none opacity-0 backdrop-blur-sm transition-opacity duration-500;
}
.cinematic-blur-layer.active {
  @apply opacity-100 pointer-events-auto;
}
```

## 3. Glassmorphism Padrão Ouro (O Vidro Espesso)
*(Referência prática: inspecione os componentes da UI no arquivo de demonstração em `examples/mock_ui_initial.html`)*
Os elementos flutuantes do sistema NÃO são plástico transparente fino; eles simulam **blocos de vidro espesso**. Para atingir esse padrão, aplique religiosamente as seguintes regras:
- **Blur Fraco (`backdrop-blur-[2px]`):** Blurs pesados (como `blur-md` ou `blur-2xl`) estragam o vidro e o deixam opaco ("chapadão"). O mapa ao fundo **deve** ser perfeitamente legível em movimento atrás da UI.
- **Massa e Arestas (`border-[3px]`):** O vidro precisa de volume físico. Todas as bordas primárias têm exatos 3 pixels de espessura (ou `border-y-[3px] border-r-[3px] border-l-0` dependendo das quinas expostas).
- **Refração Subliminar (Bordas Direcionais):** A luz ambiente bate na quina do vidro e some rapidamente. NUNCA desenhe bordas brancas opacas e contínuas (ex: `border-white/80` é terminantemente proibido). A aresta externa de onde vem a luz ganha apenas `border-t-white/10`, as laterais enfraquecem para `border-x-white/5` e a base de oclusão afunda na água com `border-b-transparent`.
- **Luminosidade Interna (Background Gradients):** O preenchimento do vidro deve contrabalançar o escurecimento do mapa ao fundo, "emitindo" luz. Use gradientes opacos que partem da borda exterior em direção à raiz do elemento. Ex: `bg-gradient-to-l from-base-100/50 via-base-100/20 to-base-100/10`.
- **Sombras Tintadas (Efeito Neon na Água):** Sombras pretas ou neutras (`shadow-xl`) são vetadas em elementos *glass*. A sombra representa a luz colorida da UI atravessando o vidro e batendo na água. Use *drop-shadows* puramente Cianos: `shadow-[0_20px_40px_-10px_rgba(72,202,228,0.35)]`.
- **Alto Relevo de Vidro (Ícones):** Ícones flutuantes dentro do vidro não são pintados, parecem ser esculpidos em alto relevo na própria chapa. Use fundo transparente (`!bg-transparent`), traços sutis (`stroke-white/50`), preenchimento quase nulo (`text-white/10`) e um *drop-shadow* Ciano projetado (`drop-shadow-[0_4px_8px_rgba(72,202,228,0.4)]`).
- **Badges:** Não use preenchimentos sólidos agressivos. Aplique banhos translúcidos como `bg-accent/10` para criar rótulos, mantendo a estética cristalina intacta.

## 4. O Mapa como Canvas e Foco Dinâmico (Lente Cinematográfica)
O mapa base Leaflet não é um iframe no meio da página; ele é a própria tela (UI Espacial).
- **Atmosfera Permanente:** O mapa base possui um tratamento fixo (`brightness-[0.90] contrast-[1.1] saturate-[0.6]` + overlay em `bg-primary/20`) que o deixa levemente escuro e denso, servindo de cama escura para o UI de vidro brilhar (gerando contraste natural).
- **Lentes Cinematográficas para Foco (NUNCA Escurecer a Tela):** Quando um painel modal ou gaveta se abrir, **jamais** aplique overlays de fundo escuro (`bg-black/40` ou `drawer-overlay` com fundos). Ao escurecer o fundo, a transparência do vidro rouba a escuridão, "desligando" o brilho natural da UI que já estava iluminada.
- **Foco por Desfoque (`#blur-layer`):** O jeito correto de dar foco ao componente aberto é usar um desfoque cinematográfico dinâmico (Depth of Field). Injete via CSS um `backdrop-blur-sm` no nível exato entre a UI flutuante e o mapa (`z-index` menor que a gaveta). O mapa inteiro embaça em 500ms, isolando o vidro brilhante da gaveta sem roubar sua luz.
- **Coreografia Silenciosa da UI Concorrente:** O foco numa ação deve ser exclusivo. Quando a Gaveta abrir, a Barra de Busca (que não é o foco atual) deve desaparecer graciosamente. Utilize as regras do estado ativador (ex: `#lote-drawer:checked ~ .drawer-content`) para esconder componentes via CSS usando `transform: translateY(-20px) scale(0.95); opacity: 0; pointer-events: none;`, sem depender de JavaScript imperativo.

## 5. Micro-interações e Estados Dinâmicos
- **Feedback Constante:** Todo elemento interativo precisa reagir via `hover:`, `focus:` e `active:`.
- **Transições Suaves:** Mutações no estado da interface devem deslizar fluidamente usando `transition-all duration-300` ou `duration-500`.
- **"Acender" Elementos (Opacidade Dinâmica):** Para transicionar um componente *glass* inativo para o estado "hover/focus", não mude a cor, apenas jogue luz "acendendo" o vidro. Suba o alpha do branco ligeiramente (`hover:!bg-base-100/10`), criando um efeito orgânico.

## 6. Estados de Carregamento e Experiência HTMX
- A aplicação é uma SPA orquestrada estritamente por HTMX; recarregamentos de página (Full Page Reloads) são proibidos após a carga do mapa.
- Operações de CRUD e buscas injetam/substituem pedaços de DOM (Swaps). Use `.htmx-indicator` e as utilitárias `.loading` do daisyUI nos alvos de requisição, pois a UI de vidro não pode ser bloqueante (o usuário precisa saber que os dados da API estão viajando).

## 7. Foco Progressivo e Movimentação Espacial
A direção na qual um componente "nasce" importa e segue uma gramática estrita:
- **Idle:** Barra central flutuando serenamente sobre a tela.
- **Da Esquerda para a Direita (Domínio de Dados/Busca):** Toda gaveta, resultado de lote fiscal, detalhe de logradouro ou inspeção espacial **nasce colada no eixo esquerdo** e expande para a direita do monitor (Glide-in à direita).
- **Da Direita para a Esquerda (Sistema/Gestão):** Gerenciamento de conta, áreas de usuário, painéis de camadas de projetos salvos residem e "abrem" a partir do canto superior direito (Glide-in à esquerda).
- **Integração Visual de Animações:** Use os sufixos temporários do HTMX (como `.htmx-added` e `.htmx-swapping`) para amarrar movimentos elegantes de entrada e saída, impedindo que o DOM seja renderizado secamente. Modais absolutos e alertas críticos explodem a partir do eixo Z (Scale-up no centro da tela).
