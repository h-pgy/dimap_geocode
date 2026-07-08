# Skills sugeridas — DIMAP GeoCoder

Rascunhos de skills que estão **faltando** em `.claude/skills/`, identificados na revisão do
CLAUDE.md (ver `../01-diagnostico.md` §4).

**Importante: são rascunhos-esqueleto.** Nesta revisão eu deliberadamente não li o código fonte
módulo a módulo — assinaturas, nomes exatos de classes/funções e caminhos marcados com `TODO`
precisam ser **confirmados contra o código** antes de promover qualquer rascunho para
`.claude/skills/`. O valor aqui é o recorte (o que merece ser skill e por quê) e a estrutura.

## Prioridade

| # | Skill | Por quê agora |
|---|---|---|
| 1 | `wms-fetcher` | Integração existe (`services/integrations/wms`), já causou bug real em produção de dev (commit sobre a ortofoto barrando) e não tem documentação de uso. O irmão WFS tem skill. |
| 2 | `catalogos-lookup` | Todo fluxo de busca consome os catálogos cacheados; a interface de lookup é o ponto de troca futura para Redis — acoplar fora dela é o erro estrutural mais provável de um agente novo. |
| 3 | `fluxo-busca` | O padrão "filtro regex → roteador → seção de sugestão → partial" foi iterado em 14 SPECs; cada extensão nova re-deriva o padrão lendo SPECs antigas. |
| 4 | `management-commands` | Absorve o §8 do CLAUDE.md atual (regra + exemplo + ordem do pipeline), enxugando o arquivo de contexto. |
| 5 | `leaflet-eventos` | Prometida pela própria skill `leaflet-map`. Só se materializa quando o épico de digitalização/eventos do mapa (Fase 2) começar — por ora, placeholder de escopo. |

## Critério usado (quando algo merece ser skill)

- **Recorrência:** o tema volta em várias iterações (não é conhecimento de uma SPEC só).
- **Risco de reimplementação:** existe uma peça pronta que um agente tenderia a recriar
  (normalização, fuzzy, middleware) — a skill existe para dizer "não reimplemente, use assim".
- **Custo de contexto:** o *como* é longo demais para viver no CLAUDE.md, que é carregado em
  toda sessão.

Contra-exemplos deliberados (não propostos como skill): regras de arquitetura (§3 do CLAUDE.md
— precisam estar sempre em contexto, não sob demanda) e conteúdo de uma SPEC única (a SPEC já é
o registro).
