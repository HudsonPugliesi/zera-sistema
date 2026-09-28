---
name: api-design
description: Use ao desenhar ou alterar endpoints, contratos de API (REST ou GraphQL), formato de erros, paginação, validação ou versionamento; também ao avaliar se uma mudança quebra clientes existentes.
---

# Desenho de API

Responsáveis: `architect` (contrato), `backend-senior` (implementação), `security-senior` (authz/validação), `test-senior` (testes de contrato), `docs-writer` (referência).

## Passos
1. Levante consumidores, casos de uso e dados envolvidos antes de desenhar.
2. Modele recursos (substantivos, plural: `/orders/{id}`); ações não-CRUD como sub-recurso (`POST /orders/{id}/cancel`). No GraphQL: tipos pequenos, mutations com input/payload dedicados.
3. Defina por endpoint: método, path, request, response, status codes, auth/permissão exigida.
4. Escreva o contrato (OpenAPI/SDL) ANTES do código e revise com o consumidor.
5. Implemente validação na borda (schema), rejeitando campos inválidos com 400/422.
6. Teste o contrato (casos felizes, erros, limites) e atualize a documentação.

## Convenções
- Métodos: GET seguro/idempotente; PUT/DELETE idempotentes; POST criação (aceitar `Idempotency-Key` em operações sensíveis).
- Erros padronizados (ex.: RFC 9457): `{type, title, status, detail, code, errors[]}`; nunca expor stack trace nem detalhes internos.
- Status: 201 + `Location` na criação, 204 sem corpo, 401 vs 403 distintos, 404, 409 conflito, 429 com `Retry-After`.
- Paginação: cursor para listas grandes/mutáveis (`limit`, `cursor`, `next_cursor`); offset só para conjuntos pequenos. Limite máximo obrigatório. Ordenação e filtros explícitos e whitelisted.
- Datas ISO 8601 UTC; dinheiro em inteiro/decimal string com moeda; IDs opacos.

## Compatibilidade e versionamento
- Não quebra: adicionar campo opcional, endpoint novo, valor de enum novo (se clientes toleram).
- Quebra: remover/renomear campo, mudar tipo, tornar campo obrigatório, mudar semântica ou status code.
- Breaking change exige nova versão (`/v2` ou header), período de depreciação (`Deprecation`/`Sunset`) e aviso aos consumidores.

## Checklist
- [ ] Contrato escrito e revisado
- [ ] Authn/authz e rate limit definidos
- [ ] Validação e erros padronizados
- [ ] Paginação com limite máximo
- [ ] Sem breaking change (ou versão nova + depreciação)
- [ ] Testes de contrato e docs atualizados
