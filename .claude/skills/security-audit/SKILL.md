---
name: security-audit
description: Use para auditoria defensiva de segurança do projeto ou de um módulo - entrada de usuário, autenticação/autorização, segredos, dependências e configuração. Produz relatório com severidade e correções. Não use para explorar sistemas de terceiros.
---

# Auditoria de segurança (defensiva)

## Passos
1. Mapeie a superfície: rotas/endpoints, formulários, uploads, jobs, integrações externas.
2. Percorra cada área do checklist com Grep/Read no código; registre evidência (`arquivo:linha`).
3. Rode ferramentas de dependência disponíveis (`npm audit`, `pip-audit`, `dotnet list package --vulnerable`, etc.).
4. Delegue a `security-senior` os pontos complexos; `database-senior` para SQL/permissões; `devops-senior` para infra/CI.
5. Corrija apenas se solicitado; do contrário, apenas reporte.

## Checklist
- [ ] Entrada de usuário: validação no servidor, SQL parametrizado, escape de saída (XSS), proteção contra path traversal, SSRF, desserialização insegura, limites de upload/tamanho.
- [ ] Autenticação: hash de senha forte (bcrypt/argon2), expiração de sessão/token, rate limit e bloqueio de brute force, cookies `HttpOnly/Secure/SameSite`.
- [ ] Autorização: checagem em toda rota no servidor, sem IDOR (verificar dono do recurso), princípio do menor privilégio.
- [ ] Segredos: nada em código, `.env` no `.gitignore`, sem chaves em logs ou histórico; rotacionar se vazadas.
- [ ] Dependências: vulnerabilidades conhecidas, versões fixadas, pacotes abandonados.
- [ ] Configuração: debug desligado em produção, CORS restrito, headers (CSP, HSTS), HTTPS, mensagens de erro sem stack trace, logs sem dados sensíveis.
- [ ] CSRF em ações que alteram estado; dados sensíveis criptografados em repouso/trânsito.

## Formato do relatório
Resumo (2-3 linhas) e, por achado:
- **ID / Título** — Severidade (Crítica/Alta/Média/Baixa/Info)
- Local: `arquivo:linha`
- Risco: o que um atacante consegue
- Evidência: trecho ou comando
- Correção: passo concreto

Ordene da maior para a menor severidade. Finalize com "Áreas não verificadas" para deixar claro o que ficou de fora.
