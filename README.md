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
- **Senha:** `admin123`

Troque essa senha em Usuários assim que possível.

Para aprender a usar cada tela do sistema (financeiro, estoque,
patrimônio, alunos, usuários etc.), veja o [Manual do Sistema](MANUAL.md).

## Deploy na Vercel

O projeto já inclui `vercel.json` para deploy direto (basta importar o
repositório na Vercel). **Atenção:** a Vercel roda o Flask como função
serverless com sistema de arquivos somente leitura — o banco SQLite é
gravado em `/tmp`, que **não é persistente**: os dados cadastrados podem
ser perdidos a qualquer redeploy, cold start ou nova instância. Isso serve
para demonstrar a interface, não para uso real da escola. Para uso real,
migre para um banco externo (Postgres) e ajuste `SQLALCHEMY_DATABASE_URI`
em `app.py`.
