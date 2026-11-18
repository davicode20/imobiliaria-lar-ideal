-- =========================================================
-- SISTEMA IMOBILIÁRIA LAR IDEAL - Script de criação
-- =========================================================

-- 1) CREATE DATABASE
DROP DATABASE IF EXISTS imobiliaria_lar_ideal_db;
CREATE DATABASE imobiliaria_lar_ideal_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE imobiliaria_lar_ideal_db;

-- 2) CREATE TABLE

-- Usuários do sistema (login)
CREATE TABLE usuarios (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    usuario     VARCHAR(50)  NOT NULL UNIQUE,
    senha_hash  CHAR(64)     NOT NULL,          -- SHA-256 em hexadecimal
    criado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Clientes (proprietários e interessados)
CREATE TABLE clientes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    cpf         CHAR(11)     NOT NULL UNIQUE,
    telefone    VARCHAR(20)  NOT NULL,
    email       VARCHAR(100),
    tipo        ENUM('PROPRIETARIO', 'INTERESSADO', 'AMBOS') NOT NULL,
    criado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Imóveis
CREATE TABLE imoveis (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    proprietario_id  INT           NOT NULL,
    titulo           VARCHAR(100)  NOT NULL,
    tipo             ENUM('CASA', 'APARTAMENTO', 'TERRENO', 'SALA_COMERCIAL') NOT NULL,
    finalidade       ENUM('VENDA', 'ALUGUEL') NOT NULL,
    endereco         VARCHAR(150)  NOT NULL,
    bairro           VARCHAR(80)   NOT NULL,
    cidade           VARCHAR(80)   NOT NULL DEFAULT 'Palmas',
    area_m2          DECIMAL(8,2)  NOT NULL,
    quartos          TINYINT UNSIGNED NOT NULL DEFAULT 0,
    valor            DECIMAL(12,2) NOT NULL,     -- preço de venda ou aluguel mensal
    status           ENUM('DISPONIVEL', 'ALUGADO', 'VENDIDO') NOT NULL DEFAULT 'DISPONIVEL',
    CONSTRAINT fk_imoveis_proprietario
        FOREIGN KEY (proprietario_id) REFERENCES clientes(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Contratos (locação ou venda)
CREATE TABLE contratos (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    imovel_id    INT           NOT NULL,
    cliente_id   INT           NOT NULL,         -- inquilino ou comprador
    tipo         ENUM('LOCACAO', 'VENDA') NOT NULL,
    data_inicio  DATE          NOT NULL,
    data_fim     DATE          NULL,             -- NULL em vendas
    valor        DECIMAL(12,2) NOT NULL,
    status       ENUM('ATIVO', 'ENCERRADO', 'CANCELADO') NOT NULL DEFAULT 'ATIVO',
    CONSTRAINT fk_contratos_imovel
        FOREIGN KEY (imovel_id) REFERENCES imoveis(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_contratos_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_datas
        CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);

-- 3) INSERT INTO

INSERT INTO usuarios (nome, usuario, senha_hash) VALUES
('Administrador',       'admin',      SHA2('admin123', 256)),
('Davi Barbosa Brito',  'davi',       SHA2('davi123', 256)),
('Igo Patrick',         'dupla',      SHA2('dupla123', 256)),
('Corretor Plantão',    'corretor',   SHA2('corretor123', 256)),
('Secretaria',          'secretaria', SHA2('secretaria123', 256));

INSERT INTO clientes (nome, cpf, telefone, email, tipo) VALUES
('Maria Oliveira Santos',  '12345678901', '(63) 99901-1001', 'maria.oliveira@email.com',  'PROPRIETARIO'),
('João Pereira Lima',      '23456789012', '(63) 99902-2002', 'joao.lima@email.com',       'PROPRIETARIO'),
('Ana Costa Ribeiro',      '34567890123', '(63) 99903-3003', 'ana.ribeiro@email.com',     'AMBOS'),
('Carlos Souza Mendes',    '45678901234', '(63) 99904-4004', 'carlos.mendes@email.com',   'INTERESSADO'),
('Fernanda Alves Rocha',   '56789012345', '(63) 99905-5005', 'fernanda.rocha@email.com',  'INTERESSADO'),
('Ricardo Gomes Barros',   '67890123456', '(63) 99906-6006', 'ricardo.barros@email.com',  'INTERESSADO'),
('Juliana Martins Freitas','78901234567', '(63) 99907-7007', 'juliana.freitas@email.com', 'INTERESSADO'),
('Paulo Henrique Dias',    '89012345678', '(63) 99908-8008', 'paulo.dias@email.com',      'PROPRIETARIO');

INSERT INTO imoveis
(proprietario_id, titulo, tipo, finalidade, endereco, bairro, area_m2, quartos, valor, status) VALUES
(1, 'Apartamento 2 quartos na 104 Sul',  'APARTAMENTO',    'ALUGUEL', 'Quadra 104 Sul, Alameda 5, Lote 10',   'Plano Diretor Sul',   68.00, 2,   1800.00, 'ALUGADO'),
(1, 'Casa 3 quartos na 406 Norte',       'CASA',           'VENDA',   'Quadra 406 Norte, Alameda 12, Lote 3', 'Plano Diretor Norte', 180.00, 3, 450000.00, 'VENDIDO'),
(2, 'Sala comercial na Av. JK',          'SALA_COMERCIAL', 'ALUGUEL', 'Av. Juscelino Kubitschek, 1500, Sala 8','Centro',             45.00, 0,   2500.00, 'ALUGADO'),
(2, 'Terreno em Taquaralto',             'TERRENO',        'VENDA',   'Rua 7, Quadra 15, Lote 22',            'Taquaralto',          360.00, 0, 120000.00, 'DISPONIVEL'),
(3, 'Casa 4 quartos na 1103 Sul',        'CASA',           'VENDA',   'Quadra 1103 Sul, Alameda 2, Lote 18',  'Plano Diretor Sul',   250.00, 4, 680000.00, 'DISPONIVEL'),
(8, 'Apartamento 3 quartos na 202 Norte','APARTAMENTO',    'ALUGUEL', 'Quadra 202 Norte, Alameda 1, Lote 7',  'Plano Diretor Norte', 95.00, 3,   2200.00, 'ALUGADO'),
(8, 'Casa 2 quartos no Aureny I',        'CASA',           'ALUGUEL', 'Rua 4, Quadra 30, Lote 5',             'Jardim Aureny I',     90.00, 2,   1200.00, 'DISPONIVEL');

INSERT INTO contratos (imovel_id, cliente_id, tipo, data_inicio, data_fim, valor, status) VALUES
(1, 4, 'LOCACAO', '2026-02-01', '2027-01-31',   1800.00, 'ATIVO'),
(2, 5, 'VENDA',   '2026-05-15', NULL,         445000.00, 'ENCERRADO'),
(3, 3, 'LOCACAO', '2025-08-01', '2027-07-31',   2500.00, 'ATIVO'),
(6, 6, 'LOCACAO', '2026-03-10', '2027-03-09',   2200.00, 'ATIVO'),
(7, 7, 'LOCACAO', '2024-06-01', '2025-05-31',   1150.00, 'ENCERRADO');


-- =========================================================
-- CONSULTAS PARA DEMONSTRAÇÃO
-- =========================================================

-- SELECT simples: imóveis disponíveis
SELECT id, titulo, finalidade, bairro, valor
FROM imoveis
WHERE status = 'DISPONIVEL'
ORDER BY valor;

-- Pesquisa: aluguéis até R$ 2.000
SELECT titulo, bairro, quartos, valor
FROM imoveis
WHERE finalidade = 'ALUGUEL' AND valor <= 2000;

-- JOIN: contratos com imóvel, proprietário e cliente
SELECT
    c.id            AS contrato,
    c.tipo,
    i.titulo        AS imovel,
    prop.nome       AS proprietario,
    cli.nome        AS cliente,
    c.valor,
    c.data_inicio,
    c.data_fim,
    c.status
FROM contratos c
INNER JOIN imoveis  i    ON i.id    = c.imovel_id
INNER JOIN clientes prop ON prop.id = i.proprietario_id
INNER JOIN clientes cli  ON cli.id  = c.cliente_id
ORDER BY c.data_inicio DESC;

-- LEFT JOIN + GROUP BY: quantidade de imóveis por proprietário
SELECT cl.nome, COUNT(i.id) AS total_imoveis
FROM clientes cl
LEFT JOIN imoveis i ON i.proprietario_id = cl.id
WHERE cl.tipo IN ('PROPRIETARIO', 'AMBOS')
GROUP BY cl.id, cl.nome;

-- UPDATE: reajuste do aluguel do imóvel 7
UPDATE imoveis
SET valor = 1300.00
WHERE id = 7;

-- DELETE: cria um cliente de teste e exclui
INSERT INTO clientes (nome, cpf, telefone, tipo)
VALUES ('Cliente Teste', '99999999999', '(63) 90000-0000', 'INTERESSADO');

DELETE FROM clientes
WHERE cpf = '99999999999';

-- Demonstração da FK (vai dar ERRO 1451 de propósito):
-- a Maria possui imóveis, então o banco impede a exclusão.
-- DELETE FROM clientes WHERE id = 1;
