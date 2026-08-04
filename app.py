import csv
import io
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect

from db_url import normalizar_postgres_url
from models import (
    Aluno,
    Auditoria,
    CategoriaFinanceira,
    Compra,
    CompraItem,
    Duplicata,
    EstoqueEntrada,
    EstoqueSaida,
    Fornecedor,
    Funcionario,
    Inscricao,
    LancamentoFinanceiro,
    Patrimonio,
    Produto,
    SERIES_CHOICES,
    Usuario,
    db,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PER_PAGE = 15


def paginar_ou_todos(query, order_by=None):
    """Pagina a query normalmente, mas se ?relatorio=1 estiver na URL retorna
    todos os registros de uma vez (sem paginação), para o relatório completo."""
    if order_by is not None:
        query = query.order_by(order_by)
    if request.args.get("relatorio") == "1":
        return query.all(), None
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    return pagination.items, pagination

load_dotenv(os.path.join(BASE_DIR, ".env"))

# Se DATABASE_URL estiver definida (Postgres, ex: Neon/Vercel Postgres), usa
# esse banco. Caso contrário, cai para SQLite local — útil em dev sem precisar
# de um Postgres rodando. Na Vercel o sistema de arquivos do projeto é somente
# leitura e /tmp não é persistente entre cold starts, então rodar lá sem
# DATABASE_URL configurada perde os dados a cada novo deploy/cold start.
_database_url = os.environ.get("DATABASE_URL")
_engine_options = {}
if _database_url:
    DB_URI, _engine_options = normalizar_postgres_url(_database_url)
else:
    DB_PATH = "/tmp/zera.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "zera.db")
    DB_URI = "sqlite:///" + DB_PATH

app = Flask(__name__, template_folder="templates")
# SECRET_KEY vem do arquivo .env (fora do código-fonte). Se não estiver
# definida, gera uma chave temporária só para a sessão atual do processo.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _engine_options
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Em produção (Vercel ou USE_HTTPS=true) o site só é servido via HTTPS, então o
# cookie de sessão pode exigir conexão segura. Em dev local sem HTTPS isso
# quebraria o login, por isso fica condicional.
_cookies_seguros = bool(os.environ.get("VERCEL")) or os.environ.get("USE_HTTPS", "false").lower() == "true"
app.config["SESSION_COOKIE_SECURE"] = _cookies_seguros
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar esta página."
login_manager.login_message_category = "warning"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.perfil != "admin":
            flash("Acesso restrito a administradores.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_now():
    return {"now": datetime.now()}


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


@app.template_filter("brl")
def format_brl(value):
    if not value:
        return "-"
    texto = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"(R${texto})" if value < 0 else f"R${texto}"


def registrar_auditoria(acao, modulo, descricao):
    usuario_nome = current_user.nome if current_user.is_authenticated else "Sistema"
    log = Auditoria(
        data_hora=datetime.now().replace(microsecond=0),
        usuario=usuario_nome,
        acao=acao,
        modulo=modulo,
        descricao=descricao,
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        login_input = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter(
            db.or_(Usuario.login == login_input, Usuario.email == login_input)
        ).first()
        if usuario and usuario.status == "ativo" and usuario.check_senha(senha):
            login_user(usuario)
            usuario.ultimo_acesso = datetime.now().replace(microsecond=0)
            db.session.commit()
            registrar_auditoria("login", "usuarios", f"Login realizado por {usuario.nome}")
            flash(f"Bem-vindo(a), {usuario.nome}!", "success")
            return redirect(url_for("home"))
        flash("Usuário ou senha inválidos.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    registrar_auditoria("logout", "usuarios", f"Logout realizado por {current_user.nome}")
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def home():
    return render_template("home.html")


# ---------------------------------------------------------------------------
# Dashboard financeiro
# ---------------------------------------------------------------------------

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _anos_disponiveis():
    anos = {datetime.now().year}
    data_ref_lancamento = db.func.coalesce(LancamentoFinanceiro.data_pagamento, LancamentoFinanceiro.data_vencimento)
    consultas = [
        db.session.query(db.func.distinct(db.func.extract("year", data_ref_lancamento))),
        db.session.query(db.func.distinct(db.func.extract("year", Compra.data_emissao))),
        db.session.query(db.func.distinct(db.func.extract("year", EstoqueEntrada.data))),
        db.session.query(db.func.distinct(db.func.extract("year", Patrimonio.data_aquisicao))).filter(
            Patrimonio.data_aquisicao.isnot(None)
        ),
    ]
    for consulta in consultas:
        for (ano,) in consulta:
            if ano is not None:
                anos.add(int(ano))
    return sorted(anos, reverse=True)


@app.route("/dashboard")
@login_required
def dashboard():
    ano = request.args.get("ano", datetime.now().year, type=int)

    receitas_mes = [0.0] * 12
    despesas_mes = [0.0] * 12

    data_ref_lancamento = db.func.coalesce(LancamentoFinanceiro.data_pagamento, LancamentoFinanceiro.data_vencimento)
    lancamentos_do_ano = db.session.query(
        LancamentoFinanceiro.tipo, LancamentoFinanceiro.valor, data_ref_lancamento
    ).filter(db.func.extract("year", data_ref_lancamento) == ano)
    for tipo, valor, ref in lancamentos_do_ano:
        if tipo == "receita":
            receitas_mes[ref.month - 1] += valor
        else:
            despesas_mes[ref.month - 1] += valor

    # Despesas automáticas: Compras, Entradas de Estoque e Patrimônio adquirido.
    compras_do_ano = db.session.query(Compra.data_emissao, Compra.valor_total).filter(
        db.func.extract("year", Compra.data_emissao) == ano
    )
    for (data_emissao, valor_total) in compras_do_ano:
        despesas_mes[data_emissao.month - 1] += valor_total or 0

    entradas_do_ano = db.session.query(EstoqueEntrada.data, EstoqueEntrada.valor_total).filter(
        db.func.extract("year", EstoqueEntrada.data) == ano
    )
    for (data, valor_total) in entradas_do_ano:
        despesas_mes[data.month - 1] += valor_total or 0

    patrimonio_do_ano = db.session.query(Patrimonio.data_aquisicao, Patrimonio.valor).filter(
        Patrimonio.data_aquisicao.isnot(None), db.func.extract("year", Patrimonio.data_aquisicao) == ano
    )
    for (data_aquisicao, valor) in patrimonio_do_ano:
        despesas_mes[data_aquisicao.month - 1] += valor or 0

    resumo_mensal = []
    saldo_acumulado = 0.0
    for i, mes in enumerate(MESES_ABREV):
        saldo_mes = receitas_mes[i] - despesas_mes[i]
        saldo_acumulado += saldo_mes
        resumo_mensal.append(
            {
                "mes": mes,
                "receitas": receitas_mes[i],
                "despesas": despesas_mes[i],
                "saldo_mes": saldo_mes,
                "saldo_acumulado": saldo_acumulado,
            }
        )

    total_receitas = sum(receitas_mes)
    total_despesas = sum(despesas_mes)
    return render_template(
        "dashboard.html",
        ano=ano,
        anos_disponiveis=_anos_disponiveis(),
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo_do_ano=total_receitas - total_despesas,
        saldo_acumulado_final=saldo_acumulado,
        resumo_mensal=resumo_mensal,
    )


# ---------------------------------------------------------------------------
# Lançamentos Financeiros
# ---------------------------------------------------------------------------

def _categorias_financeiras_json():
    categorias = CategoriaFinanceira.query.order_by(CategoriaFinanceira.nome).all()
    return [{"nome": c.nome, "tipo": c.tipo, "natureza": c.natureza} for c in categorias]


@app.route("/financeiro/lancamentos")
@login_required
def lancamentos_listar():
    q = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "").strip()
    natureza = request.args.get("natureza", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    query = LancamentoFinanceiro.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(LancamentoFinanceiro.categoria.ilike(like), LancamentoFinanceiro.descricao.ilike(like)))
    if tipo:
        query = query.filter(LancamentoFinanceiro.tipo == tipo)
    if natureza:
        query = query.filter(LancamentoFinanceiro.natureza == natureza)
    if data_inicio:
        query = query.filter(LancamentoFinanceiro.data_vencimento >= parse_date(data_inicio))
    if data_fim:
        query = query.filter(LancamentoFinanceiro.data_vencimento <= parse_date(data_fim))

    lancamentos, pagination = paginar_ou_todos(query, LancamentoFinanceiro.data_vencimento.desc())
    return render_template("lancamentos/list.html", lancamentos=lancamentos, pagination=pagination)


@app.route("/financeiro/lancamentos/novo", methods=["GET", "POST"])
@login_required
@admin_required
def lancamentos_novo():
    if request.method == "POST":
        lancamento = LancamentoFinanceiro(
            tipo=request.form["tipo"],
            natureza=request.form["natureza"],
            categoria=request.form["categoria"].strip(),
            descricao=request.form.get("descricao", "").strip(),
            valor=float(request.form.get("valor") or 0),
            data_vencimento=parse_date(request.form["data_vencimento"]),
            data_pagamento=parse_date(request.form.get("data_pagamento")),
        )
        db.session.add(lancamento)
        db.session.commit()
        registrar_auditoria(
            "criacao", "financeiro", f"Lançamento de {lancamento.tipo} ({lancamento.categoria}) cadastrado"
        )
        flash("Lançamento cadastrado com sucesso.", "success")
        return redirect(url_for("lancamentos_listar"))
    return render_template("lancamentos/form.html", lancamento=None, categorias=_categorias_financeiras_json())


@app.route("/financeiro/lancamentos/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def lancamentos_editar(id):
    lancamento = db.get_or_404(LancamentoFinanceiro, id)
    if request.method == "POST":
        lancamento.tipo = request.form["tipo"]
        lancamento.natureza = request.form["natureza"]
        lancamento.categoria = request.form["categoria"].strip()
        lancamento.descricao = request.form.get("descricao", "").strip()
        lancamento.valor = float(request.form.get("valor") or 0)
        lancamento.data_vencimento = parse_date(request.form["data_vencimento"])
        lancamento.data_pagamento = parse_date(request.form.get("data_pagamento"))
        db.session.commit()
        registrar_auditoria("edicao", "financeiro", f"Lançamento #{lancamento.id} atualizado")
        flash("Lançamento atualizado com sucesso.", "success")
        return redirect(url_for("lancamentos_listar"))
    return render_template("lancamentos/form.html", lancamento=lancamento, categorias=_categorias_financeiras_json())


@app.route("/financeiro/lancamentos/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def lancamentos_excluir(id):
    lancamento = db.get_or_404(LancamentoFinanceiro, id)
    descricao = f"{lancamento.tipo} ({lancamento.categoria})"
    db.session.delete(lancamento)
    db.session.commit()
    registrar_auditoria("exclusao", "financeiro", f"Lançamento {descricao} excluído")
    flash("Lançamento excluído.", "success")
    return redirect(url_for("lancamentos_listar"))


# ---------------------------------------------------------------------------
# Categorias Financeiras
# ---------------------------------------------------------------------------

@app.route("/financeiro/categorias")
@login_required
def categorias_financeiras_listar():
    categorias = CategoriaFinanceira.query.order_by(CategoriaFinanceira.nome).all()
    grupos = {
        ("receita", "fixa"): [],
        ("receita", "variavel"): [],
        ("despesa", "fixa"): [],
        ("despesa", "variavel"): [],
    }
    for categoria in categorias:
        grupos[(categoria.tipo, categoria.natureza)].append(categoria)
    return render_template("categorias_financeiras/list.html", grupos=grupos)


@app.route("/financeiro/categorias/nova", methods=["POST"])
@login_required
@admin_required
def categorias_financeiras_nova():
    nome = request.form.get("nome", "").strip()
    tipo = request.form.get("tipo")
    natureza = request.form.get("natureza")
    if nome and tipo and natureza:
        db.session.add(CategoriaFinanceira(tipo=tipo, natureza=natureza, nome=nome))
        db.session.commit()
        registrar_auditoria("criacao", "financeiro", f"Categoria {nome} ({tipo}/{natureza}) cadastrada")
        flash("Categoria cadastrada com sucesso.", "success")
    return redirect(url_for("categorias_financeiras_listar"))


@app.route("/financeiro/categorias/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def categorias_financeiras_excluir(id):
    categoria = db.get_or_404(CategoriaFinanceira, id)
    nome = categoria.nome
    db.session.delete(categoria)
    db.session.commit()
    registrar_auditoria("exclusao", "financeiro", f"Categoria {nome} excluída")
    flash("Categoria excluída.", "success")
    return redirect(url_for("categorias_financeiras_listar"))


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------

@app.route("/produtos")
@login_required
def produtos_listar():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()

    query = Produto.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Produto.nome.ilike(like), Produto.codigo.ilike(like)))
    if categoria:
        query = query.filter(Produto.categoria == categoria)

    produtos, pagination = paginar_ou_todos(query, Produto.nome)
    categorias = [c[0] for c in db.session.query(Produto.categoria).distinct() if c[0]]
    return render_template(
        "produtos/list.html", produtos=produtos, pagination=pagination, categorias=categorias
    )


def _gerar_codigo_produto():
    max_num = 0
    for (codigo,) in db.session.query(Produto.codigo):
        if codigo and codigo.isdigit():
            max_num = max(max_num, int(codigo))
    return f"{max_num + 1:04d}"


@app.route("/produtos/novo", methods=["GET", "POST"])
@login_required
@admin_required
def produtos_novo():
    if request.method == "POST":
        produto = Produto(
            codigo=request.form.get("codigo", "").strip() or _gerar_codigo_produto(),
            nome=request.form["nome"].strip(),
            categoria=request.form.get("categoria", "").strip(),
            unidade=request.form.get("unidade", "UN"),
            preco_custo=float(request.form.get("preco_custo") or 0),
            preco_venda=float(request.form.get("preco_venda") or 0),
            quantidade=int(request.form.get("quantidade") or 0),
            estoque_minimo=int(request.form.get("estoque_minimo") or 0),
            fornecedor_id=request.form.get("fornecedor_id") or None,
            status=request.form.get("status", "ativo"),
            descricao=request.form.get("descricao", ""),
        )
        db.session.add(produto)
        db.session.commit()
        registrar_auditoria("criacao", "produtos", f"Produto {produto.nome} cadastrado")
        flash("Produto cadastrado com sucesso.", "success")
        return redirect(url_for("produtos_listar"))
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    return render_template(
        "produtos/form.html", produto=None, fornecedores=fornecedores, codigo_sugerido=_gerar_codigo_produto()
    )


@app.route("/produtos/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def produtos_editar(id):
    produto = db.get_or_404(Produto, id)
    if request.method == "POST":
        produto.codigo = request.form["codigo"].strip()
        produto.nome = request.form["nome"].strip()
        produto.categoria = request.form.get("categoria", "").strip()
        produto.unidade = request.form.get("unidade", "UN")
        produto.preco_custo = float(request.form.get("preco_custo") or 0)
        produto.preco_venda = float(request.form.get("preco_venda") or 0)
        produto.quantidade = int(request.form.get("quantidade") or 0)
        produto.estoque_minimo = int(request.form.get("estoque_minimo") or 0)
        produto.fornecedor_id = request.form.get("fornecedor_id") or None
        produto.status = request.form.get("status", "ativo")
        produto.descricao = request.form.get("descricao", "")
        db.session.commit()
        registrar_auditoria("edicao", "produtos", f"Produto {produto.nome} atualizado")
        flash("Produto atualizado com sucesso.", "success")
        return redirect(url_for("produtos_listar"))
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    return render_template("produtos/form.html", produto=produto, fornecedores=fornecedores)


@app.route("/produtos/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def produtos_excluir(id):
    produto = db.get_or_404(Produto, id)
    nome = produto.nome
    db.session.delete(produto)
    db.session.commit()
    registrar_auditoria("exclusao", "produtos", f"Produto {nome} excluído")
    flash("Produto excluído.", "success")
    return redirect(url_for("produtos_listar"))


# ---------------------------------------------------------------------------
# Estoque - Entrada
# ---------------------------------------------------------------------------

@app.route("/estoque/entrada")
@login_required
def estoque_entrada_listar():
    q = request.args.get("q", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    query = EstoqueEntrada.query.join(Produto)
    if q:
        query = query.filter(Produto.nome.ilike(f"%{q}%"))
    if data_inicio:
        query = query.filter(EstoqueEntrada.data >= parse_date(data_inicio))
    if data_fim:
        query = query.filter(EstoqueEntrada.data <= parse_date(data_fim))

    entradas, pagination = paginar_ou_todos(query, EstoqueEntrada.data.desc())
    return render_template("estoque/entrada_list.html", entradas=entradas, pagination=pagination)


@app.route("/estoque/entrada/nova", methods=["GET", "POST"])
@login_required
@admin_required
def estoque_entrada_nova():
    if request.method == "POST":
        quantidade = int(request.form["quantidade"])
        valor_unitario = float(request.form.get("valor_unitario") or 0)
        produto = db.get_or_404(Produto, int(request.form["produto_id"]))
        entrada = EstoqueEntrada(
            produto_id=produto.id,
            data=parse_date(request.form["data"]),
            fornecedor_id=request.form.get("fornecedor_id") or None,
            nota_fiscal=request.form.get("nota_fiscal", ""),
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=quantidade * valor_unitario,
            responsavel=request.form.get("responsavel", ""),
            observacao=request.form.get("observacao", ""),
        )
        produto.quantidade = (produto.quantidade or 0) + quantidade
        db.session.add(entrada)
        db.session.commit()
        registrar_auditoria("criacao", "estoque", f"Entrada de {quantidade} un. de {produto.nome}")
        flash("Entrada registrada com sucesso.", "success")
        return redirect(url_for("estoque_entrada_listar"))
    produtos = Produto.query.order_by(Produto.nome).all()
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    return render_template("estoque/entrada_form.html", entrada=None, produtos=produtos, fornecedores=fornecedores)


@app.route("/estoque/entrada/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def estoque_entrada_editar(id):
    entrada = db.get_or_404(EstoqueEntrada, id)
    if request.method == "POST":
        produto_antigo = db.session.get(Produto, entrada.produto_id)
        if produto_antigo:
            produto_antigo.quantidade = (produto_antigo.quantidade or 0) - entrada.quantidade

        entrada.produto_id = int(request.form["produto_id"])
        entrada.data = parse_date(request.form["data"])
        entrada.fornecedor_id = request.form.get("fornecedor_id") or None
        entrada.nota_fiscal = request.form.get("nota_fiscal", "")
        entrada.quantidade = int(request.form["quantidade"])
        entrada.valor_unitario = float(request.form.get("valor_unitario") or 0)
        entrada.valor_total = entrada.quantidade * entrada.valor_unitario
        entrada.responsavel = request.form.get("responsavel", "")
        entrada.observacao = request.form.get("observacao", "")

        produto_novo = db.get_or_404(Produto, entrada.produto_id)
        produto_novo.quantidade = (produto_novo.quantidade or 0) + entrada.quantidade

        db.session.commit()
        registrar_auditoria("edicao", "estoque", f"Entrada #{entrada.id} atualizada")
        flash("Entrada atualizada com sucesso.", "success")
        return redirect(url_for("estoque_entrada_listar"))
    produtos = Produto.query.order_by(Produto.nome).all()
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    return render_template("estoque/entrada_form.html", entrada=entrada, produtos=produtos, fornecedores=fornecedores)


@app.route("/estoque/entrada/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def estoque_entrada_excluir(id):
    entrada = db.get_or_404(EstoqueEntrada, id)
    produto = db.session.get(Produto, entrada.produto_id)
    if produto:
        produto.quantidade = (produto.quantidade or 0) - entrada.quantidade
    db.session.delete(entrada)
    db.session.commit()
    registrar_auditoria("exclusao", "estoque", f"Entrada #{id} excluída")
    flash("Entrada excluída.", "success")
    return redirect(url_for("estoque_entrada_listar"))


# ---------------------------------------------------------------------------
# Estoque - Saída
# ---------------------------------------------------------------------------

@app.route("/estoque/saida")
@login_required
def estoque_saida_listar():
    q = request.args.get("q", "").strip()
    motivo = request.args.get("motivo", "").strip()

    query = EstoqueSaida.query.join(Produto)
    if q:
        query = query.filter(Produto.nome.ilike(f"%{q}%"))
    if motivo:
        query = query.filter(EstoqueSaida.motivo == motivo)

    saidas, pagination = paginar_ou_todos(query, EstoqueSaida.data.desc())
    return render_template("estoque/saida_list.html", saidas=saidas, pagination=pagination)


@app.route("/estoque/saida/nova", methods=["GET", "POST"])
@login_required
@admin_required
def estoque_saida_nova():
    if request.method == "POST":
        quantidade = int(request.form["quantidade"])
        produto = db.get_or_404(Produto, int(request.form["produto_id"]))
        saida = EstoqueSaida(
            produto_id=produto.id,
            data=parse_date(request.form["data"]),
            destino=request.form.get("destino", ""),
            motivo=request.form.get("motivo", "venda"),
            quantidade=quantidade,
            responsavel=request.form.get("responsavel", ""),
            observacao=request.form.get("observacao", ""),
        )
        produto.quantidade = (produto.quantidade or 0) - quantidade
        db.session.add(saida)
        db.session.commit()
        registrar_auditoria("criacao", "estoque", f"Saída de {quantidade} un. de {produto.nome}")
        flash("Saída registrada com sucesso.", "success")
        return redirect(url_for("estoque_saida_listar"))
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template("estoque/saida_form.html", saida=None, produtos=produtos)


@app.route("/estoque/saida/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def estoque_saida_editar(id):
    saida = db.get_or_404(EstoqueSaida, id)
    if request.method == "POST":
        produto_antigo = db.session.get(Produto, saida.produto_id)
        if produto_antigo:
            produto_antigo.quantidade = (produto_antigo.quantidade or 0) + saida.quantidade

        saida.produto_id = int(request.form["produto_id"])
        saida.data = parse_date(request.form["data"])
        saida.destino = request.form.get("destino", "")
        saida.motivo = request.form.get("motivo", "venda")
        saida.quantidade = int(request.form["quantidade"])
        saida.responsavel = request.form.get("responsavel", "")
        saida.observacao = request.form.get("observacao", "")

        produto_novo = db.get_or_404(Produto, saida.produto_id)
        produto_novo.quantidade = (produto_novo.quantidade or 0) - saida.quantidade

        db.session.commit()
        registrar_auditoria("edicao", "estoque", f"Saída #{saida.id} atualizada")
        flash("Saída atualizada com sucesso.", "success")
        return redirect(url_for("estoque_saida_listar"))
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template("estoque/saida_form.html", saida=saida, produtos=produtos)


@app.route("/estoque/saida/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def estoque_saida_excluir(id):
    saida = db.get_or_404(EstoqueSaida, id)
    produto = db.session.get(Produto, saida.produto_id)
    if produto:
        produto.quantidade = (produto.quantidade or 0) + saida.quantidade
    db.session.delete(saida)
    db.session.commit()
    registrar_auditoria("exclusao", "estoque", f"Saída #{id} excluída")
    flash("Saída excluída.", "success")
    return redirect(url_for("estoque_saida_listar"))


# ---------------------------------------------------------------------------
# Compras
# ---------------------------------------------------------------------------

def _aplicar_itens_compra(compra, form):
    compra.itens = []
    produto_ids = form.getlist("item_produto_id[]")
    quantidades = form.getlist("item_quantidade[]")
    valores = form.getlist("item_valor_unitario[]")
    total = 0.0
    for produto_id, quantidade, valor in zip(produto_ids, quantidades, valores):
        if not produto_id:
            continue
        qtd = int(quantidade or 0)
        val = float(valor or 0)
        compra.itens.append(CompraItem(produto_id=int(produto_id), quantidade=qtd, valor_unitario=val))
        total += qtd * val
    compra.valor_total = total


def _aplicar_duplicatas_compra(compra, form):
    compra.duplicatas = []
    valores = form.getlist("duplicata_valor[]")
    vencimentos = form.getlist("duplicata_vencimento[]")
    for valor, vencimento in zip(valores, vencimentos):
        if not vencimento:
            continue
        compra.duplicatas.append(Duplicata(valor=float(valor or 0), data_vencimento=parse_date(vencimento)))


@app.route("/compras")
@login_required
def compras_listar():
    q = request.args.get("q", "").strip()

    query = Compra.query.join(Fornecedor)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Compra.numero_nota.ilike(like), Fornecedor.nome.ilike(like)))

    compras, pagination = paginar_ou_todos(query, Compra.data_emissao.desc())
    return render_template("compras/list.html", compras=compras, pagination=pagination)


@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
@admin_required
def compras_nova():
    if request.method == "POST":
        compra = Compra(
            numero_nota=request.form["numero_nota"].strip(),
            fornecedor_id=int(request.form["fornecedor_id"]),
            data_emissao=parse_date(request.form["data_emissao"]),
            observacao=request.form.get("observacao", ""),
        )
        _aplicar_itens_compra(compra, request.form)
        _aplicar_duplicatas_compra(compra, request.form)
        db.session.add(compra)
        db.session.commit()
        registrar_auditoria("criacao", "compras", f"Compra #{compra.numero_nota} registrada")
        flash("Compra registrada com sucesso.", "success")
        return redirect(url_for("compras_listar"))
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template("compras/form.html", compra=None, fornecedores=fornecedores, produtos=produtos)


@app.route("/compras/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def compras_editar(id):
    compra = db.get_or_404(Compra, id)
    if request.method == "POST":
        compra.numero_nota = request.form["numero_nota"].strip()
        compra.fornecedor_id = int(request.form["fornecedor_id"])
        compra.data_emissao = parse_date(request.form["data_emissao"])
        compra.observacao = request.form.get("observacao", "")
        _aplicar_itens_compra(compra, request.form)
        _aplicar_duplicatas_compra(compra, request.form)
        db.session.commit()
        registrar_auditoria("edicao", "compras", f"Compra #{compra.numero_nota} atualizada")
        flash("Compra atualizada com sucesso.", "success")
        return redirect(url_for("compras_listar"))
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template("compras/form.html", compra=compra, fornecedores=fornecedores, produtos=produtos)


@app.route("/compras/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def compras_excluir(id):
    compra = db.get_or_404(Compra, id)
    numero = compra.numero_nota
    db.session.delete(compra)
    db.session.commit()
    registrar_auditoria("exclusao", "compras", f"Compra #{numero} excluída")
    flash("Compra excluída.", "success")
    return redirect(url_for("compras_listar"))


# ---------------------------------------------------------------------------
# Patrimônio
# ---------------------------------------------------------------------------

@app.route("/patrimonio")
@login_required
def patrimonio_listar():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = Patrimonio.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Patrimonio.codigo.ilike(like), Patrimonio.descricao.ilike(like)))
    if status:
        query = query.filter(Patrimonio.status == status)

    patrimonios, pagination = paginar_ou_todos(query, Patrimonio.codigo)
    return render_template("patrimonio/list.html", patrimonios=patrimonios, pagination=pagination)


@app.route("/patrimonio/novo", methods=["GET", "POST"])
@login_required
@admin_required
def patrimonio_novo():
    if request.method == "POST":
        bem = Patrimonio(
            codigo=request.form["codigo"].strip(),
            descricao=request.form["descricao"].strip(),
            categoria=request.form.get("categoria", ""),
            data_aquisicao=parse_date(request.form.get("data_aquisicao")),
            valor=float(request.form.get("valor") or 0),
            localizacao=request.form.get("localizacao", ""),
            responsavel_id=request.form.get("responsavel_id") or None,
            estado_conservacao=request.form.get("estado_conservacao", "bom"),
            status=request.form.get("status", "ativo"),
            observacao=request.form.get("observacao", ""),
        )
        db.session.add(bem)
        db.session.commit()
        registrar_auditoria("criacao", "patrimonio", f"Bem {bem.codigo} cadastrado")
        flash("Bem patrimonial cadastrado com sucesso.", "success")
        return redirect(url_for("patrimonio_listar"))
    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    return render_template("patrimonio/form.html", bem=None, funcionarios=funcionarios)


@app.route("/patrimonio/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def patrimonio_editar(id):
    bem = db.get_or_404(Patrimonio, id)
    if request.method == "POST":
        bem.codigo = request.form["codigo"].strip()
        bem.descricao = request.form["descricao"].strip()
        bem.categoria = request.form.get("categoria", "")
        bem.data_aquisicao = parse_date(request.form.get("data_aquisicao"))
        bem.valor = float(request.form.get("valor") or 0)
        bem.localizacao = request.form.get("localizacao", "")
        bem.responsavel_id = request.form.get("responsavel_id") or None
        bem.estado_conservacao = request.form.get("estado_conservacao", "bom")
        bem.status = request.form.get("status", "ativo")
        bem.observacao = request.form.get("observacao", "")
        db.session.commit()
        registrar_auditoria("edicao", "patrimonio", f"Bem {bem.codigo} atualizado")
        flash("Bem patrimonial atualizado com sucesso.", "success")
        return redirect(url_for("patrimonio_listar"))
    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    return render_template("patrimonio/form.html", bem=bem, funcionarios=funcionarios)


@app.route("/patrimonio/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def patrimonio_excluir(id):
    bem = db.get_or_404(Patrimonio, id)
    codigo = bem.codigo
    db.session.delete(bem)
    db.session.commit()
    registrar_auditoria("exclusao", "patrimonio", f"Bem {codigo} excluído")
    flash("Bem patrimonial excluído.", "success")
    return redirect(url_for("patrimonio_listar"))


# ---------------------------------------------------------------------------
# Fornecedores
# ---------------------------------------------------------------------------

@app.route("/fornecedores")
@login_required
def fornecedores_listar():
    q = request.args.get("q", "").strip()

    query = Fornecedor.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Fornecedor.nome.ilike(like), Fornecedor.documento.ilike(like)))

    fornecedores, pagination = paginar_ou_todos(query, Fornecedor.nome)
    return render_template("fornecedores/list.html", fornecedores=fornecedores, pagination=pagination)


@app.route("/fornecedores/novo", methods=["GET", "POST"])
@login_required
def fornecedores_novo():
    if request.method == "POST":
        fornecedor = Fornecedor(
            nome=request.form["nome"].strip(),
            documento=request.form.get("documento", ""),
            categoria=request.form.get("categoria", ""),
            contato=request.form.get("contato", ""),
            telefone=request.form.get("telefone", ""),
            email=request.form.get("email", ""),
            endereco=request.form.get("endereco", ""),
            status=request.form.get("status", "ativo"),
            observacao=request.form.get("observacao", ""),
        )
        db.session.add(fornecedor)
        db.session.commit()
        registrar_auditoria("criacao", "fornecedores", f"Fornecedor {fornecedor.nome} cadastrado")
        flash("Fornecedor cadastrado com sucesso.", "success")
        return redirect(url_for("fornecedores_listar"))
    return render_template("fornecedores/form.html", fornecedor=None)


@app.route("/fornecedores/<int:id>/editar", methods=["GET", "POST"])
@login_required
def fornecedores_editar(id):
    fornecedor = db.get_or_404(Fornecedor, id)
    if request.method == "POST":
        fornecedor.nome = request.form["nome"].strip()
        fornecedor.documento = request.form.get("documento", "")
        fornecedor.categoria = request.form.get("categoria", "")
        fornecedor.contato = request.form.get("contato", "")
        fornecedor.telefone = request.form.get("telefone", "")
        fornecedor.email = request.form.get("email", "")
        fornecedor.endereco = request.form.get("endereco", "")
        fornecedor.status = request.form.get("status", "ativo")
        fornecedor.observacao = request.form.get("observacao", "")
        db.session.commit()
        registrar_auditoria("edicao", "fornecedores", f"Fornecedor {fornecedor.nome} atualizado")
        flash("Fornecedor atualizado com sucesso.", "success")
        return redirect(url_for("fornecedores_listar"))
    return render_template("fornecedores/form.html", fornecedor=fornecedor)


@app.route("/fornecedores/<int:id>/excluir", methods=["POST"])
@login_required
def fornecedores_excluir(id):
    fornecedor = db.get_or_404(Fornecedor, id)
    nome = fornecedor.nome
    db.session.delete(fornecedor)
    db.session.commit()
    registrar_auditoria("exclusao", "fornecedores", f"Fornecedor {nome} excluído")
    flash("Fornecedor excluído.", "success")
    return redirect(url_for("fornecedores_listar"))


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------

@app.route("/funcionarios")
@login_required
def funcionarios_listar():
    q = request.args.get("q", "").strip()
    departamento = request.args.get("departamento", "").strip()

    query = Funcionario.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Funcionario.nome.ilike(like), Funcionario.cpf.ilike(like)))
    if departamento:
        query = query.filter(Funcionario.departamento == departamento)

    funcionarios, pagination = paginar_ou_todos(query, Funcionario.nome)
    departamentos = [d[0] for d in db.session.query(Funcionario.departamento).distinct() if d[0]]
    return render_template(
        "funcionarios/list.html", funcionarios=funcionarios, pagination=pagination, departamentos=departamentos
    )


@app.route("/funcionarios/novo", methods=["GET", "POST"])
@login_required
def funcionarios_novo():
    if request.method == "POST":
        funcionario = Funcionario(
            nome=request.form["nome"].strip(),
            cpf=request.form["cpf"].strip(),
            cargo=request.form.get("cargo", ""),
            departamento=request.form.get("departamento", ""),
            data_admissao=parse_date(request.form.get("data_admissao")),
            telefone=request.form.get("telefone", ""),
            email=request.form.get("email", ""),
            nivel_acesso=request.form.get("nivel_acesso", "operador"),
            status=request.form.get("status", "ativo"),
        )
        db.session.add(funcionario)
        db.session.commit()
        registrar_auditoria("criacao", "funcionarios", f"Funcionário {funcionario.nome} cadastrado")
        flash("Funcionário cadastrado com sucesso.", "success")
        return redirect(url_for("funcionarios_listar"))
    return render_template("funcionarios/form.html", funcionario=None)


@app.route("/funcionarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
def funcionarios_editar(id):
    funcionario = db.get_or_404(Funcionario, id)
    if request.method == "POST":
        funcionario.nome = request.form["nome"].strip()
        funcionario.cpf = request.form["cpf"].strip()
        funcionario.cargo = request.form.get("cargo", "")
        funcionario.departamento = request.form.get("departamento", "")
        funcionario.data_admissao = parse_date(request.form.get("data_admissao"))
        funcionario.telefone = request.form.get("telefone", "")
        funcionario.email = request.form.get("email", "")
        funcionario.nivel_acesso = request.form.get("nivel_acesso", "operador")
        funcionario.status = request.form.get("status", "ativo")
        db.session.commit()
        registrar_auditoria("edicao", "funcionarios", f"Funcionário {funcionario.nome} atualizado")
        flash("Funcionário atualizado com sucesso.", "success")
        return redirect(url_for("funcionarios_listar"))
    return render_template("funcionarios/form.html", funcionario=funcionario)


@app.route("/funcionarios/<int:id>/excluir", methods=["POST"])
@login_required
def funcionarios_excluir(id):
    funcionario = db.get_or_404(Funcionario, id)
    nome = funcionario.nome
    db.session.delete(funcionario)
    db.session.commit()
    registrar_auditoria("exclusao", "funcionarios", f"Funcionário {nome} excluído")
    flash("Funcionário excluído.", "success")
    return redirect(url_for("funcionarios_listar"))


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

@app.route("/alunos")
@login_required
def alunos_listar():
    q = request.args.get("q", "").strip()
    serie = request.args.get("serie", "").strip()

    query = Aluno.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Aluno.nome.ilike(like), Aluno.cpf.ilike(like)))
    if serie:
        query = query.filter(Aluno.serie == serie)

    alunos, pagination = paginar_ou_todos(query, Aluno.nome)
    return render_template(
        "alunos/list.html", alunos=alunos, pagination=pagination, series=SERIES_CHOICES
    )


@app.route("/alunos/novo", methods=["GET", "POST"])
@login_required
def alunos_novo():
    if request.method == "POST":
        aluno = Aluno(
            nome=request.form["nome"].strip(),
            data_nascimento=parse_date(request.form.get("data_nascimento")),
            cpf=request.form.get("cpf", "").strip(),
            rg=request.form.get("rg", "").strip(),
            sexo=request.form.get("sexo", ""),
            serie=request.form["serie"],
            turma=request.form.get("turma", "").strip(),
            turno=request.form.get("turno", ""),
            endereco=request.form.get("endereco", "").strip(),
            telefone=request.form.get("telefone", "").strip(),
            email=request.form.get("email", "").strip(),
            responsavel_nome=request.form.get("responsavel_nome", "").strip(),
            responsavel_parentesco=request.form.get("responsavel_parentesco", "").strip(),
            responsavel_telefone=request.form.get("responsavel_telefone", "").strip(),
            responsavel_email=request.form.get("responsavel_email", "").strip(),
            responsavel_financeiro_nome=request.form.get("responsavel_financeiro_nome", "").strip(),
            responsavel_financeiro_parentesco=request.form.get("responsavel_financeiro_parentesco", "").strip(),
            responsavel_financeiro_telefone=request.form.get("responsavel_financeiro_telefone", "").strip(),
            responsavel_financeiro_email=request.form.get("responsavel_financeiro_email", "").strip(),
            data_matricula=parse_date(request.form.get("data_matricula")) or datetime.now().date(),
            status=request.form.get("status", "ativo"),
            observacao=request.form.get("observacao", ""),
        )
        db.session.add(aluno)
        db.session.commit()
        registrar_auditoria("criacao", "alunos", f"Aluno {aluno.nome} cadastrado")
        flash("Aluno cadastrado com sucesso.", "success")
        return redirect(url_for("alunos_listar"))
    return render_template("alunos/form.html", aluno=None, series=SERIES_CHOICES)


@app.route("/alunos/<int:id>/editar", methods=["GET", "POST"])
@login_required
def alunos_editar(id):
    aluno = db.get_or_404(Aluno, id)
    if request.method == "POST":
        aluno.nome = request.form["nome"].strip()
        aluno.data_nascimento = parse_date(request.form.get("data_nascimento"))
        aluno.cpf = request.form.get("cpf", "").strip()
        aluno.rg = request.form.get("rg", "").strip()
        aluno.sexo = request.form.get("sexo", "")
        aluno.serie = request.form["serie"]
        aluno.turma = request.form.get("turma", "").strip()
        aluno.turno = request.form.get("turno", "")
        aluno.endereco = request.form.get("endereco", "").strip()
        aluno.telefone = request.form.get("telefone", "").strip()
        aluno.email = request.form.get("email", "").strip()
        aluno.responsavel_nome = request.form.get("responsavel_nome", "").strip()
        aluno.responsavel_parentesco = request.form.get("responsavel_parentesco", "").strip()
        aluno.responsavel_telefone = request.form.get("responsavel_telefone", "").strip()
        aluno.responsavel_email = request.form.get("responsavel_email", "").strip()
        aluno.responsavel_financeiro_nome = request.form.get("responsavel_financeiro_nome", "").strip()
        aluno.responsavel_financeiro_parentesco = request.form.get("responsavel_financeiro_parentesco", "").strip()
        aluno.responsavel_financeiro_telefone = request.form.get("responsavel_financeiro_telefone", "").strip()
        aluno.responsavel_financeiro_email = request.form.get("responsavel_financeiro_email", "").strip()
        aluno.data_matricula = parse_date(request.form.get("data_matricula"))
        aluno.status = request.form.get("status", "ativo")
        aluno.observacao = request.form.get("observacao", "")
        db.session.commit()
        registrar_auditoria("edicao", "alunos", f"Aluno {aluno.nome} atualizado")
        flash("Aluno atualizado com sucesso.", "success")
        return redirect(url_for("alunos_listar"))
    return render_template("alunos/form.html", aluno=aluno, series=SERIES_CHOICES)


@app.route("/alunos/<int:id>/excluir", methods=["POST"])
@login_required
def alunos_excluir(id):
    aluno = db.get_or_404(Aluno, id)
    nome = aluno.nome
    db.session.delete(aluno)
    db.session.commit()
    registrar_auditoria("exclusao", "alunos", f"Aluno {nome} excluído")
    flash("Aluno excluído.", "success")
    return redirect(url_for("alunos_listar"))


# ---------------------------------------------------------------------------
# Inscrições
# ---------------------------------------------------------------------------

@app.route("/inscricoes")
@login_required
def inscricoes_listar():
    q = request.args.get("q", "").strip()
    ano_letivo = request.args.get("ano_letivo", "").strip()
    status = request.args.get("status", "").strip()

    query = Inscricao.query.join(Aluno)
    if q:
        query = query.filter(Aluno.nome.ilike(f"%{q}%"))
    if ano_letivo:
        query = query.filter(Inscricao.ano_letivo == ano_letivo)
    if status:
        query = query.filter(Inscricao.status == status)

    inscricoes, pagination = paginar_ou_todos(query, Inscricao.data_inscricao.desc())
    anos_letivos = [a[0] for a in db.session.query(Inscricao.ano_letivo).distinct() if a[0]]
    return render_template(
        "inscricoes/list.html", inscricoes=inscricoes, pagination=pagination, anos_letivos=anos_letivos
    )


@app.route("/inscricoes/nova", methods=["GET", "POST"])
@login_required
def inscricoes_nova():
    if request.method == "POST":
        inscricao = Inscricao(
            aluno_id=int(request.form["aluno_id"]),
            ano_letivo=request.form["ano_letivo"].strip(),
            serie=request.form["serie"],
            turma=request.form.get("turma", "").strip(),
            turno=request.form.get("turno", ""),
            data_inscricao=parse_date(request.form["data_inscricao"]),
            status=request.form.get("status", "ativa"),
            observacao=request.form.get("observacao", ""),
        )
        db.session.add(inscricao)
        db.session.commit()
        registrar_auditoria(
            "criacao", "inscricoes", f"Inscrição de {inscricao.aluno_nome} em {inscricao.ano_letivo} registrada"
        )
        flash("Inscrição registrada com sucesso.", "success")
        return redirect(url_for("inscricoes_listar"))
    alunos = Aluno.query.order_by(Aluno.nome).all()
    return render_template("inscricoes/form.html", inscricao=None, alunos=alunos, series=SERIES_CHOICES)


@app.route("/inscricoes/<int:id>/editar", methods=["GET", "POST"])
@login_required
def inscricoes_editar(id):
    inscricao = db.get_or_404(Inscricao, id)
    if request.method == "POST":
        inscricao.aluno_id = int(request.form["aluno_id"])
        inscricao.ano_letivo = request.form["ano_letivo"].strip()
        inscricao.serie = request.form["serie"]
        inscricao.turma = request.form.get("turma", "").strip()
        inscricao.turno = request.form.get("turno", "")
        inscricao.data_inscricao = parse_date(request.form["data_inscricao"])
        inscricao.status = request.form.get("status", "ativa")
        inscricao.observacao = request.form.get("observacao", "")
        db.session.commit()
        registrar_auditoria("edicao", "inscricoes", f"Inscrição #{inscricao.id} atualizada")
        flash("Inscrição atualizada com sucesso.", "success")
        return redirect(url_for("inscricoes_listar"))
    alunos = Aluno.query.order_by(Aluno.nome).all()
    return render_template("inscricoes/form.html", inscricao=inscricao, alunos=alunos, series=SERIES_CHOICES)


@app.route("/inscricoes/<int:id>/excluir", methods=["POST"])
@login_required
def inscricoes_excluir(id):
    inscricao = db.get_or_404(Inscricao, id)
    db.session.delete(inscricao)
    db.session.commit()
    registrar_auditoria("exclusao", "inscricoes", f"Inscrição #{id} excluída")
    flash("Inscrição excluída.", "success")
    return redirect(url_for("inscricoes_listar"))


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------

@app.route("/usuarios")
@login_required
@admin_required
def usuarios_listar():
    q = request.args.get("q", "").strip()
    perfil = request.args.get("perfil", "").strip()

    query = Usuario.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Usuario.nome.ilike(like), Usuario.login.ilike(like)))
    if perfil:
        query = query.filter(Usuario.perfil == perfil)

    usuarios, pagination = paginar_ou_todos(query, Usuario.nome)
    return render_template("usuarios/list.html", usuarios=usuarios, pagination=pagination)


@app.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_required
def usuarios_novo():
    if request.method == "POST":
        usuario = Usuario(
            nome=request.form["nome"].strip(),
            login=request.form["login"].strip(),
            email=request.form["email"].strip(),
            perfil=request.form.get("perfil", "operador"),
            status=request.form.get("status", "ativo"),
        )
        usuario.set_senha(request.form["senha"])
        db.session.add(usuario)
        db.session.commit()
        registrar_auditoria("criacao", "usuarios", f"Usuário {usuario.login} cadastrado")
        flash("Usuário cadastrado com sucesso.", "success")
        return redirect(url_for("usuarios_listar"))
    return render_template("usuarios/form.html", usuario=None)


@app.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def usuarios_editar(id):
    usuario = db.get_or_404(Usuario, id)
    if request.method == "POST":
        usuario.nome = request.form["nome"].strip()
        usuario.login = request.form["login"].strip()
        usuario.email = request.form["email"].strip()
        if usuario.id != current_user.id:
            usuario.perfil = request.form.get("perfil", "operador")
        usuario.status = request.form.get("status", "ativo")
        senha = request.form.get("senha", "").strip()
        if senha:
            usuario.set_senha(senha)
        db.session.commit()
        registrar_auditoria("edicao", "usuarios", f"Usuário {usuario.login} atualizado")
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("usuarios_listar"))
    return render_template("usuarios/form.html", usuario=usuario)


@app.route("/usuarios/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def usuarios_excluir(id):
    if id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("usuarios_listar"))
    usuario = db.get_or_404(Usuario, id)
    login_nome = usuario.login
    db.session.delete(usuario)
    db.session.commit()
    registrar_auditoria("exclusao", "usuarios", f"Usuário {login_nome} excluído")
    flash("Usuário excluído.", "success")
    return redirect(url_for("usuarios_listar"))


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------

def _query_auditoria(args):
    q = args.get("q", "").strip()
    modulo = args.get("modulo", "").strip()
    acao = args.get("acao", "").strip()
    data_inicio = args.get("data_inicio", "")
    data_fim = args.get("data_fim", "")

    query = Auditoria.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Auditoria.usuario.ilike(like), Auditoria.descricao.ilike(like)))
    if modulo:
        query = query.filter(Auditoria.modulo == modulo)
    if acao:
        query = query.filter(Auditoria.acao == acao)
    if data_inicio:
        query = query.filter(Auditoria.data_hora >= parse_date(data_inicio))
    if data_fim:
        query = query.filter(Auditoria.data_hora < parse_date(data_fim) + timedelta(days=1))
    return query


@app.route("/auditoria")
@login_required
@admin_required
def auditoria_listar():
    logs, pagination = paginar_ou_todos(_query_auditoria(request.args), Auditoria.data_hora.desc())
    return render_template("auditoria/list.html", logs=logs, pagination=pagination)


def _csv_seguro(valor):
    """Evita CSV Injection: neutraliza valores que o Excel/LibreOffice
    interpretaria como fórmula (=, +, -, @) prefixando com um apóstrofo."""
    texto = str(valor) if valor is not None else ""
    if texto and texto[0] in ("=", "+", "-", "@"):
        return "'" + texto
    return texto


@app.route("/auditoria/exportar")
@login_required
@admin_required
def auditoria_exportar():
    logs = _query_auditoria(request.args).order_by(Auditoria.data_hora.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Data/Hora", "Usuário", "Ação", "Módulo", "Descrição", "IP"])
    for log in logs:
        writer.writerow([_csv_seguro(v) for v in (log.data_hora, log.usuario, log.acao, log.modulo, log.descricao, log.ip)])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def seed_admin():
    if Usuario.query.count() == 0:
        admin = Usuario(nome="Administrador", login="admin", email="admin@zera.local", perfil="admin", status="ativo")
        admin.set_senha("admin123")
        db.session.add(admin)
        db.session.commit()


# Mesmas listas da aba "Categorias" da planilha de fluxo de caixa escolar.
CATEGORIAS_FINANCEIRAS_PADRAO = {
    ("receita", "fixa"): [
        "Mensalidades - Educação Infantil",
        "Mensalidades - Fundamental I",
        "Mensalidade Contraturno",
        "Diária Contraturno",
        "Taxa de Matrícula",
        "Taxa de Materias",
        "Uniformes",
        "Ballet",
    ],
    ("receita", "variavel"): [
        "Eventos e Festas Escolares",
        "Passeios e Excursões",
        "Colônia de Férias",
        "Cursos e Atividades Extracurriculares",
        "Multas e Juros por Atraso",
        "Segunda Via de Documentos",
        "Aluguel de Espaço/Quadra",
        "Doações e Patrocínios",
    ],
    ("despesa", "fixa"): [
        "Folha de Pagamento - Professores",
        "Folha de Pagamento - Coordenação/Direção",
        "Folha de Pagamento - Administrativo/Apoio",
        "Encargos Trabalhistas (INSS/FGTS)",
        "Aluguel do Imóvel + IPTU",
        "Folha de Pagamento - Auxiliar de Desenvolvimento/Estágio",
        "Água e Esgoto",
        "Energia Elétrica",
        "Internet e Telefonia",
        "Clip Escola",
        "Mídias Digitais e Design",
        "Ifood Benefícios",
        "Controle de Pragas",
        "Honorários Contábeis",
        "Little Kickers",
    ],
    ("despesa", "variavel"): [
        "Material Didático e Pedagógico",
        "Material de Limpeza e Higiene",
        "Material de Escritório",
        "Alimentação Contraturno",
        "Manutenção e Reparos Prediais",
        "Eventos e Festas Escolares",
        "Passeios e Excursões",
        "Marketing e Publicidade",
        "Capacitação e Formação de Professores",
        "Uniformes e Brindes",
        "Brinquedos e Material Pedagógico (Infantil)",
        "Despesas Jurídicas e Cartoriais",
        "Impostos e Taxas Municipais",
        "Serviços de Terceiros/Freelancers",
        "Equipamentos - Patrimônio",
        "Água mineral",
    ],
}


def seed_categorias_financeiras():
    if CategoriaFinanceira.query.count() == 0:
        for (tipo, natureza), nomes in CATEGORIAS_FINANCEIRAS_PADRAO.items():
            for nome in nomes:
                db.session.add(CategoriaFinanceira(tipo=tipo, natureza=natureza, nome=nome))
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_admin()
    seed_categorias_financeiras()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    use_https = os.environ.get("USE_HTTPS", "false").lower() == "true"
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    ssl_context = "adhoc" if use_https else None
    app.run(debug=debug, host=host, port=port, ssl_context=ssl_context)
