---
spec: user_admin/005
versao: v2
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial — desmembrada da SPEC user_admin/004, que ficou só com o gerador de SVG
  - v2: escopo reduzido à cor da unidade; a foto do perfil e a separação nome/sobrenome saem
    para a SPEC user_admin/006
---

# SPEC user_admin/005 — Cor da unidade

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da DIMAP, quero dar uma cor a cada unidade, para que a identificação visual de
cada servidor no sistema também diga de qual unidade ele vem.

## Critérios de aceite

- [x] A unidade tem uma **cor**, escolhida entre os tons de tinta do design system, com um valor
      **padrão**; cor fora da paleta é recusada. Cores podem se repetir entre unidades.
- [x] A unidade expõe a **cor sugerida** para o cadastro: a cor da unidade-pai, ou o padrão global
      quando ela é raiz.

## Contexto e decisões de arquitetura

Iteração de **persistência**, sobre o model `Unidade` das SPECs `user_admin/001` e `003`: um campo
novo e a propriedade que sugere a cor no cadastro. Nenhum model novo.

O gerador de SVG que pinta o avatar com essa cor é a SPEC `user_admin/004`, e as duas **não se
cruzam em código** — ele recebe as cores já resolvidas por DTO. O encontro acontece na view, que é a
SPEC de front-end do épico.

**A cor é um `choices` de tokens, não hex livre.** A skill `componentes-frontend` veda hex solto:
cor nova entra numa escala existente ou não entra. O banco guarda o **slug do token** (`agua-700`),
não o valor — assim, se o design system reajustar a escala, todas as unidades acompanham sem
migração de dados. A resolução slug → hex acontece na borda do app, e o domínio recebe o hex já
resolvido pelo DTO.

**A tinta é sempre `base-100`, e isso é o que define a paleta.** Uma tinta única mantém o gerador
sem tabela de pareamento, mas cobra o piso de contraste: medido contra `#F2F8FB`, só passam de 4,5:1
os tons a partir de `agua-700`, `rocha-600`, `madeira-600` e `sakura-600` — os tons claros das
quatro escalas são luz e a letra some neles. Os oito tokens oferecidos saem dessa faixa. Custo
aceito: a paleta oferece oito cores, não a escala inteira.

**A cor não é única por unidade.** Unicidade global amarraria o número de unidades ao tamanho da
paleta e obrigaria a derrubar o `default` (a segunda unidade salva sem cor quebraria). A cor é pista
de identidade visual, não chave — duas unidades repetirem cor não quebra nada.

**A cor do pai é sugestão, não herança.** A unidade grava a cor que escolheu, e ponto; o que o model
oferece é `cor_sugerida`, que devolve a cor do pai (ou o default global, na raiz) para o formulário
de cadastro usar como valor inicial. Herança de verdade — campo anulável resolvido na leitura —
custaria travessia da cadeia e propagação em ramo para uma pista visual, e nada no sistema depende
de a cor ser coerente com o organograma. Custo aceito: trocar a cor de uma unidade não repinta as
filhas já cadastradas.

## Peças de referência a compor

- `@SPECS/user_admin/001` → `Unidade`: o campo novo entra no model existente, não em model novo.
- `@SPECS/user_admin/003` → `Unidade.pai`, de onde sai a cor sugerida; e o marker `banco`.
- `@SPECS/user_admin/004` → `AvatarIniciaisInput`: é o DTO que recebe o hex resolvido a partir do
  token gravado aqui.
- `@.claude/skills/componentes-frontend` → `references/paleta.json`: fonte da verdade dos valores das
  escalas `agua`/`rocha`/`madeira`/`sakura` e do papel `base-100`.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# ── a borda do app que conhece o design system ────────────────────────────────────────

# base-100: a tinta clara do tema, legível sobre os oito tons oferecidos abaixo.
TINTA_AVATAR = "#F2F8FB"


class CorUnidade(models.TextChoices):
    AGUA_700 = "agua-700", "Água 700"
    AGUA_800 = "agua-800", "Água 800"
    ROCHA_700 = "rocha-700", "Rocha 700"
    ROCHA_900 = "rocha-900", "Rocha 900"
    MADEIRA_600 = "madeira-600", "Madeira 600"
    MADEIRA_700 = "madeira-700", "Madeira 700"
    SAKURA_600 = "sakura-600", "Sakura 600"
    SAKURA_700 = "sakura-700", "Sakura 700"


HEX_POR_COR: dict[str, str] = {
    CorUnidade.AGUA_700: "#0077B6",
    CorUnidade.AGUA_800: "#023E8A",
    CorUnidade.ROCHA_700: "#415A77",
    CorUnidade.ROCHA_900: "#1B263B",
    CorUnidade.MADEIRA_600: "#7F5539",
    CorUnidade.MADEIRA_700: "#5E412F",
    CorUnidade.SAKURA_600: "#BC3A67",
    CorUnidade.SAKURA_700: "#97294F",
}


# ── campo NOVO na Unidade que já existe (SPEC 001/003) ────────────────────────────────

# Repetir cor entre unidades é aceito: a cor é pista de identidade, não chave.
cor = models.CharField(
    max_length=20,
    choices=CorUnidade,
    default=CorUnidade.AGUA_700,
)


# Valor inicial oferecido ao formulário de cadastro; a unidade grava a cor que escolher.
@property
def cor_sugerida(self) -> str:
    return self.pai.cor if self.pai else CorUnidade.AGUA_700
```

## Fora de escopo

- A foto do perfil e a separação nome/sobrenome — SPEC `user_admin/006`.
- O gerador de SVG e a extração das iniciais — SPEC `user_admin/004`.
- O formulário de cadastro de unidade que consome `cor_sugerida` como valor inicial.
- Cor por perfil, por cargo ou derivada de hash do nome — a cor é da unidade.
- Propagar cor para as unidades filhas já cadastradas.
- Seed das cores das unidades da DIMAP — vai junto com o seed do épico.

## Testes (TDD)

Ambos levam o marker `banco`: validam `choices`, default e travessia de FK contra o Postgres real.

- `test_unidade_recusa_cor_fora_da_paleta_e_nasce_com_a_padrao` — unidade salva sem cor fica com o
  token padrão, e um valor fora do `choices` é recusado no `full_clean`.
- `test_cor_sugerida_vem_do_pai_e_cai_no_padrao_na_raiz` — a filha sugere a cor do pai mesmo quando
  a sua própria já é outra; a unidade raiz sugere o token padrão.

## Patches

_Nenhum patch registrado até o momento._
