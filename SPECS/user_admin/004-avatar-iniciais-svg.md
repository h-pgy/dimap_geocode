---
spec: user_admin/004
versao: v5
atualizado_em: 2026-08-05
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
  - v2: a unidade passa a expor `cor_sugerida` (a cor do pai, ou o padrão global na raiz) como
    valor inicial do cadastro
  - v3: escopo reduzido ao gerador de SVG; os campos de model, a paleta e a migração saem para a
    SPEC user_admin/005
  - v4: termos de uma letra passam a ser descartados como resíduo de partícula elidida
    (`d'Angelo` → `A`), garantindo duas iniciais maiúsculas sempre que nome e sobrenome têm
    termo aproveitável
  - v5: `services/domain/__init__.py` não precisa reexportar o gerador — o reexport de
    `aquecer_catalogos` é conveniência pontual, não convenção do pacote
---

# SPEC user_admin/004 — Avatar de iniciais em SVG

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como servidor da DIMAP, quero que o sistema saiba desenhar um avatar circular com as minhas
iniciais numa cor dada, para que eu seja identificável na plataforma mesmo sem ter enviado foto
alguma.

## Critérios de aceite

- [ ] A partir de nome, sobrenome e duas cores, o domínio devolve um **SVG** e as **iniciais**
      usadas.
- [ ] As iniciais são a **primeira letra do primeiro nome** + a **primeira letra do último
      sobrenome** — **duas letras, sempre em caixa alta e sem acento**.
- [ ] **Partículas elididas não viram inicial:** `d'Angelo` produz `A`, não `D`; o mesmo vale no
      primeiro nome (`D'Artagnan` → `A`).
- [ ] Termos sem letra (partículas com pontuação, dígitos, símbolos) são **descartados**: nenhum
      caractere fora do alfabeto chega ao markup.
- [ ] O SVG é **redondo por construção** — círculo preenchendo um `viewBox` quadrado —, não depende
      de recorte do CSS para ser circular.
- [ ] As cores do círculo e da letra são as **recebidas na entrada**; o domínio não conhece paleta.

## Contexto e decisões de arquitetura

Iteração de **domínio puro**: entra um submódulo em `services/domain/`, sem Django, sem model e sem
rota. Os campos que alimentam o gerador (`sobrenome` no perfil, `cor` na unidade) são a SPEC
`user_admin/005`, e as duas não se cruzam em código — o acoplamento só aparece na view que as
consome, e essa view é a SPEC de front-end do épico.

`services/domain/__init__.py` não precisa reexportar o gerador. O reexport de `aquecer_catalogos`
que já está lá é conveniência pontual daquele caso, não convenção do pacote — quem for usar o
gerador importa direto de `services.domain.avatar_iniciais`.

**O gerador é domínio, não template.** Iniciais e SVG viveriam confortavelmente num partial, mas a
certidão de lançamento (ação futura, §3.5 do CLAUDE.md) vai precisar do mesmo avatar fora do
pipeline HTML. Em `services/domain/` ele serve os dois; num template, serviria só a web.

**O avatar é gerado a cada leitura, nunca persistido.** Medido em **5,59 µs** por avatar (311 bytes
de markup), contra ~300 µs de uma única query no Postgres local: não há processamento a economizar.
O que pesaria é a invalidação, e ela é cruzada — a cor vem da unidade, então o cache venceria também
quando o servidor é remanejado, quando a unidade troca de cor (todos os perfis dela de uma vez) e
quando o gabarito muda, este último exigindo migração de dados para re-renderizar a tabela.
Recomputar em `save()` ou signal é vedado pelo §3.2 do CLAUDE.md; fora deles, todo caminho de
escrita — inclusive o da unidade — teria que lembrar de recomputar.

**As cores entram pelo DTO, resolvidas pela orquestração.** É o mesmo padrão do CRS (§7.2 do
CLAUDE.md): valor de design vem de fora, nunca hardcoded no domínio. Assim o gerador não importa a
paleta da SPEC `005` nem sabe que ela existe, e a certidão em PDF pode pintar o avatar com outra
tinta se precisar.

**As iniciais passam pela normalização única do projeto** (§6.1): o SVG é markup, e restringir a
saída a letras é o que garante que nome algum injete marcação — não um escape ad hoc.

**O último sobrenome é o último termo alfabético do campo**, o que descarta partículas (`da`, `de`,
`dos`) sem lista de exceções.

**Termo de uma letra é descartado como resíduo, não tratado como nome.** A normalização do projeto
troca pontuação por espaço, então `d'Angelo` chega ao gerador como `D ANGELO`: pegar o último termo
já resolve o sobrenome, mas no primeiro nome (`D'Artagnan`) o `D` seria o *primeiro* termo e viraria
a inicial. Descartar todo termo de letra única resolve os dois lados com uma regra só, e não há
nome de servidor de uma letra para proteger.

