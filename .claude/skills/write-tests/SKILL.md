---
name: write-tests
description: Use ao criar ou melhorar testes (unitário, integração, E2E), cobrir um bug corrigido ou nova funcionalidade, escolher a estratégia de teste ou rodar um teste isolado.
---

# Escrita de testes

## Passos
1. Descubra o framework e convenções: veja `package.json`, `pytest.ini`, `*.csproj`, testes existentes (nome, pasta, helpers). Siga o padrão já usado.
2. Escolha o nível:
   - **Unitário**: lógica pura, rápido, sem I/O; maior volume.
   - **Integração**: módulos + banco/API reais ou em contêiner; valida contratos e queries.
   - **E2E**: poucos fluxos críticos pelo usuário (login, checkout); mais lentos.
3. Liste os casos antes de codar; escreva no padrão Arrange-Act-Assert, um comportamento por teste.
4. Para bug: escreva primeiro o teste que falha, depois corrija (`debugger` ajuda a isolar).
5. Rode o teste novo, depois a suíte completa. Para casos complexos, consulte `test-senior`.

## Casos de borda
- [ ] Vazio, nulo/undefined, zero, negativo, limites (mín/máx, off-by-one)
- [ ] Strings longas, unicode, espaços, caracteres especiais
- [ ] Entrada inválida e erros esperados (exceções, status 4xx/5xx)
- [ ] Duplicados, ordem, paginação, datas/fusos, arredondamento
- [ ] Permissões negadas, concorrência, timeout de dependência externa

## Boas práticas
- Nome descreve o comportamento (`retorna erro quando email é inválido`).
- Testes independentes, sem ordem nem estado compartilhado; dados criados por teste.
- Mocke só fronteiras externas (rede, relógio, e-mail), não a lógica própria.
- Sem `sleep` arbitrário; sem testes flakey.

## Rodar um teste único
- Jest/Vitest: `npx jest caminho/arquivo.test.ts -t "nome do teste"` / `npx vitest run arquivo -t "nome"`
- Pytest: `pytest caminho/test_x.py::test_nome -x`
- .NET: `dotnet test --filter "FullyQualifiedName~NomeDoTeste"`
- Playwright: `npx playwright test arquivo.spec.ts -g "nome"`
- Go: `go test ./pkg -run TestNome`
