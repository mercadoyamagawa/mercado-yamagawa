# Mercado YAMAGAWA — versão simples

Esta é a versão mais fácil para publicar online usando **Supabase + Render**.

## 1) Banco Supabase
No Supabase, abra **SQL Editor** e execute o arquivo `schema.sql` se quiser criar as tabelas manualmente.
A aplicação também cria as tabelas automaticamente na primeira abertura.

## 2) GitHub
Crie um repositório no GitHub e envie todos os arquivos desta pasta.

## 3) Render
No Render, escolha **New > Web Service**, conecte o repositório e use:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app`

Em **Environment Variables**, coloque:
- `DATABASE_URL` = sua conexão do Supabase com `?sslmode=require`
- `SECRET_KEY` = uma chave longa aleatória
- `ADMIN_USERNAME` = usuário inicial, por exemplo `admin`
- `ADMIN_PASSWORD` = senha inicial forte
- `ADMIN_NAME` = Administrador
- `COOKIE_SECURE` = `1`

**Nunca coloque a senha real do banco ou do administrador dentro do GitHub.**

## 4) Primeiro acesso
Abra a URL criada pelo Render e entre com `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

## Recursos desta versão
- Login seguro com senha armazenada em hash
- Administrador e operador
- Produtos por setor
- Busca por nome/código de barras
- Leitura de código pela câmera quando o navegador oferece BarcodeDetector
- Entrada, saída e ajuste de estoque
- Histórico de movimentações
- Alerta visual de estoque baixo
- Logo do Mercado YAMAGAWA
- Endpoint `/health`

## Observação
O serviço gratuito do Render pode entrar em repouso após um período sem acesso. Isso é normal no plano gratuito.
