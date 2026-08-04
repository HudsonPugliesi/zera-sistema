"""Importa os lançamentos financeiros da planilha "Fluxo_de_Caixa_Escola.xlsx"
(aba "Lançamentos") pro banco de dados do sistema, e cadastra as categorias
financeiras que a planilha usa e o sistema ainda não tem.

Uso:
    python migrations/importar_planilha_fluxo_caixa.py
"""

import os
import sys
from datetime import datetime

import openpyxl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PLANILHA_PATH = os.path.join(os.path.dirname(BASE_DIR), "Fluxo_de_Caixa_Escola (4).xlsx")
CRIADO_POR = "Importação (planilha)"


def ler_lancamentos():
    wb = openpyxl.load_workbook(PLANILHA_PATH, data_only=True)
    ws = wb["Lançamentos"]
    lancamentos = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        data_vencimento, data_pagamento, tipo, natureza, categoria, descricao, valor = row[:7]
        if data_vencimento is None or tipo is None:
            continue
        lancamentos.append(
            {
                "data_vencimento": data_vencimento.date(),
                "data_pagamento": data_pagamento.date() if data_pagamento else None,
                "tipo": "despesa" if tipo == "Despesa" else "receita",
                "natureza": "variavel" if "ri" in (natureza or "") else "fixa",
                "categoria": (categoria or "").strip(),
                "descricao": (descricao or "").strip(),
                "valor": float(valor or 0),
            }
        )
    return lancamentos


def main():
    import app as a

    with a.app.app_context():
        existentes = a.LancamentoFinanceiro.query.count()
        if existentes > 0:
            print(f"O sistema já tem {existentes} lançamento(s) financeiro(s) cadastrado(s).")
            print("Para evitar duplicar dados, esse script só roda com a tabela vazia. Abortando.")
            return

        lancamentos = ler_lancamentos()
        print(f"{len(lancamentos)} lançamentos lidos da planilha.")

        categorias_existentes = {
            (c.tipo, c.natureza, c.nome.strip().lower()) for c in a.CategoriaFinanceira.query.all()
        }
        categorias_planilha = {(l["tipo"], l["natureza"], l["categoria"]) for l in lancamentos if l["categoria"]}
        novas_categorias = [
            c for c in categorias_planilha if (c[0], c[1], c[2].lower()) not in categorias_existentes
        ]
        agora = datetime.now().replace(microsecond=0)
        for tipo, natureza, nome in novas_categorias:
            cat = a.CategoriaFinanceira(tipo=tipo, natureza=natureza, nome=nome)
            cat.criado_por = CRIADO_POR
            cat.criado_em = agora
            a.db.session.add(cat)
        print(f"{len(novas_categorias)} categoria(s) nova(s) cadastrada(s).")

        for l in lancamentos:
            lanc = a.LancamentoFinanceiro(**l)
            lanc.criado_por = CRIADO_POR
            lanc.criado_em = agora
            a.db.session.add(lanc)

        a.db.session.commit()

        log = a.Auditoria(
            data_hora=agora,
            usuario=CRIADO_POR,
            acao="criacao",
            modulo="financeiro",
            descricao=f"Importação em massa de {len(lancamentos)} lançamentos financeiros via planilha",
            ip="local",
        )
        a.db.session.add(log)
        a.db.session.commit()

        print(f"\nImportação concluída: {len(lancamentos)} lançamentos e {len(novas_categorias)} categorias novas.")


if __name__ == "__main__":
    main()