**Duas iniciais é garantia do caso normal, não invariante do gerador.** Nome e sobrenome são
obrigatórios (SPEC `005`), então na prática sempre há termo aproveitável dos dois lados; se um deles
degenerar (só dígitos, só partícula), o avatar sai com uma inicial só em vez de inventar a segunda.

**O texto é posicionado com `dy`, não com `dominant-baseline`.** As duas centralizam no browser, mas
rasterizadores de PDF ignoram a segunda — e o PDF já está no horizonte do épico.

## Peças de referência a compor

- `@services/utils/normalization` → `normalize_text`: a normalização única do projeto, usada para
  tirar acento das iniciais.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

class AvatarIniciaisInput(BaseModel):
    nome: str
    sobrenome: str
    cor_fundo: str
    cor_tinta: str


class AvatarIniciaisOutput(BaseModel):
    iniciais: str
    svg: str


# dy="0.35em" em vez de dominant-baseline: rasterizadores de PDF ignoram a segunda.
GABARITO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"'
    ' role="img" aria-label="{iniciais}">'
    '<circle cx="50" cy="50" r="50" fill="{cor_fundo}"/>'
    '<text x="50" y="50" dy="0.35em" text-anchor="middle"'
    ' font-family="Roboto, ui-sans-serif, system-ui, sans-serif"'
    ' font-size="42" font-weight="700" fill="{cor_tinta}">{iniciais}</text>'
    "</svg>"
)


class AvatarIniciaisSvg:
    def __call__(self, entrada: AvatarIniciaisInput) -> AvatarIniciaisOutput:
        return self.pipeline(entrada)

    def pipeline(self, entrada: AvatarIniciaisInput) -> AvatarIniciaisOutput:
        iniciais = self._extrair_iniciais(entrada.nome, entrada.sobrenome)
        svg = GABARITO_SVG.format(
            iniciais=iniciais,
            cor_fundo=entrada.cor_fundo,
            cor_tinta=entrada.cor_tinta,
        )
        return AvatarIniciaisOutput(
            iniciais=iniciais,
            svg=svg,
        )

    def _extrair_iniciais(self, nome: str, sobrenome: str) -> str:
        primeiro = self._primeira_letra(self._termos(nome)[:1])
        ultimo = self._primeira_letra(self._termos(sobrenome)[-1:])
        return f"{primeiro}{ultimo}"

    def _termos(self, texto: str) -> list[str]:
        # Só termos alfabéticos: fecha a porta de injeção de markup no gabarito.
        # Termo de uma letra é resíduo de partícula elidida ("d'Angelo" -> "D ANGELO"), não nome.
        return [
            termo
            for termo in normalize_text(texto).split()
            if termo.isalpha() and len(termo) > 1
        ]

    def _primeira_letra(self, termos: list[str]) -> str:
        return termos[0][0].upper() if termos else ""
```

## Fora de escopo

- Todo model: `sobrenome` e `foto` no perfil, `cor` na unidade, a paleta de tokens e a migração —
  são a SPEC `user_admin/005`.
- Escolher entre foto e avatar na resposta, rota que serve a imagem, e qualquer template ou átomo
  de UI do avatar — é a SPEC de front-end do épico.
- Registrar o token novo `.avatar-*` no styleguide do design system.
- Avatar de qualquer entidade que não seja perfil de servidor.

## Testes (TDD)

Domínio puro, sem Django e sem banco: todos rodam na suíte padrão.

- `test_iniciais_vem_do_primeiro_nome_e_do_ultimo_sobrenome` — "João" + "Pedro da Silva" produz
  `JS`, não `JP` nem `Jd`.
- `test_iniciais_sao_maiusculas_e_sem_acento` — "ávila" + "éboli" produz `AE`, duas letras.
- `test_particula_elidida_nao_vira_inicial` — "João" + "d'Angelo" produz `JA`, e "D'Artagnan" +
  "Silva" produz `AS`: o resíduo de uma letra é descartado dos dois lados.
- `test_avatar_e_um_circulo_pintado_com_as_cores_recebidas` — o SVG traz um `circle` de raio igual à
  metade do `viewBox` com o `fill` da cor de fundo recebida, e a letra com a cor de tinta recebida.
- `test_iniciais_descartam_termos_nao_alfabeticos` — nome com pontuação ou dígito não vaza caractere
  algum para o markup; sobrenome sem termo alfabético produz avatar de uma inicial só.

## Patches

_Nenhum patch registrado até o momento._
