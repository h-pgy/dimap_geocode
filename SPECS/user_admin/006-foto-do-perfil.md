---
spec: user_admin/006
versao: v4
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial — desmembrada da SPEC user_admin/005, que ficou só com a cor da unidade
  - v2: acrescenta `cor_unidade`, campo calculado do Perfil que expõe a cor da unidade vinculada
  - v3: acrescenta `resolver_imagem_perfil`, função de domínio que decide entre foto e avatar
    gerado, reusável em qualquer call-site sem repetir a lógica nem tocar o model; o módulo
    `services/domain/avatar_iniciais` (SPEC 004) é renomeado para `services/domain/avatar` para
    acomodá-la
  - v4: registra que a resiliência a foto ausente do storage (arquivo apagado, registro órfão) é
    responsabilidade de quem monta `foto_url` — não do resolver, que ficaria acoplado a Django
---

# SPEC user_admin/006 — Foto do perfil

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como servidor da DIMAP, quero subir uma foto para o meu perfil e me identificar no sistema — e,
quando não tiver uma foto à mão, quero que o sistema me identifique por uma imagem com as minhas
iniciais.

## Critérios de aceite

- [x] O perfil tem uma **foto opcional**: salvar perfil sem foto é aceito, e o campo aceita imagem
      enviada por upload.
- [x] O perfil tem **nome e sobrenome** em campos separados, ambos obrigatórios, e o perfil já
      cadastrado sobrevive à migração com o nome repartido.
- [x] O perfil expõe um campo calculado **`cor_unidade`**, que devolve a cor cadastrada na unidade a
      que o perfil está vinculado.
- [x] Existe uma função de **domínio**, sem qualquer dependência de Django ou do model, que decide
      entre foto e avatar: dados nome, sobrenome, as cores já resolvidas e a URL da foto (quando
      houver), devolve qual das duas usar — reusável em qualquer ponto do sistema que precise
      exibir a imagem do perfil.

## Contexto e decisões de arquitetura

Iteração de **persistência**, sobre o model `Perfil` da SPEC `user_admin/001`: dois campos novos, a
troca de semântica do `nome` e uma property que atravessa a FK de `Unidade`. Nenhum model novo.

O gerador de SVG que consome as iniciais é a SPEC `user_admin/004`, e as duas **não se cruzam em
código** — ele recebe nome e sobrenome por DTO. A escolha entre foto e avatar ganha aqui uma função
de domínio própria (ver adiante); o encontro com o `Perfil` continua acontecendo na view, que é a
SPEC de front-end do épico.

**Nome e sobrenome separados porque a inicial exige a separação.** Extrair sobrenome de um campo
único por heurística de espaços funcionaria hoje e quebraria no primeiro nome composto; o modelo
passa a guardar a informação que a regra consome.

**Consequência operacional:** `sobrenome` é obrigatório e a tabela de perfis já tem carga, então a
migração precisa de um passo de dados que quebre o `nome` atual no primeiro espaço (primeiro termo →
`nome`, resto → `sobrenome`) — mesmo padrão da migração custom da SPEC `003`. Como `nome` também
encolhe de 200 para 100 caracteres, a ordem das operações importa: acrescentar `sobrenome`,
repartir os dados e só então alterar a coluna. A assinatura de `create_user`/`REQUIRED_FIELDS`
acompanha, e os testes que hoje criam perfil avulso também.

**`cor_unidade` é `@property`, não coluna.** A cor mora na `Unidade` (SPEC `005`); o perfil só a
atravessa via `self.unidade.cor`, na mesma linha de `cor_sugerida` e de `natureza`/`padrao` da SPEC
`001` — formatação/leitura de campo já persistido, não regra de negócio, e por isso cabe no model
(§3.2). Guardar a cor de novo no perfil duplicaria o dado e desatualizaria no dia em que a unidade
trocasse de cor. É o campo que a view de identificação visual usa para montar o `AvatarIniciaisInput`
junto com nome e sobrenome.

**Duas dependências de infraestrutura entram junto:** `Pillow` (exigido pelo `ImageField`, que é o
que valida que o arquivo enviado é imagem de verdade — `FileField` aceitaria qualquer coisa) e
`MEDIA_ROOT`/`MEDIA_URL` nas settings. Servir o arquivo por rota é front-end e fica de fora.

**A escolha entre foto e avatar é domínio puro, não perfil e não view.** A imagem do perfil vai
aparecer em muitos pontos do sistema (telas da gaveta, futura certidão em PDF); resolver a escolha
uma vez só, num lugar reusável, é o que evita reimplementar o `if` em cada call-site — sem que esse
lugar seja o `Perfil`. Colocar a decisão no model inverteria a cadeia do §3.3 (`views → services/ →
models`): o model passaria a importar domínio, e o domínio conheceria Django.

**O resolver entra no mesmo módulo do gerador, que por isso é renomeado.** `services/domain/
avatar_iniciais` (SPEC `004`) vira `services/domain/avatar`: ele deixa de ser só "gerador de
iniciais" e passa a ser o domínio de imagem de avatar como um todo — gerar o SVG e decidir se ele é
usado. É *patch* da SPEC `004` (refactor sobre spec já implementada), não mudança de comportamento
do gerador. A função nova, `resolver_imagem_perfil`, recebe os parâmetros direto (nome, sobrenome,
cores, `foto_url: str | None`) em vez de um DTO de input — só o output é DTO (`ImagemPerfilOutput`),
porque quem chama não ganha nada instanciando um input só para os mesmos cinco valores que já tinha
soltos; e ela **compõe** (não herda, §7.1) o `AvatarIniciaisSvg` só quando não há foto. Cores entram
já resolvidas em hex, mesmo padrão da SPEC `004` — a paleta é responsabilidade da borda do app. Quem
monta os argumentos a partir do `Perfil` (lendo `foto.url` quando houver, `cor_unidade` e
`nome`/`sobrenome`) e chama a função é a view, na SPEC de front-end do épico — o mesmo ponto de
encontro que 004 e 005 já previam, só que agora com a decisão já pronta para reusar.

