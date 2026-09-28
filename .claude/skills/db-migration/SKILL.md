---
name: db-migration
description: Use ao criar ou revisar migrações de banco de dados (schema, índices, constraints, backfill de dados), especialmente em tabelas grandes ou com requisito de zero-downtime e plano de rollback.
---

# Migrações de banco seguras

Responsáveis: `database-senior` (autor), `backend-senior` (código compatível), `devops-senior` (execução), `code-reviewer`/`security-senior` (revisão).

## Princípio: expand / migrate / contract
Nunca faça mudança destrutiva num único deploy. Sequência:
1. **Expand**: adicione coluna/tabela/índice novos, compatíveis com o código antigo (nullable ou com default).
2. **Deploy do código** que escreve nos dois modelos (dual-write) e lê do novo com fallback.
3. **Backfill** dos dados antigos, em lotes.
4. **Validação** (contagens, checksums, amostras) e troca da leitura para o novo.
5. **Contract**: remova o antigo só em release posterior, após janela de segurança.

## Passos
1. Descreva a mudança, tamanho das tabelas e locks esperados.
2. Escreva migração `up` e `down` (ou justifique por que `down` é irreversível e use backup/PITR).
3. Teste em cópia com volume realista; meça tempo e locks.
4. Escreva o plano de rollback antes de aplicar.
5. Aplique fora de pico, com monitoramento; confirme e registre.

## Regras de segurança
- Índices em tabela grande: criação concorrente/online (`CREATE INDEX CONCURRENTLY` no Postgres; `ALGORITHM=INPLACE` no MySQL), fora de transação quando exigido.
- `NOT NULL`/FK/CHECK: adicione como não validado, backfill, depois valide.
- Coluna com default: verifique se o SGBD reescreve a tabela (versões antigas reescrevem).
- Renomear = adicionar nova + copiar + remover antiga; nunca `RENAME` direto com código antigo no ar.
- Backfill em lotes pequenos com pausa, idempotente e retomável; nunca uma única transação gigante.
- Defina `lock_timeout`/`statement_timeout`; falhe rápido em vez de bloquear produção.
- Faça backup/snapshot verificado antes de mudanças destrutivas.

## Checklist
- [ ] Padrão expand/contract respeitado
- [ ] `down` testado ou irreversibilidade documentada
- [ ] Testada com volume realista; locks medidos
- [ ] Índices criados online
- [ ] Backfill em lotes, idempotente
- [ ] Backup feito; plano de rollback escrito
- [ ] Código antigo e novo funcionam com o schema intermediário
