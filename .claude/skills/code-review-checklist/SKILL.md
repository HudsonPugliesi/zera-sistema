---
name: code-review-checklist
description: Use ao revisar um diff, PR ou conjunto de arquivos alterados antes de merge. Aplica checklist de correção, testes, segurança, legibilidade e breaking changes, e entrega achados por severidade.
---

# Revisão de código

## Passos
1. Delimite o escopo: liste os arquivos alterados e leia o diff inteiro antes de comentar.
2. Entenda a intenção (descrição do PR/tarefa). Se o diff não cumpre a intenção, isso é o primeiro achado.
3. Percorra o checklist abaixo, arquivo a arquivo.
4. Verifique se testes e lint/build rodam (peça ao `test-senior` se faltar cobertura).
5. Para achados de segurança ou desempenho profundos, acione `security-senior` ou `performance-senior`; para decisões estruturais, `architect`.
6. Emita o relatório no formato abaixo.

## Checklist
- [ ] Correção: lógica, condições de borda, null/vazio, erros tratados, concorrência, off-by-one.
- [ ] Testes: novo comportamento coberto, casos de borda e regressão do bug corrigido.
- [ ] Segurança: entrada validada, sem segredos no código, queries parametrizadas, authz checada.
- [ ] Legibilidade: nomes claros, funções pequenas, sem código morto ou duplicado, comentários explicam o "porquê".
- [ ] Breaking changes: API pública, schema/migração, contratos, variáveis de ambiente, compatibilidade retroativa.
- [ ] Desempenho: N+1, loops caros, chamadas de I/O desnecessárias.
- [ ] Escopo: nada alheio à tarefa no diff.

## Formato de saída
Uma seção por severidade, omitindo as vazias. Cada item: `arquivo:linha` — problema — sugestão.
- **Bloqueante**: bug, falha de segurança, perda de dados, breaking change não tratado.
- **Importante**: falta de teste, tratamento de erro fraco, risco de desempenho.
- **Sugestão**: legibilidade, estilo, refatoração opcional.
- **Elogio** (opcional): decisões boas que devem ser mantidas.

Termine com veredito: Aprovar / Aprovar com ressalvas / Mudanças necessárias.
Não reescreva o código do autor sem pedido; aponte e sugira.