## Peças de referência a compor

- `@SPECS/user_admin/001` → `Perfil` e `PerfilManager`: os campos novos entram no model existente, e
  `create_user`/`REQUIRED_FIELDS` acompanham a mudança de assinatura.
- `@SPECS/user_admin/003` → o marker `banco` e o padrão de migração custom para tabela com carga
  pré-existente.
- `@SPECS/user_admin/004` → `AvatarIniciaisSvg`/`AvatarIniciaisInput`, hoje em
  `services/domain/avatar_iniciais`: recebe um patch de rename para `services/domain/avatar` e passa
  a ser composto pelo novo `resolver_imagem_perfil` quando não há foto.
- `@SPECS/user_admin/005` → `Unidade.cor`: campo do qual `cor_unidade` é derivado por travessia de
  FK, e de onde sai a cor que a view resolve em hex antes de montar o DTO do resolver.

## Snippets sugeridos

```python
# direção de implementação — adaptar conforme necessário, sem violar os princípios de
# arquitetura nem o estilo de código do CLAUDE.md

# ── campos NOVOS no Perfil que já existe (SPEC 001) ───────────────────────────────────

# `nome` troca de semântica (nome completo -> primeiro nome) e por isso encolhe o max_length.
nome = models.CharField(max_length=100)
sobrenome = models.CharField(max_length=150)
foto = models.ImageField(
    upload_to="perfis/fotos/",
    null=True,
    blank=True,
)

REQUIRED_FIELDS = ["nome", "sobrenome"]


# Deriva da Unidade (SPEC 005); não duplica a cor no perfil.
@property
def cor_unidade(self) -> str:
    return self.unidade.cor
```

```python
# ── services/domain/avatar (renomeado de avatar_iniciais — patch na SPEC 004) ────────
# resolver.py — compõe o AvatarIniciaisSvg já existente em generator.py

class ImagemPerfilOutput(BaseModel):  # em models.py, junto de AvatarIniciaisInput/Output
    tipo: Literal["foto", "avatar"]
    valor: str  # a URL da foto, ou o markup do SVG


def resolver_imagem_perfil(
    nome: str,
    sobrenome: str,
    cor_fundo: str,
    cor_tinta: str,
    foto_url: str | None = None,
) -> ImagemPerfilOutput:
    if foto_url:
        return ImagemPerfilOutput(tipo="foto", valor=foto_url)
    avatar = AvatarIniciaisSvg()(
        AvatarIniciaisInput(
            nome=nome,
            sobrenome=sobrenome,
            cor_fundo=cor_fundo,
            cor_tinta=cor_tinta,
        )
    )
    return ImagemPerfilOutput(tipo="avatar", valor=avatar.svg)
```

## Fora de escopo

- O campo `Unidade.cor` em si e a cor sugerida no cadastro da unidade — SPEC `user_admin/005`;
  `cor_unidade` só o lê por travessia.
- O gerador de SVG e a extração das iniciais em si — SPEC `user_admin/004`; esta SPEC só compõe.
- A resolução do token de cor para hex, a view que chama `resolver_imagem_perfil` com os dados do
  `Perfil` (lendo `foto.url`, `nome`, `sobrenome`, `cor_unidade`), o template que consome
  `ImagemPerfilOutput` e a rota que serve o arquivo de mídia — front-end do épico. **Inclui a
  resiliência a foto ausente do storage:** é essa view que deve checar
  `perfil.foto.storage.exists(perfil.foto.name)` antes de passar `foto_url` — se o arquivo sumiu,
  passa `None` e o resolver cai no avatar. O resolver não faz essa checagem: exigiria Django/I·O de
  disco dentro do domínio puro.
- Redimensionar, recortar ou limitar o tamanho da foto enviada.

## Testes (TDD)

Os três primeiros levam o marker `banco`: validam obrigatoriedade, campo nulo, a nova assinatura do
manager e a travessia de FK contra o Postgres real. Os dois últimos são domínio puro — sem Django e
sem banco — e rodam na suíte padrão.

- `test_perfil_exige_sobrenome_e_admite_foto_nula` — perfil sem foto é salvo, e perfil com sobrenome
  vazio é recusado no `full_clean`.
- `test_create_user_guarda_nome_e_sobrenome_separados` — o manager passa a exigir os dois campos e
  grava cada um no seu, fixando a nova assinatura.
- `test_cor_unidade_reflete_a_cor_da_unidade_vinculada` — `perfil.cor_unidade` devolve o mesmo token
  gravado em `perfil.unidade.cor`.
- `test_resolver_devolve_a_foto_quando_ha_foto_url` — com `foto_url` preenchida,
  `resolver_imagem_perfil` devolve `tipo="foto"` e o próprio valor recebido.
- `test_resolver_gera_avatar_quando_nao_ha_foto` — com `foto_url=None`, devolve `tipo="avatar"` e o
  SVG produzido pelo `AvatarIniciaisSvg` a partir de nome/sobrenome/cores.

## Patches

_Nenhum patch registrado até o momento._
