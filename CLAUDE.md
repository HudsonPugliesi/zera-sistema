# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado atual do repositório

"Projeto omega" ainda não contém código de aplicação, build, lint ou testes, e não é um repositório git. Hoje ele só tem uma equipe de subagentes do Claude Code em `.claude/agents/` e um conjunto de skills em `.claude/skills/`. Quando o código da aplicação for adicionado, atualize este arquivo com a stack, os comandos (build, lint, teste, teste único) e a arquitetura.

## Equipe de subagentes (`.claude/agents/`)

Cada arquivo `.md` define um subagente (frontmatter `name`, `description`, `tools`, `model`; o corpo é o prompt de sistema, em português). Os prompts e descrições estão em português, então mantenha o idioma ao editá-los.

| Agente | Papel | Tools | Modelo |
|---|---|---|---|
| `tech-lead` | Orquestrador: planeja, delega e integra | `Agent, Read, Glob, Grep, Bash` (sem Write/Edit) | opus |
| `frontend-senior` | UI, acessibilidade, performance web | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `backend-senior` | APIs, regras de negócio, auth, integrações | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `database-senior` | Esquema, migrações, queries, índices | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `test-senior` | Estratégia e execução de testes | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `security-senior` | Revisão de segurança defensiva (AppSec) | Read, Glob, Grep, Bash (somente leitura) | sonnet |
| `devops-senior` | CI/CD, Docker, IaC, deploy, observabilidade | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `code-reviewer` | Revisão de código (somente leitura) | Read, Glob, Grep, Bash (somente leitura) | sonnet |
| `debugger` | Diagnóstico de bugs, causa raiz, teste de regressão | Read, Write, Edit, Glob, Grep, Bash | sonnet |
| `architect` | Decisões de design, trade-offs, ADRs (somente leitura) | Read, Glob, Grep, Bash (somente leitura) | opus |
| `docs-writer` | README, guias, changelog, docs de API | Read, Write, Edit, Glob, Grep (sem Bash) | sonnet |
| `performance-senior` | Profiling, benchmarks, otimização medida | Read, Write, Edit, Glob, Grep, Bash | sonnet |

### Como o fluxo de trabalho foi desenhado

- O `tech-lead` é o único que pode acionar os outros (é o único com a tool `Agent`) e não edita arquivos. Ele delega toda a implementação aos especialistas.
- Ordem de dependência prevista: banco → backend → frontend → testes → segurança. O trabalho independente é paralelizado.
- Mudanças que tocam auth, dados ou entrada de usuário devem terminar com `test-senior` (rodar testes) e `security-senior` (revisão).
- Ao delegar, o contexto passado a cada especialista precisa ser completo e autocontido (objetivo, arquivos, contratos, critérios de aceite), porque cada subagente começa sem o histórico da conversa.
- `security-senior`, `code-reviewer` e `architect` são somente leitura por desenho: não lhes dê `Write`/`Edit`.
- Princípios do `tech-lead`: menor mudança que resolve o problema, sem over-engineering; não inventar fatos sobre o código (verificar lendo); ações destrutivas ou irreversíveis exigem confirmação do usuário.

Ao adicionar ou alterar um agente, mantenha a tabela de roteamento no corpo de `tech-lead.md` sincronizada com os arquivos existentes.

## Skills (`.claude/skills/`)

Cada skill é `.claude/skills/<nome>/SKILL.md` (frontmatter `name` igual ao nome da pasta e `description`; corpo em português).

- `new-feature`: feature ponta a ponta (UI, API, banco, testes).
- `bugfix`: correção de bug com causa raiz, correção mínima e teste de regressão.
- `refactor`: refatoração segura, sem mudar comportamento externo.
- `code-review-checklist`: revisão de diff/PR com checklist e achados por severidade.
- `security-audit`: auditoria defensiva de segurança com relatório por severidade.
- `write-tests`: criação e melhoria de testes (unitário, integração, E2E).
- `api-design`: contratos de API, erros, paginação, versionamento e breaking changes.
- `db-migration`: migrações seguras, zero-downtime e plano de rollback.
- `release`: release/deploy com testes, changelog, versionamento, smoke test e rollback.
