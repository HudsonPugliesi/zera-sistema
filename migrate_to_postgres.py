"""
Copia todos os dados do zera.db (SQLite) para um banco Postgres.

Uso:
    python migrate_to_postgres.py "postgresql://usuario:senha@host/banco"

Ou defina DATABASE_URL no .env e rode sem argumento:
    python migrate_to_postgres.py

O que o script faz:
  1. Cria todas as tabelas no Postgres (a partir dos models do Flask-SQLAlchemy).
  2. Copia os dados do SQLite para o Postgres, tabela por tabela, respeitando
     a ordem de chaves estrangeiras.
  3. Ajusta as sequências de autoincremento do Postgres para continuar a
     partir do maior id já existente (senão o próximo INSERT colide).

É seguro rodar mais de uma vez em um banco Postgres vazio; se as tabelas já
tiverem dados, o script para e avisa, para não duplicar registros.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from db_url import normalizar_postgres_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SQLITE_PATH = os.path.join(BASE_DIR, "zera.db")


def get_postgres_url():
    if len(sys.argv) > 1:
        return sys.argv[1]
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Erro: informe a URL do Postgres como argumento ou defina DATABASE_URL no .env")
        sys.exit(1)
    return url


def main():
    if not os.path.exists(SQLITE_PATH):
        print(f"Banco SQLite não encontrado em {SQLITE_PATH}")
        sys.exit(1)

    postgres_url, engine_options = normalizar_postgres_url(get_postgres_url())

    import models  # importa depois de garantir que o .env já foi carregado

    sqlite_engine = create_engine("sqlite:///" + SQLITE_PATH)
    postgres_engine = create_engine(postgres_url, **engine_options)

    print("Criando tabelas no Postgres...")
    models.db.metadata.create_all(postgres_engine)

    tabelas = models.db.metadata.sorted_tables  # já em ordem segura de FK

    with postgres_engine.connect() as pg_conn:
        for tabela in tabelas:
            existentes = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{tabela.name}"')).scalar()
            if existentes:
                print(f"Tabela {tabela.name} já tem {existentes} registro(s) no Postgres — abortando.")
                print("Se quiser migrar mesmo assim, esvazie o banco Postgres antes e rode de novo.")
                sys.exit(1)

    print("Copiando dados...")
    with sqlite_engine.connect() as sqlite_conn, postgres_engine.begin() as pg_conn:
        for tabela in tabelas:
            linhas = sqlite_conn.execute(tabela.select()).mappings().all()
            if not linhas:
                print(f"  {tabela.name}: 0 registros (nada a copiar)")
                continue
            pg_conn.execute(tabela.insert(), [dict(linha) for linha in linhas])
            print(f"  {tabela.name}: {len(linhas)} registro(s) copiado(s)")

            if "id" in tabela.c:
                pg_conn.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{tabela.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM \"{tabela.name}\"), 1))"
                    )
                )

    print("\nMigração concluída com sucesso.")


if __name__ == "__main__":
    main()
