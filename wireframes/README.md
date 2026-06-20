# Handoff: DIMAP GeoCoder — Interface de busca, projetos e camadas

## Overview
Geocodificador da Prefeitura de São Paulo (DIMAP/PMSP). Permite buscar **logradouros, endereços e lotes** do cadastro municipal, ver o resultado no mapa (linha, ponto ou polígono) e — autenticado — **salvar resultados em Projetos organizados por Layers**. Inclui busca simples (barra única) e busca detalhada (formulário segmentado), além de um drawer de "ficha do imóvel" previsto para dados futuros.

## About the Design Files
Os arquivos deste pacote são **referências de design feitas em HTML** — um wireframe **low-fidelity (lo-fi sketch)** mostrando estrutura, fluxo e intenção, **não código de produção para copiar**. A tarefa é **recriar estas telas no ambiente do codebase alvo** (ver `CLAUDE.md` — provável stack web com Leaflet para o mapa) usando seus padrões e bibliotecas estabelecidos. Onde o codebase já tiver um design system, **aplique-o**: as cores, fontes "à mão" (Caveat/Kalam) e bordas pretas grossas do wireframe são linguagem de rascunho, **não** o visual final.

## Fidelity
**Low-fidelity (lo-fi).** Use os frames como guia de **layout, hierarquia, campos e fluxo**. Não reproduza cores/tipografia do sketch — aplique o design system do projeto. As medidas abaixo são proporções de intenção, não specs pixel-perfect.

## Conceitos de domínio (ler antes — vêm do CLAUDE.md)
- **Três tipos de entidade**, cada um com uma geometria fixa:
  - **Logradouro** → **linha** (eixo da via). Identificado por **codlog** (match exato) ou por **tipo + nome** do logradouro.
  - **Endereço** → **ponto** (número interpolado sobre o logradouro).
  - **Lote** → **polígono** (geometria do imóvel). Identificado por **número de contribuinte** (setor.quadra.lote-dígito + tipo de quadra + tipo de lote) ou pelo **endereço do lote**.
- **Busca simples**: barra única. O sistema **infere o tipo** por regex/heurística e oferece sugestões a cada tecla, marcadas com tag (END / LOG / LOTE).
- **Busca detalhada**: o usuário **escolhe o tipo explicitamente**; o tipo é dado, não inferido. Os campos do formulário trocam conforme o tipo.
- **Endereço fiscal exato**: quando um endereço bate exato com um lote cadastrado, a UI **pergunta** se o usuário quer o **ponto** (geocodificado a partir do lote) ou o **polígono** do lote. Único momento em que a UI pede decisão.
- **Acesso**: busca é **pública** (sem login). **Salvar** resultado num projeto **exige login**.
- **Projetos → Layers → Itens**: um Projeto contém Layers; cada **Layer é homogêneo** (só ponto, só linha OU só polígono) e tem nome, descrição, cor e estilo. Itens são os resultados salvos.
- **Página de Projetos**: separada do app de busca. O mapa ali é **read-only** (visualização). Para adicionar itens, o usuário volta ao fluxo de busca via "buscar & adicionar".

## Screens / Views

### Seção 1 — Fluxo principal (busca pública)
**01 · Estado inicial** — Header: logo + barra de busca única (placeholder "Rua, endereço, codlog ou nº de contribuinte…") + botão Entrar. Abaixo, mapa full-bleed de SP. Badge "público — busca sem login".

**02 · Digitando → sugestões** — Ao digitar, dropdown de sugestões sob a barra. Cada item tem **tag de tipo** (END/LOG/LOTE) + texto. Sugestões por match exato (keyup); sem clicar, fuzzy match no texto livre. A barra fica em estado focado.

**03 · Resultado linha (logradouro)** — Mapa com o **eixo do logradouro** desenhado (polilinha). Chip superior "LINHA · Logradouro · <nome>". Botão flutuante "＋ Salvar no projeto".

**04 · Resultado ponto (endereço)** — Marcador de **ponto** no mapa. Chip "PONTO · Endereço". Dois botões: "ⓘ Detalhes" (abre drawer) e "＋ Salvar".

**05 · Resultado polígono (lote) + Drawer** — Mapa com **polígono** do lote + drawer lateral (largura ~268–330px) à direita. **Drawer = ficha do imóvel** (estilo painel de negócio do Google Maps):
- Topo: slot de **foto / Street View** (placeholder).
- Título (endereço), subtítulo (bairro/cidade/codlog), linhas de ficha.
- **Bloco reservado "FUTURO · DADOS EXTERNOS"**: espaço já previsto para uso do imóvel, IPTU, área, zoneamento, horários de funcionamento, fotos. **Ainda não construído** — reservar o espaço/estrutura.
- Rodapé: "＋ Salvar no projeto".

### Seção 2 — Estados de decisão & detalhe
**06 · Drawer ampliado (FUTURO)** — Mesmo drawer da 05, em largura maior: foto grande, título, chips (codlog, contribuinte), ficha (tipo do lote, área/frente, coordenadas) e o bloco "FUTURO · DADOS EXTERNOS". Estrutura pronta; só plugar dados.

**07 · Pop-up endereço fiscal exato** — Modal sobre o mapa: "Esse endereço é um imóvel cadastrado." Duas opções lado a lado: **Geocodificar como ponto** (a partir do polígono) ou **Mostrar o polígono do lote**. Decisão do usuário.

**08 · Salvar → exige login** — Modal: "Entre pra salvar num projeto". Campos usuário/senha, botão Entrar, links "criar conta" e "continuar sem salvar". Após login, retorna ao resultado.

