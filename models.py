from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

SERIES_CHOICES = [
    "1º Ano - Ensino Fundamental",
    "2º Ano - Ensino Fundamental",
    "3º Ano - Ensino Fundamental",
    "4º Ano - Ensino Fundamental",
    "5º Ano - Ensino Fundamental",
    "6º Ano - Ensino Fundamental",
    "7º Ano - Ensino Fundamental",
    "8º Ano - Ensino Fundamental",
    "9º Ano - Ensino Fundamental",
    "1ª Série - Ensino Médio",
    "2ª Série - Ensino Médio",
    "3ª Série - Ensino Médio",
]


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="operador")
    status = db.Column(db.String(20), nullable=False, default="ativo")
    ultimo_acesso = db.Column(db.DateTime, nullable=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class RastreioMixin:
    """Registra quem criou/alterou o registro e quando, pra exibir na tela
    (além do log completo já existente na Auditoria)."""

    criado_por = db.Column(db.String(150))
    criado_em = db.Column(db.DateTime)
    atualizado_por = db.Column(db.String(150))
    atualizado_em = db.Column(db.DateTime)


class Fornecedor(RastreioMixin, db.Model):
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    documento = db.Column(db.String(30))
    categoria = db.Column(db.String(100))
    contato = db.Column(db.String(150))
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    endereco = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="ativo")
    observacao = db.Column(db.Text)


class Funcionario(RastreioMixin, db.Model):
    __tablename__ = "funcionarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    cargo = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    data_admissao = db.Column(db.Date)
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    nivel_acesso = db.Column(db.String(20), nullable=False, default="operador")
    status = db.Column(db.String(20), nullable=False, default="ativo")


class Produto(RastreioMixin, db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(100))
    unidade = db.Column(db.String(10))
    preco_custo = db.Column(db.Float, default=0)
    preco_venda = db.Column(db.Float, default=0)
    quantidade = db.Column(db.Integer, default=0)
    estoque_minimo = db.Column(db.Integer, default=0)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ativo")
    descricao = db.Column(db.Text)

    fornecedor = db.relationship("Fornecedor")


class EstoqueEntrada(RastreioMixin, db.Model):
    __tablename__ = "estoque_entradas"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=True)
    nota_fiscal = db.Column(db.String(50))
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False, default=0)
    valor_total = db.Column(db.Float, nullable=False, default=0)
    responsavel = db.Column(db.String(150))
    observacao = db.Column(db.Text)

    produto = db.relationship("Produto")
    fornecedor = db.relationship("Fornecedor")

    @property
    def produto_nome(self):
        return self.produto.nome if self.produto else ""

    @property
    def fornecedor_nome(self):
        return self.fornecedor.nome if self.fornecedor else ""


class EstoqueSaida(RastreioMixin, db.Model):
    __tablename__ = "estoque_saidas"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    destino = db.Column(db.String(150))
    motivo = db.Column(db.String(30), nullable=False, default="venda")
    quantidade = db.Column(db.Integer, nullable=False)
    responsavel = db.Column(db.String(150))
    observacao = db.Column(db.Text)

    produto = db.relationship("Produto")

    @property
    def produto_nome(self):
        return self.produto.nome if self.produto else ""


class Compra(RastreioMixin, db.Model):
    __tablename__ = "compras"

    id = db.Column(db.Integer, primary_key=True)
    numero_nota = db.Column(db.String(50), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedores.id"), nullable=False)
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Float, nullable=False, default=0)
    observacao = db.Column(db.Text)

    fornecedor = db.relationship("Fornecedor")
    itens = db.relationship("CompraItem", backref="compra", cascade="all, delete-orphan")
    duplicatas = db.relationship("Duplicata", backref="compra", cascade="all, delete-orphan")

    @property
    def fornecedor_nome(self):
        return self.fornecedor.nome if self.fornecedor else ""


class CompraItem(db.Model):
    __tablename__ = "compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    valor_unitario = db.Column(db.Float, nullable=False, default=0)

    produto = db.relationship("Produto")


class Duplicata(db.Model):
    __tablename__ = "duplicatas"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id"), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0)
    data_vencimento = db.Column(db.Date, nullable=False)


class Patrimonio(RastreioMixin, db.Model):
    __tablename__ = "patrimonios"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100))
    data_aquisicao = db.Column(db.Date, nullable=True)
    valor = db.Column(db.Float, default=0)
    localizacao = db.Column(db.String(150))
    responsavel_id = db.Column(db.Integer, db.ForeignKey("funcionarios.id"), nullable=True)
    estado_conservacao = db.Column(db.String(20), default="bom")
    status = db.Column(db.String(20), nullable=False, default="ativo")
    observacao = db.Column(db.Text)

    responsavel_funcionario = db.relationship("Funcionario")

    @property
    def responsavel(self):
        return self.responsavel_funcionario.nome if self.responsavel_funcionario else ""


class Aluno(RastreioMixin, db.Model):
    __tablename__ = "alunos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(db.String(20))
    rg = db.Column(db.String(20))
    sexo = db.Column(db.String(20))
    serie = db.Column(db.String(50), nullable=False)
    turma = db.Column(db.String(20))
    turno = db.Column(db.String(20))
    endereco = db.Column(db.String(255))
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    responsavel_nome = db.Column(db.String(200))
    responsavel_parentesco = db.Column(db.String(50))
    responsavel_telefone = db.Column(db.String(30))
    responsavel_email = db.Column(db.String(150))
    responsavel_financeiro_nome = db.Column(db.String(200))
    responsavel_financeiro_parentesco = db.Column(db.String(50))
    responsavel_financeiro_telefone = db.Column(db.String(30))
    responsavel_financeiro_email = db.Column(db.String(150))
    data_matricula = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ativo")
    observacao = db.Column(db.Text)

    inscricoes = db.relationship("Inscricao", backref="aluno", cascade="all, delete-orphan")


class Inscricao(RastreioMixin, db.Model):
    __tablename__ = "inscricoes"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    ano_letivo = db.Column(db.String(10), nullable=False)
    serie = db.Column(db.String(50), nullable=False)
    turma = db.Column(db.String(20))
    turno = db.Column(db.String(20))
    data_inscricao = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ativa")
    observacao = db.Column(db.Text)

    @property
    def aluno_nome(self):
        return self.aluno.nome if self.aluno else ""


class CategoriaFinanceira(RastreioMixin, db.Model):
    __tablename__ = "categorias_financeiras"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)  # receita | despesa
    natureza = db.Column(db.String(10), nullable=False)  # fixa | variavel
    nome = db.Column(db.String(150), nullable=False)


class LancamentoFinanceiro(RastreioMixin, db.Model):
    __tablename__ = "lancamentos_financeiros"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)  # receita | despesa
    natureza = db.Column(db.String(10), nullable=False)  # fixa | variavel
    categoria = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.String(255))
    valor = db.Column(db.Float, nullable=False, default=0)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)

    @property
    def status(self):
        if self.data_pagamento:
            return "Recebido" if self.tipo == "receita" else "Pago"
        if self.data_vencimento < date.today():
            return "Atrasado"
        return "Pendente"

    @property
    def data_referencia(self):
        return self.data_pagamento or self.data_vencimento


class Auditoria(db.Model):
    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    usuario = db.Column(db.String(150))
    acao = db.Column(db.String(20))
    modulo = db.Column(db.String(30))
    descricao = db.Column(db.String(500))
    ip = db.Column(db.String(50))
