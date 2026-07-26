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
