---
name: release
description: Use ao preparar, executar ou reverter uma release/deploy para produção ou staging — validação de testes, changelog, versionamento semântico, smoke test e rollback.
---

# Release / Deploy

Responsáveis: `tech-lead` (go/no-go), `test-senior` (testes), `devops-senior` (deploy), `security-senior` (verificação), `docs-writer` (changelog), `code-reviewer` (revisão final).

## Passos
1. **Congele o escopo**: liste o que entra (PRs/commits) e pendências conhecidas.
2. **Versão** (SemVer): MAJOR = breaking change, MINOR = funcionalidade compatível, PATCH = correção. Atualize arquivos de versão e crie tag.
3. **Qualidade**: build limpo, lint, testes unitários/integração/e2e verdes, sem vulnerabilidades críticas em dependências.
4. **Changelog**: agrupe em Adicionado / Alterado / Corrigido / Removido / Segurança; destaque breaking changes e migrações necessárias.
5. **Pré-deploy**: migrações revisadas (veja skill `db-migration`), variáveis/segredos configurados, feature flags definidas, backup feito.
6. **Deploy** gradual quando possível (canary/blue-green) e fora de horário crítico.
7. **Smoke test** pós-deploy: health check, login, fluxo crítico de negócio, uma leitura e uma escrita reais.
8. **Monitore** 15–30 min: taxa de erros, latência, logs, filas, métricas de negócio.
9. **Decida**: confirmar ou reverter; comunique resultado.

## Rollback
- Gatilhos claros: aumento de erros 5xx, falha no smoke test, degradação de latência acima do limite combinado.
- Reverta para a versão/tag anterior (artefato imutável já disponível) ou desligue a feature flag.
- Migrações: só reverta schema se `down` for seguro; senão mantenha schema (expand-only) e reverta apenas o código.
- Registre incidente e causa; abra pós-mortem se houve impacto.

## Checklist
- [ ] Escopo congelado e versão definida (tag criada)
- [ ] Testes e build verdes; dependências verificadas
- [ ] Changelog escrito com breaking changes
- [ ] Migrações revisadas; backup feito
- [ ] Segredos/config e flags prontos
- [ ] Plano de rollback testável e responsável definido
- [ ] Smoke test executado e monitoramento pós-deploy concluído
- [ ] Comunicação enviada (equipe/usuários)
