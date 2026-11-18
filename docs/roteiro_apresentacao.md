# Roteiro da apresentação — Imobiliária Lar Ideal (10 min)

**Dupla:** Davi Barbosa Brito e Igo Patrick

> **Antes de começar:** MySQL rodando, `uvicorn app.main:app --reload` no ar, navegador em
> http://127.0.0.1:8000 **já deslogado**, Workbench aberto com o `sql/script_imobiliaria.sql`
> e a imagem `docs/der.png` em outra aba.

| Tempo | Quem | Assunto |
|---|---|---|
| 0:00–1:30 | Davi | Problema e empresa |
| 1:30–3:30 | Davi | Banco: tabelas, DER, relacionamentos |
| 3:30–7:30 | Igo | Demonstração do sistema (CRUD) |
| 7:30–9:30 | Davi | Como o app conversa com o banco (código + SQL) |
| 9:30–10:00 | Igo | Encerramento |

---

## 1. Problema e empresa (1:30)
- Segmento sorteado: **Imobiliária**. Empresa fictícia: **Imobiliária Lar Ideal**, em Palmas–TO.
- Problema: hoje o controle de clientes, imóveis e contratos fica em planilhas e papel. Isso gera
  imóvel anunciado como disponível que já foi alugado, contrato sem dono e dados duplicados.
- Solução: um sistema web com login em que tudo fica gravado no MySQL, com regras garantidas pelo próprio banco.
- Tecnologias: **Python + FastAPI**, **MySQL**, **Jinja2 + Bootstrap 5** e **PyMySQL** com SQL puro, sem ORM,
  justamente para mostrar os comandos SQL.

## 2. Banco de dados (2:00) — mostrar `docs/der.png`
- Banco **`imobiliaria_lar_ideal_db`** com **4 tabelas**, todas com PK `AUTO_INCREMENT`:
  - `usuarios`: login do sistema; a senha é guardada como **hash SHA-256**, nunca em texto puro.
  - `clientes`: proprietários e interessados (ENUM `tipo`); `cpf` é **UNIQUE**.
  - `imoveis`: FK **`proprietario_id → clientes`** (1 cliente possui N imóveis).
  - `contratos`: FK **`imovel_id → imoveis`** e **`cliente_id → clientes`** (inquilino ou comprador).
- Tipos escolhidos: `DECIMAL(12,2)` para dinheiro (sem erro de arredondamento), `CHAR(11)` para CPF,
  `ENUM` para valores fixos, `DATE` para datas.
- Regras no banco: `ON DELETE RESTRICT` (não deixa apagar um cliente que tem imóvel) e
  `CHECK (data_fim >= data_inicio)`.
- No Workbench, mostrar rapidamente: `CREATE DATABASE`, `CREATE TABLE contratos` (FKs) e os `INSERT`s.

## 3. Demonstração (4:00)
1. **Login** com uma senha errada (aparece o alerta) e depois com `admin / admin123`.
2. **Painel**: contadores, receita de aluguéis ativos e últimos contratos (é um **JOIN** de 4 tabelas).
3. **Clientes**: pesquisar "Maria", cadastrar um cliente novo (**INSERT**), editar o telefone (**UPDATE**).
4. **Imóveis**: filtrar por *Aluguel + Disponível* e cadastrar um imóvel para o cliente recém-criado.
5. **Contratos**: em Imóveis, clicar em "Criar contrato" no imóvel novo. O tipo e o valor já vêm preenchidos.
   Salvar e mostrar que o imóvel passou para **Alugado** automaticamente.
   - Tentar a data de término antes da de início: o sistema mostra a validação.
   - Editar o contrato para **Encerrado**: o imóvel volta para **Disponível**.
6. **Exclusão bloqueada pela FK**: em Clientes, excluir a **Maria Oliveira**. Aparece o alerta
   "possui imóveis ou contratos vinculados", porque o MySQL devolveu o erro 1451.
7. **Exclusão real (DELETE)**: excluir o contrato e o imóvel de teste.
8. **Usuários**: cadastrar um usuário novo e mostrar que a senha não aparece; no banco fica só o hash.

## 4. Comunicação app ↔ banco (2:00) — mostrar o código
- `app/database.py`: `get_cursor()` abre a conexão PyMySQL com os dados do `.env` e faz
  **commit** se der tudo certo ou **rollback** se der erro.
- Fluxo: formulário HTML → `POST` → rota FastAPI (`app/routers/*.py`) → SQL com parâmetros `%s`
  (protege contra SQL Injection) → MySQL → redirect → listagem atualizada.
- Mostrar em `app/routers/contratos.py` a função `criar`: **INSERT** do contrato + **UPDATE** do status do
  imóvel na **mesma transação**. Ou grava os dois, ou nenhum.
- Mostrar o `SELECT ... INNER JOIN` da listagem de contratos.
- Erros do banco (`IntegrityError` 1451/1062) são capturados e viram mensagens amigáveis.

## 5. Encerramento (0:30)
- Requisitos cumpridos: 4 tabelas, PK/FK, ≥ 5 registros por tabela, login com usuário e senha,
  CRUD completo, pesquisa, JOIN e dados gravados de verdade no MySQL.
- Melhorias futuras: senha com bcrypt, níveis de permissão, upload de fotos dos imóveis, relatórios.

---

### Perguntas prováveis do professor
- **Por que FastAPI e não Flask?** Também é um microframework Python, só que mais moderno, com validação
  de formulário e documentação automática em `/docs`. A estrutura é parecida.
- **Por que não usar ORM?** Para os comandos SQL aparecerem explicitamente no código, que é o foco da disciplina.
- **O que acontece se apagar um imóvel com contrato?** O MySQL bloqueia (FK com RESTRICT, erro 1451) e o app mostra o aviso.
- **Como a senha é verificada?** O app calcula o SHA-256 da senha digitada e compara com o `senha_hash` no `SELECT` do login.
- **Por que a tabela `usuarios` não tem FK?** Ela só controla quem acessa o sistema; não participa das regras do negócio.
