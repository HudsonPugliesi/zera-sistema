"""Adiciona a coluna valor_mensalidade na tabela alunos.

db.create_all() só cria tabelas que não existem — não adiciona colunas em
tabelas já existentes. Esse script cobre esse caso rodando ALTER TABLE
ADD COLUMN IF NOT EXISTS, que é uma operação aditiva e segura (não apaga
nem altera dados existentes).

Uso:
    python migrations/2026_09_28_add_valor_mensalidade.py
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import sys
sys.path.insert(0, BASE_DIR)
from db_url import normalizar_postgres_url


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL não definida — nada a fazer (sistema usaria SQLite local, que já recria via db.create_all()).")
        return

    url, engine_options = normalizar_postgres_url(database_url)
    engine = create_engine(url, **engine_options)

    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE "alunos" ADD COLUMN IF NOT EXISTS "valor_mensalidade" FLOAT DEFAULT 0'))
        print("OK: alunos.valor_mensalidade")

    print("\nMigração concluída.")


if __name__ == "__main__":
    main()