### Seção 3 — Projetos (página separada)
**09 · Projeto aberto** — Layout em 3 colunas:
- **Coluna 1 (lista de projetos)** — projetos do usuário; um ativo destacado; "＋ novo projeto".
- **Coluna 2 (painel de layers)** — nome do projeto; lista de layers, cada um com: swatch de cor, nome, tag de tipo (POLY/LINE/PT), contagem de itens, ícone excluir. "＋ novo layer". "⤓ exportar" marcado **Fase 2**.
- **Coluna 3 (mapa read-only)** — renderiza os layers do projeto, cada um na sua cor. Badge "visualização".
- Header: logo / "Meus projetos" / "＋ buscar & adicionar" (volta ao fluxo de busca) / usuário.

**10 · Pop-up criar layer** — Modal com metadados:
- **Nome da camada** (texto)
- **Descrição** (textarea, opcional)
- **Geometria** — segmentado Ponto / Linha / Polígono (**trava o tipo do layer**)
- **Estilo condicional pela geometria**:
  - **Polígono** → **cor de preenchimento** (+ opacidade) e **cor de borda** (+ espessura)
  - **Ponto** → **tipo de símbolo** (○ ◆ ▲ ■ ✚) + cor
  - **Linha** → cor + espessura
- Botões Cancelar / Criar layer.

### Seção 4 — Busca detalhada (formulário segmentado)
Toggle **Simples / Detalhada** no header. Seletor de tipo no topo do form: **Logradouro / Lote / Endereço**. Campos trocam conforme o tipo.

**11 · Tipo = Logradouro → linha**
- **Por nome**: dropdown *Tipo de logradouro* (Rua/Av/…) + input *Nome do logradouro*.
- **— ou — Por codlog**: input *Codlog* (match exato).

**12 · Tipo = Lote → polígono**
- **Por nº de contribuinte**: campos segmentados *Setor . Quadra . Lote - Dígito* + dropdowns *Tipo de quadra* e *Tipo de lote*.
- **— ou — Por endereço do lote**: input de endereço completo.

**13 · Tipo = Endereço → ponto**
- **Logradouro + número**: *Tipo de logradouro* + *Nome do logradouro* + *Número* + *Complemento* (opc.).
- **Codlog (opcional)**: desambigua o logradouro.
- Endereço fiscal exato ainda dispara o pop-up 07 (ponto vs polígono).

## Interactions & Behavior
- **Busca simples**: debounce no input; sugestões a cada keyup; tag indica tipo inferido; Enter ou clique em sugestão dispara o geocode; resultado anima no mapa e centraliza.
- **Drawer**: abre por "Detalhes" (ponto) ou automaticamente ao resolver um lote; fecha no ✕; não cobre o mapa inteiro (mapa permanece à esquerda).
- **Pop-up fiscal exato**: bloqueante; só aparece quando endereço == lote cadastrado.
- **Salvar**: se não autenticado → modal de login; após login, volta ao mesmo resultado e abre seletor de projeto/layer.
- **Criar layer**: a escolha de geometria revela o bloco de estilo correspondente (campos de polígono/ponto/linha são mutuamente exclusivos).
- **Projetos**: mapa read-only; CRUD de layers no painel; toggle de visibilidade por layer (recomendado).
- **Busca detalhada**: trocar o tipo (Logradouro/Lote/Endereço) recompõe o formulário; submit valida campos obrigatórios do tipo ativo.

## State Management
- `searchMode`: 'simples' | 'detalhada'
- `query`, `suggestions[]`, `inferredType` (busca simples)
- `detailedType`: 'logradouro' | 'lote' | 'endereco' + sub-modo por tipo (porNome/porCodlog, porContribuinte/porEndereco)
- `result`: { tipo: 'linha'|'ponto'|'poligono', geometry, attributes }
- `drawerOpen`, `fiscalChoice` ('ponto'|'poligono')
- `auth`: { user, isLoggedIn }
- `projects[]`, `activeProjectId`, `layers[]` (cada layer: { id, nome, descricao, geometria, cor, estilo, itens[] })
- Data fetching: serviço de geocode da PMSP (ver CLAUDE.md); sugestões/autocomplete; CRUD de projetos/layers/itens (autenticado).

## Design Tokens
**Não usar os tokens do wireframe** (são linguagem de sketch). Tokens semânticos a mapear no design system do projeto:
- **Cores por geometria** (placeholder do wireframe): linha/ponto = azul `#2f6fae`; polígono = preenchimento azul translúcido + borda azul; layers diversos = azul/verde `#3f8f5b`/laranja `#c98a1e`/vermelho `#c0392b`.
- **Tags de tipo**: END (azul), LOG (verde), LOTE (laranja).
- **Marcador FUTURO**: usado só no wireframe para sinalizar o que não existe ainda — **não** levar pro produto.
- Espaçamento, raio, sombra, tipografia: **usar a escala do codebase**.

## Assets
- **Mapa**: Leaflet (conforme CLAUDE.md). Tiles conforme o provedor já usado no projeto.
- **Foto/Street View** no drawer: placeholder — fonte de imagem a definir (funcionalidade futura).
- Ícones: usar a biblioteca de ícones do codebase. Não há assets de marca proprietários neste pacote.

## Files
- `DIMAP-GeoCoder-Wireframe.html` — wireframe completo, autossuficiente (todas as 13 telas + pop-ups). **Abra no navegador como referência visual principal.**
- `CLAUDE.md` — contexto de domínio e arquitetura original do projeto (fonte da verdade para regras e stack).
