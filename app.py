import csv
import io
import os
from datetime import datetime, timedelta

from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect

from models import (
    Aluno,
    Auditoria,
    Compra,
    CompraItem,
    Duplicata,
    EstoqueEntrada,
    EstoqueSaida,
    Fornecedor,
    Funcionario,
    Inscricao,
    Patrimonio,
    Produto,
    SERIES_CHOICES,
    Usuario,
    db,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PER_PAGE = 15

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "zera.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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


@app.context_processor
def inject_now():
    return {"now": datetime.now()}


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


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
        return redirect(url_for("dashboard"))
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
            return redirect(url_for("dashboard"))
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
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    total_produtos = Produto.query.count()
    total_estoque_baixo = Produto.query.filter(Produto.quantidade <= Produto.estoque_minimo).count()
    total_compras = Compra.query.count()
    total_patrimonio = Patrimonio.query.count()
    atividades_recentes = Auditoria.query.order_by(Auditoria.data_hora.desc()).limit(10).all()
    produtos_estoque_baixo = (
        Produto.query.filter(Produto.quantidade <= Produto.estoque_minimo)
        .order_by(Produto.quantidade)
        .limit(5)
        .all()
    )
    return render_template(
        "dashboard.html",
        total_produtos=total_produtos,
        total_estoque_baixo=total_estoque_baixo,
        total_compras=total_compras,
        total_patrimonio=total_patrimonio,
        atividades_recentes=atividades_recentes,
        produtos_estoque_baixo=produtos_estoque_baixo,
    )


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------

@app.route("/produtos")
@login_required
def produtos_listar():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Produto.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Produto.nome.ilike(like), Produto.codigo.ilike(like)))
    if categoria:
        query = query.filter(Produto.categoria == categoria)

    pagination = query.order_by(Produto.nome).paginate(page=page, per_page=PER_PAGE, error_out=False)
    categorias = [c[0] for c in db.session.query(Produto.categoria).distinct() if c[0]]
    return render_template(
        "produtos/list.html", produtos=pagination.items, pagination=pagination, categorias=categorias
    )


def _gerar_codigo_produto():
    max_num = 0
    for (codigo,) in db.session.query(Produto.codigo):
        if codigo and codigo.isdigit():
            max_num = max(max_num, int(codigo))
    return f"{max_num + 1:04d}"


@app.route("/produtos/novo", methods=["GET", "POST"])
@login_required
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
    page = request.args.get("page", 1, type=int)

    query = EstoqueEntrada.query.join(Produto)
    if q:
        query = query.filter(Produto.nome.ilike(f"%{q}%"))
    if data_inicio:
        query = query.filter(EstoqueEntrada.data >= parse_date(data_inicio))
    if data_fim:
        query = query.filter(EstoqueEntrada.data <= parse_date(data_fim))

    pagination = query.order_by(EstoqueEntrada.data.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("estoque/entrada_list.html", entradas=pagination.items, pagination=pagination)


@app.route("/estoque/entrada/nova", methods=["GET", "POST"])
@login_required
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
    page = request.args.get("page", 1, type=int)

    query = EstoqueSaida.query.join(Produto)
    if q:
        query = query.filter(Produto.nome.ilike(f"%{q}%"))
    if motivo:
        query = query.filter(EstoqueSaida.motivo == motivo)

    pagination = query.order_by(EstoqueSaida.data.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("estoque/saida_list.html", saidas=pagination.items, pagination=pagination)


@app.route("/estoque/saida/nova", methods=["GET", "POST"])
@login_required
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
    page = request.args.get("page", 1, type=int)

    query = Compra.query.join(Fornecedor)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Compra.numero_nota.ilike(like), Fornecedor.nome.ilike(like)))

    pagination = query.order_by(Compra.data_emissao.desc()).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("compras/list.html", compras=pagination.items, pagination=pagination)


