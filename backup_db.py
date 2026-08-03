import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "zera.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
KEEP_ULTIMOS = 30


def backup():
    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado em {DB_PATH}, nada a fazer.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUP_DIR, f"zera_{timestamp}.db")

    # Usa a API de backup do sqlite3 em vez de copiar o arquivo bruto,
    # assim a cópia fica consistente mesmo com o app rodando e escrevendo.
    origem_con = sqlite3.connect(DB_PATH)
    destino_con = sqlite3.connect(destino)
    with destino_con:
        origem_con.backup(destino_con)
    origem_con.close()
    destino_con.close()
    print(f"Backup criado: {destino}")

    _remover_antigos()


def _remover_antigos():
    backups = sorted(
        (f for f in os.listdir(BACKUP_DIR) if f.startswith("zera_") and f.endswith(".db")),
        reverse=True,
    )
    for antigo in backups[KEEP_ULTIMOS:]:
        os.remove(os.path.join(BACKUP_DIR, antigo))
        print(f"Backup antigo removido: {antigo}")


if __name__ == "__main__":
    backup()
