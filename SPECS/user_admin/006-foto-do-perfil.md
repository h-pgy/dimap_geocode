---
spec: user_admin/006
versao: v1
atualizado_em: 2026-08-05
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial — desmembrada da SPEC user_admin/005, que ficou só com a cor da unidade
---

# SPEC user_admin/006 — Foto do perfil

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como servidor da DIMAP, quero subir uma foto para o meu perfil e me identificar no sistema — e,
quando não tiver uma foto à mão, quero que o sistema me identifique por uma imagem com as minhas
iniciais.

## Critérios de aceite

- [ ] O perfil tem uma **foto opcional**: salvar perfil sem foto é aceito, e o campo aceita imagem
      enviada por upload.
- [ ] O perfil tem **nome e sobrenome** em campos separados, ambos obrigatórios, e o perfil já
      cadastrado sobrevive à migração com o nome repartido.

## Contexto e decisões de arquitetura

Iteração de **persistência**, sobre o model `Perfil` da SPEC `user_admin/001`: dois campos novos e
a troca de semântica do `nome`. Nenhum model novo.

O gerador de SVG que consome as iniciais é a SPEC `user_admin/004`, e as duas **não se cruzam em
código** — ele recebe nome e sobrenome por DTO. O encontro acontece na view, que é a SPEC de
front-end do épico; é lá também que se decide entre exibir a foto e gerar o avatar.

**Nome e sobrenome separados porque a inicial exige a separação.** Extrair sobrenome de um campo
único por heurística de espaços funcionaria hoje e quebraria no primeiro nome composto; o modelo
passa a guardar a informação que a regra consome.

**Consequência operacional:** `sobrenome` é obrigatório e a tabela de perfis já tem carga, então a
migração precisa de um passo de dados que quebre o `nome` atual no primeiro espaço (primeiro termo →
`nome`, resto → `sobrenome`) — mesmo padrão da migração custom da SPEC `003`. Como `nome` também
encolhe de 200 para 100 caracteres, a ordem das operações importa: acrescentar `sobrenome`,
repartir os dados e só então alterar a coluna. A assinatura de `create_user`/`REQUIRED_FIELDS`
acompanha, e os testes que hoje criam perfil avulso também.

**Duas dependências de infraestrutura entram junto:** `Pillow` (exigido pelo `ImageField`, que é o
que valida que o arquivo enviado é imagem de verdade — `FileField` aceitaria qualquer coisa) e
`MEDIA_ROOT`/`MEDIA_URL` nas settings. Servir o arquivo por rota é front-end e fica de fora.

## Peças de referência a compor

- `@SPECS/user_admin/001` → `Perfil` e `PerfilManager`: os campos novos entram no model existente, e
  `create_user`/`REQUIRED_FIELDS` acompanham a mudança de assinatura.
- `@SPECS/user_admin/003` → o marker `banco` e o padrão de migração custom para tabela com carga
  pré-existente.
- `@SPECS/user_admin/004` → `AvatarIniciaisInput`: é o DTO que recebe o nome e o sobrenome gravados
  aqui.

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
```

## Fora de escopo

- A cor da unidade que pinta o avatar — SPEC `user_admin/005`.
- O gerador de SVG e a extração das iniciais — SPEC `user_admin/004`.
- Escolher entre foto e avatar na resposta, e a rota que serve o arquivo de mídia.
- Redimensionar, recortar ou limitar o tamanho da foto enviada.

## Testes (TDD)

Ambos levam o marker `banco`: validam obrigatoriedade, campo nulo e a nova assinatura do manager
contra o Postgres real.

- `test_perfil_exige_sobrenome_e_admite_foto_nula` — perfil sem foto é salvo, e perfil com sobrenome
  vazio é recusado no `full_clean`.
- `test_create_user_guarda_nome_e_sobrenome_separados` — o manager passa a exigir os dois campos e
  grava cada um no seu, fixando a nova assinatura.

## Patches

_Nenhum patch registrado até o momento._