@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
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
    page = request.args.get("page", 1, type=int)

    query = Patrimonio.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Patrimonio.codigo.ilike(like), Patrimonio.descricao.ilike(like)))
    if status:
        query = query.filter(Patrimonio.status == status)

    pagination = query.order_by(Patrimonio.codigo).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("patrimonio/list.html", patrimonios=pagination.items, pagination=pagination)


@app.route("/patrimonio/novo", methods=["GET", "POST"])
@login_required
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
    page = request.args.get("page", 1, type=int)

    query = Fornecedor.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Fornecedor.nome.ilike(like), Fornecedor.documento.ilike(like)))

    pagination = query.order_by(Fornecedor.nome).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("fornecedores/list.html", fornecedores=pagination.items, pagination=pagination)


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
    page = request.args.get("page", 1, type=int)

    query = Funcionario.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Funcionario.nome.ilike(like), Funcionario.cpf.ilike(like)))
    if departamento:
        query = query.filter(Funcionario.departamento == departamento)

    pagination = query.order_by(Funcionario.nome).paginate(page=page, per_page=PER_PAGE, error_out=False)
    departamentos = [d[0] for d in db.session.query(Funcionario.departamento).distinct() if d[0]]
    return render_template(
        "funcionarios/list.html", funcionarios=pagination.items, pagination=pagination, departamentos=departamentos
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
    page = request.args.get("page", 1, type=int)

    query = Aluno.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Aluno.nome.ilike(like), Aluno.cpf.ilike(like)))
    if serie:
        query = query.filter(Aluno.serie == serie)

    pagination = query.order_by(Aluno.nome).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template(
        "alunos/list.html", alunos=pagination.items, pagination=pagination, series=SERIES_CHOICES
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
    page = request.args.get("page", 1, type=int)

    query = Inscricao.query.join(Aluno)
    if q:
        query = query.filter(Aluno.nome.ilike(f"%{q}%"))
    if ano_letivo:
        query = query.filter(Inscricao.ano_letivo == ano_letivo)
    if status:
        query = query.filter(Inscricao.status == status)

    pagination = query.order_by(Inscricao.data_inscricao.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    anos_letivos = [a[0] for a in db.session.query(Inscricao.ano_letivo).distinct() if a[0]]
    return render_template(
        "inscricoes/list.html", inscricoes=pagination.items, pagination=pagination, anos_letivos=anos_letivos
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
def usuarios_listar():
    q = request.args.get("q", "").strip()
    perfil = request.args.get("perfil", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Usuario.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Usuario.nome.ilike(like), Usuario.login.ilike(like)))
    if perfil:
        query = query.filter(Usuario.perfil == perfil)

    pagination = query.order_by(Usuario.nome).paginate(page=page, per_page=PER_PAGE, error_out=False)
    return render_template("usuarios/list.html", usuarios=pagination.items, pagination=pagination)


@app.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
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
def usuarios_editar(id):
    usuario = db.get_or_404(Usuario, id)
    if request.method == "POST":
        usuario.nome = request.form["nome"].strip()
        usuario.login = request.form["login"].strip()
        usuario.email = request.form["email"].strip()
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
def auditoria_listar():
    page = request.args.get("page", 1, type=int)
    pagination = (
        _query_auditoria(request.args)
        .order_by(Auditoria.data_hora.desc())
        .paginate(page=page, per_page=PER_PAGE, error_out=False)
    )
    return render_template("auditoria/list.html", logs=pagination.items, pagination=pagination)


@app.route("/auditoria/exportar")
@login_required
def auditoria_exportar():
    logs = _query_auditoria(request.args).order_by(Auditoria.data_hora.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Data/Hora", "Usuário", "Ação", "Módulo", "Descrição", "IP"])
    for log in logs:
        writer.writerow([log.data_hora, log.usuario, log.acao, log.modulo, log.descricao, log.ip])
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


with app.app_context():
    db.create_all()
    seed_admin()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
