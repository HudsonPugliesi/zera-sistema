---
name: refactor
description: Use ao refatorar código (renomear, extrair, reorganizar, remover duplicação, simplificar) sem mudar comportamento. Acione quando o pedido for "refatorar", "limpar" ou "reorganizar" e a mudança deve ser segura e verificável.
---

# Refatoração segura

Regra de ouro: comportamento externo NÃO muda. Nada de feature ou bugfix junto.

## 1. Definir escopo
- Declare o objetivo (ex.: extrair serviço, remover duplicação) e o que fica fora.
- Mudança que cruza módulos: consulte `architect` e alinhe com `tech-lead`.

## 2. Rede de segurança
- Verifique cobertura do trecho alvo; rode a suíte e confirme verde.
- Cobertura fraca: `test-senior` escreve testes de caracterização (fixam o comportamento ATUAL, mesmo que feio).
- Cubra saídas, efeitos colaterais e erros; commit dos testes antes de mexer.

## 3. Passos pequenos
- Um tipo de mudança por vez: renomear, extrair, mover, simplificar.
- Após CADA passo: rode os testes; se falhar, reverta o passo, não "conserte" o teste.
- Não altere assinaturas públicas sem atualizar todos os chamadores (busque usos).
- Não edite testes de caracterização para passarem.

## 4. Verificar
- `performance-senior` se o trecho é crítico em desempenho.
- `code-reviewer` revisa: diff deve ser movimento/renomeação, sem lógica nova.
- `docs-writer` atualiza docs se estrutura ou nomes públicos mudaram.

## Checklist final
- [ ] Testes de caracterização existiam antes e continuam intactos
- [ ] Suíte verde após cada passo e no final
- [ ] Nenhuma mudança de comportamento, API ou schema
- [ ] Sem código morto ou imports órfãos
- [ ] Commits pequenos, mensagem diz "refactor:"
