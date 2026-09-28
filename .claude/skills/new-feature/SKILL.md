---
name: new-feature
description: Use ao implementar uma feature nova ponta a ponta (UI, API, banco, testes). Acione quando o pedido for "adicionar", "criar" ou "implementar" uma funcionalidade que atravessa mais de uma camada ou exige planejamento.
---

# Nova feature ponta a ponta

## 1. Entender
- Reescreva o requisito em 2-3 frases e liste critérios de aceite verificáveis.
- Leia o código vizinho e convenções existentes antes de propor algo.
- Dúvida que muda o desenho: pergunte ao usuário antes de codar.

## 2. Planejar
- `tech-lead` quebra o trabalho em tarefas por camada, com ordem e dependências.
- Mudança estrutural grande (novo módulo, contrato, integração): consulte `architect`.
- Defina o contrato (payload da API, schema, props) ANTES de implementar.

## 3. Delegar por camada
- `database-senior`: migração, índices, rollback.
- `backend-senior`: endpoints, regras de negócio, validação.
- `frontend-senior`: telas, estados (loading/erro/vazio), acessibilidade.
- `devops-senior`: variáveis de ambiente, pipeline, deploy, se afetados.
- Cada tarefa entregue com arquivos alterados e como validar.

## 4. Testar
- `test-senior`: testes unitários da regra, integração da API, fluxo principal.
- Cubra caminho feliz, erros e bordas dos critérios de aceite.
- Rode a suíte completa; nada quebrado.

## 5. Revisar
- `code-reviewer` revisa o diff completo.
- `security-senior` se houver auth, entrada de usuário, dados sensíveis ou upload.
- `performance-senior` se houver consultas pesadas ou listas grandes.
- `docs-writer` atualiza README/API docs se o uso mudou.

## Checklist final
- [ ] Critérios de aceite atendidos e demonstrados
- [ ] Contrato entre camadas consistente
- [ ] Migração reversível
- [ ] Testes novos passando + suíte verde
- [ ] Sem segredos, logs de debug ou código morto
- [ ] Docs atualizadas
