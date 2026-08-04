"""Adiciona as colunas de rastreio (criado_por/criado_em/atualizado_por/
atualizado_em) nas tabelas que ganharam RastreioMixin em models.py.

db.create_all() só cria tabelas que não existem — não adiciona colunas em
tabelas já existentes. Esse script cobre esse caso rodando ALTER TABLE
ADD COLUMN IF NOT EXISTS, que é uma operação aditiva e segura (não apaga
nem altera dados existentes).

Uso:
    python migrations/2026_08_04_add_rastreio_colunas.py
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import sys
sys.path.insert(0, BASE_DIR)
from db_url import normalizar_postgres_url

TABELAS = [
    "fornecedores",
    "funcionarios",
    "produtos",
    "estoque_entradas",
    "estoque_saidas",
    "compras",
    "patrimonios",
    "alunos",
    "inscricoes",
    "categorias_financeiras",
    "lancamentos_financeiros",
]

COLUNAS = {
    "criado_por": "VARCHAR(150)",
    "criado_em": "TIMESTAMP",
    "atualizado_por": "VARCHAR(150)",
    "atualizado_em": "TIMESTAMP",
}


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL não definida — nada a fazer (sistema usaria SQLite local, que já recria via db.create_all()).")
        return

    url, engine_options = normalizar_postgres_url(database_url)
    engine = create_engine(url, **engine_options)

    with engine.begin() as conn:
        for tabela in TABELAS:
            for coluna, tipo in COLUNAS.items():
                conn.execute(text(f'ALTER TABLE "{tabela}" ADD COLUMN IF NOT EXISTS "{coluna}" {tipo}'))
                print(f"OK: {tabela}.{coluna}")

    print("\nMigração concluída.")


if __name__ == "__main__":
    main()
