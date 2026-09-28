---
name: bugfix
description: Use ao corrigir um bug, erro, comportamento inesperado ou teste falhando. Acione quando o pedido for "corrigir", "está quebrando" ou "não funciona"; foco em causa raiz e correção mínima com teste de regressão.
---

# Correção de bug

## 1. Reproduzir
- Obtenha passos, entrada, ambiente e erro/stack exatos.
- Reproduza localmente. Sem reprodução, não corrija: colete logs ou peça dados.
- Transforme a reprodução em teste que FALHA (vermelho).

## 2. Isolar
- Delegue a investigação difícil ao `debugger`.
- Reduza: qual camada (UI, API, banco, infra)? qual commit/mudança introduziu?
- Bissecte entradas e código; use logs/breakpoints temporários (remova depois).

## 3. Causa raiz
- Escreva em uma frase POR QUE ocorre, não só ONDE.
- Verifique se o mesmo padrão existe em outros pontos (busque no código).
- Se envolver segurança, chame `security-senior`; se lentidão, `performance-senior`.

## 4. Correção mínima
- Menor mudança que ataca a causa; sem refatorar de carona.
- Não mascare (try/catch vazio, if especial para o caso).
- Delegue à camada dona: `backend-senior`, `frontend-senior` ou `database-senior`.

## 5. Teste de regressão
- O teste do passo 1 agora passa (verde); adicione bordas próximas.
- `test-senior` roda a suíte completa.
- `code-reviewer` revisa o diff.

## Checklist final
- [ ] Bug reproduzido antes e resolvido depois
- [ ] Causa raiz documentada no commit/PR
- [ ] Teste de regressão incluído
- [ ] Diff mínimo, sem código de depuração
- [ ] Casos semelhantes verificados
