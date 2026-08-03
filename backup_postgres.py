"""
Backup do banco Postgres (Neon) em produção.

Exporta todas as tabelas do Postgres para um arquivo SQLite local
timestampado em backups/, no mesmo formato que migrate_to_postgres.py usa
para importar — ou seja, dá pra restaurar rodando o processo inverso
(migrate_to_postgres.py apontando para um Postgres novo/vazio a partir
desse arquivo).

Mantém os últimos 30 backups e apaga os mais antigos.
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
KEEP_ULTIMOS = 30

load_dotenv(os.path.join(BASE_DIR, ".env"))


def backup():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL não definida — nada a fazer (sistema está usando SQLite local).")
        return

    import models

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUP_DIR, f"zera_postgres_{timestamp}.db")

    postgres_engine = create_engine(database_url)
    sqlite_engine = create_engine("sqlite:///" + destino)

    models.db.metadata.create_all(sqlite_engine)
    tabelas = models.db.metadata.sorted_tables

    with postgres_engine.connect() as pg_conn, sqlite_engine.begin() as sqlite_conn:
        for tabela in tabelas:
            linhas = pg_conn.execute(tabela.select()).mappings().all()
            if linhas:
                sqlite_conn.execute(tabela.insert(), [dict(linha) for linha in linhas])

    print(f"Backup criado: {destino}")
    _remover_antigos()


def _remover_antigos():
    backups = sorted(
        (f for f in os.listdir(BACKUP_DIR) if f.startswith("zera_postgres_") and f.endswith(".db")),
        reverse=True,
    )
    for antigo in backups[KEEP_ULTIMOS:]:
        os.remove(os.path.join(BACKUP_DIR, antigo))
        print(f"Backup antigo removido: {antigo}")


if __name__ == "__main__":
    backup()
