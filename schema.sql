-- Opcional: a aplicação já cria as tabelas automaticamente.
-- Execute este arquivo no Supabase SQL Editor se preferir criar o banco antes de publicar.

CREATE TABLE IF NOT EXISTS setores (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT UNIQUE NOT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS usuarios (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  usuario TEXT UNIQUE NOT NULL,
  senha_hash TEXT NOT NULL,
  perfil TEXT NOT NULL DEFAULT 'operador' CHECK (perfil IN ('admin','operador')),
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS produtos (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  codigo_barras TEXT UNIQUE,
  setor_id BIGINT NOT NULL REFERENCES setores(id),
  unidade TEXT NOT NULL DEFAULT 'un',
  estoque NUMERIC(12,3) NOT NULL DEFAULT 0 CHECK (estoque >= 0),
  estoque_minimo NUMERIC(12,3) NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
  custo NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (custo >= 0),
  preco_venda NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (preco_venda >= 0),
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS movimentacoes (
  id BIGSERIAL PRIMARY KEY,
  produto_id BIGINT NOT NULL REFERENCES produtos(id),
  usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('entrada','saida','ajuste')),
  quantidade NUMERIC(12,3) NOT NULL CHECK (quantidade > 0),
  estoque_anterior NUMERIC(12,3) NOT NULL,
  estoque_posterior NUMERIC(12,3) NOT NULL,
  observacao TEXT,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO setores (nome) VALUES ('Alimentos'),('Limpeza') ON CONFLICT DO NOTHING;
