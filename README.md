# Sistema Zera — Instruções de Uso

Sistema completo de gestão escolar: dashboard financeiro, lançamentos de
receitas/despesas, produtos, entrada/saída de estoque, compras, patrimônio,
fornecedores, funcionários, alunos, usuários e auditoria. Backend em Flask
com SQLAlchemy (SQLite) e login via Flask-Login.

1. Crie e ative um ambiente virtual (recomendado):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

1. Instale as dependências:

```powershell
pip install -r requirements.txt
```

1. Rode a aplicação:

```powershell
python app.py
```

Abra <http://127.0.0.1:5000> no navegador. Na primeira execução o banco
`zera.db` é criado automaticamente e um usuário administrador padrão é
gerado:

- **Usuário:** `admin`
- **Senha:** a definida em `ADMIN_PASSWORD` (veja `.env.example`). Se a
  variável não existir, uma senha aleatória é exibida no terminal na
  primeira execução.

Para aprender a usar cada tela do sistema (financeiro, estoque,
patrimônio, alunos, usuários etc.), veja o [Manual do Sistema](MANUAL.md).

## Deploy na Vercel

O projeto já inclui `vercel.json` para deploy direto (basta importar o
repositório na Vercel). **Atenção:** a Vercel roda o Flask como função
serverless com sistema de arquivos somente leitura; o SQLite em `/tmp`
**não é persistente**. Por isso, na Vercel o app **não sobe** sem estas
variáveis (Settings > Environment Variables > Production):

- `DATABASE_URL`: Postgres (Neon / Vercel Postgres). Para levar os dados do
  SQLite local, rode `python migrate_to_postgres.py`.
- `SECRET_KEY`: chave fixa das sessões.
- `ADMIN_PASSWORD`: senha inicial do `admin` (só vale se o banco estiver vazio).

Como o esquema não é criado automaticamente com `DATABASE_URL`, rode o
`migrate_to_postgres.py` (ele cria as tabelas) antes do primeiro acesso.
