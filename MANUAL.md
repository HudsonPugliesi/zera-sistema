# Manual do Sistema Zera

Guia de uso do sistema de gestão escolar: estoque, patrimônio, compras,
financeiro, alunos e administração. Para instruções de instalação, veja o
[README](README.md).

## Sumário

1. [Acesso ao sistema](#1-acesso-ao-sistema)
2. [Navegação](#2-navegação)
3. [Home](#3-home)
4. [Dashboard Financeiro](#4-dashboard-financeiro)
5. [Financeiro — Lançamentos](#5-financeiro--lançamentos)
6. [Financeiro — Categorias](#6-financeiro--categorias)
7. [Produtos](#7-produtos)
8. [Estoque — Entrada](#8-estoque--entrada)
9. [Estoque — Saída](#9-estoque--saída)
10. [Nota Fiscal (Compras)](#10-nota-fiscal-compras)
11. [Patrimônio](#11-patrimônio)
12. [Fornecedores](#12-fornecedores)
13. [Funcionários](#13-funcionários)
14. [Alunos](#14-alunos)
15. [Inscrição](#15-inscrição)
16. [Usuários e perfis de acesso](#16-usuários-e-perfis-de-acesso)
17. [Auditoria](#17-auditoria)
18. [Perguntas frequentes](#18-perguntas-frequentes)

---

## 1. Acesso ao sistema

Abra o endereço do sistema no navegador — você cai direto na tela de
**Login**. Entre com usuário e senha cadastrados.

Usuário administrador criado na primeira execução:

- **Usuário:** `admin`
- **Senha:** `admin123`

> Troque essa senha assim que possível em **Usuários** (seção 16).

Ao sair, use **🚪 Sair** no rodapé do menu lateral.

## 2. Navegação

O menu lateral (esquerda no desktop, ícone ☰ no celular) é dividido em
grupos:

| Grupo | Itens |
|---|---|
| — | Home, Dashboard |
| **Financeiro** | Lançamentos, Categorias |
| — | Produtos, Entrada de Estoque, Saída de Estoque, Nota Fiscal, Patrimônio, Fornecedores, Funcionários |
| **Escola** | Alunos, Inscrição |
| **Administração** | Usuários, Auditoria |

No canto superior direito ficam o alternador de tema claro/escuro (🌙/☀️)
e o nome do usuário logado.

Praticamente toda tela de listagem tem os mesmos recursos:

- **Busca/filtros** no topo (por nome, período, tipo etc.) — clique em
  **Filtrar** para aplicar.
- **Paginação** no rodapé da tabela.
- Botões **Editar** e **Excluir** em cada linha (exclusão sempre pede
  confirmação).
- Toda ação de criar, editar ou excluir fica registrada em **Auditoria**.

## 3. Home

Página em branco, reservada para a logo do colégio. Não tem conteúdo
funcional — é só a tela que aparece primeiro ao entrar no sistema.

## 4. Dashboard Financeiro

Painel com a visão geral do ano, no mesmo formato da planilha de fluxo de
caixa:

- **Seletor de ano** no canto superior direito do painel — troca o ano
  exibido em toda a tela.
- **4 indicadores (KPIs):** Total de Receitas, Total de Despesas, Saldo
  do Ano e Saldo Acumulado Final.
- **Resumo Mensal:** tabela com receitas, despesas, saldo do mês e saldo
  acumulado, mês a mês. Células sem movimento aparecem como "-".
- **Gráficos:** Receitas x Despesas por mês (barras) e Evolução do Saldo
  Acumulado (linha).

De onde vêm os números:

- **Receitas** = soma dos lançamentos do tipo "Receita" cadastrados em
  **Financeiro → Lançamentos**.
- **Despesas** = lançamentos do tipo "Despesa" **+ o valor de todas as
  Compras (Nota Fiscal) + Entradas de Estoque + itens de Patrimônio
  adquiridos no ano** — essas três origens entram automaticamente, sem
  precisar lançar de novo.

O mês usado para contar cada valor é o mês da **data de pagamento**
(se já foi pago/recebido) ou da **data de vencimento** (se ainda está
pendente) — ou seja, um lançamento pendente já entra no fluxo projetado
do mês em que vence.

## 5. Financeiro — Lançamentos

Cadastro de receitas e despesas que alimentam o Dashboard.

**Campos do lançamento:**

| Campo | Descrição |
|---|---|
| Tipo | Receita ou Despesa |
| Natureza | Fixa (recorrente, ex.: mensalidade, aluguel) ou Variável (esporádica, ex.: evento, manutenção) |
| Categoria | Lista muda automaticamente conforme Tipo + Natureza escolhidos (vem de **Financeiro → Categorias**) |
| Descrição | Texto livre, opcional |
| Valor (R$) | Valor do lançamento |
| Data de vencimento | Obrigatória |
| Data de pagamento/recebimento | Deixe em branco se ainda não ocorreu |

**Status**, calculado automaticamente (não é preenchido manualmente):

- **Pago** / **Recebido** — já tem data de pagamento preenchida.
- **Atrasado** — venceu e a data de pagamento continua em branco.
- **Pendente** — ainda não venceu e não foi pago.

Use os filtros da listagem (busca, tipo, natureza, período) para
encontrar lançamentos rapidamente. Editar ou excluir um lançamento
atualiza o Dashboard na próxima vez que a tela for aberta.

## 6. Financeiro — Categorias

Gerencia as quatro listas usadas no formulário de Lançamentos:
**Receitas Fixas**, **Receitas Variáveis**, **Despesas Fixas** e
**Despesas Variáveis** — já vêm pré-cadastradas com categorias comuns de
escola (mensalidades, folha de pagamento, material didático etc.).

- Para **adicionar**: digite o nome no campo abaixo da coluna certa e
  clique em **+**.
- Para **remover**: clique em **Remover** ao lado do item.

Se remover uma categoria que já foi usada em algum lançamento antigo, o
lançamento continua mostrando o nome antigo normalmente — só deixa de
aparecer como opção para novos lançamentos.

## 7. Produtos

Cadastro de itens de estoque (código, nome, categoria, unidade, preço de
custo/venda, quantidade, estoque mínimo, fornecedor, status).

- O **código** é sugerido automaticamente ao criar um produto novo, mas
  pode ser alterado depois na edição.
- **Estoque mínimo** é usado para o card de "estoque baixo" e para
  destacar produtos em situação crítica.
- A **quantidade** é ajustada automaticamente pelas telas de Entrada e
  Saída de Estoque — normalmente não precisa editá-la à mão.

## 8. Estoque — Entrada

Registra a chegada de mercadorias: produto, data, fornecedor, nota
fiscal, quantidade, valor unitário (o valor total é calculado
sozinho) e responsável. Ao salvar, a quantidade do produto é somada
automaticamente ao estoque atual.

O **valor total de cada entrada conta como despesa automática no
Dashboard Financeiro**, no mês da data de entrada.

## 9. Estoque — Saída

Registra a baixa de mercadorias: produto, data, quantidade, destino/
setor, motivo (Venda, Uso interno, Perda/avaria, Devolução) e
responsável. Ao salvar, a quantidade do produto é subtraída do estoque
atual. Diferente da Entrada, a Saída não tem valor monetário — não
entra nos totais do Dashboard Financeiro.

## 10. Nota Fiscal (Compras)

Registra uma compra completa de um fornecedor:

- **Dados da nota:** número, fornecedor, data de emissão.
- **Itens da compra:** adicione quantas linhas precisar (produto,
  quantidade, valor unitário) com **+ Adicionar item**.
- **Duplicatas:** parcelas de pagamento da compra (valor e data de
  vencimento), com **+ Adicionar duplicata** — útil para compras
  parceladas.

O **valor total da compra conta como despesa automática no Dashboard
Financeiro**, no mês da data de emissão da nota.

## 11. Patrimônio

Cadastro de bens patrimoniais: código, categoria, descrição, data de
aquisição, valor, localização, responsável (funcionário), estado de
conservação (Novo/Bom/Regular/Ruim) e status (Ativo/Em manutenção/
Baixado).

O **valor de um bem com data de aquisição preenchida conta como despesa
automática no Dashboard Financeiro**, no mês da aquisição.

## 12. Fornecedores

Cadastro de fornecedores: nome, CNPJ/CPF, categoria, contato, telefone,
e-mail, endereço e status. Usado nos formulários de Produtos, Entrada de
Estoque e Nota Fiscal.

## 13. Funcionários

Cadastro de funcionários: nome, CPF, cargo, departamento, data de
admissão, telefone, e-mail, nível de acesso e status. Usado como
responsável em Patrimônio.

## 14. Alunos

Cadastro de alunos: dados pessoais (nome, nascimento, CPF/RG, sexo),
dados escolares (série, turma, turno), contato do aluno e dados do
responsável (nome, parentesco, telefone, e-mail).

## 15. Inscrição

Vincula um aluno já cadastrado a um ano letivo: aluno, ano letivo, data
da inscrição, série, turma, turno e status (Ativa/Concluída/Cancelada).
Um mesmo aluno pode ter uma inscrição por ano letivo.

## 16. Usuários e perfis de acesso

Cadastro de quem pode acessar o sistema: nome, login, e-mail, senha e
**perfil de acesso**:

- **Operador** — uso do dia a dia.
- **Gerente** — mesmo acesso, indicado para quem supervisiona a
  operação.
- **Administrador** — acesso completo, incluindo cadastro de usuários.

Status **Bloqueado** impede o login sem excluir o cadastro. Ao editar um
usuário existente, deixe o campo **Senha** em branco para manter a senha
atual.

> Você não pode excluir o próprio usuário logado.

## 17. Auditoria

Histórico de tudo que acontece no sistema: login/logout e toda criação,
edição ou exclusão em qualquer módulo — com data/hora, usuário, ação,
módulo, descrição e IP.

- Filtre por texto, módulo, ação e período.
- **⬇ Exportar CSV** baixa os registros filtrados para abrir em Excel.

## 18. Perguntas frequentes

**Lancei uma despesa em Lançamentos e ela também aparece via Compras — estou contando em dobro?**
Só se a mesma movimentação for registrada nos dois lugares. Uma compra
lançada em **Nota Fiscal** já entra sozinha no Dashboard; não é preciso
lançá-la de novo em **Financeiro → Lançamentos**.

**Por que uma célula do Resumo Mensal mostra "-"?**
Significa que não houve movimento (valor zero) naquele mês, o mesmo
padrão usado na planilha de fluxo de caixa original.

**Como faço para ver anos anteriores no Dashboard?**
Use o seletor de ano no topo do painel financeiro.

**Removi uma categoria financeira por engano, os lançamentos antigos somem?**
Não. O lançamento mantém o nome da categoria salva nele; ela só some das
opções para novos cadastros.
