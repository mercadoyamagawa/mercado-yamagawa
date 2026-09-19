import os
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, request, redirect, url_for, session, render_template_string, flash, Response
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
    PERMANENT_SESSION_LIFETIME=28800,
)

DB = os.environ.get("DATABASE_URL", "")

SCHEMA = """
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

CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome);
CREATE INDEX IF NOT EXISTS idx_produtos_barcode ON produtos(codigo_barras);
CREATE INDEX IF NOT EXISTS idx_mov_data ON movimentacoes(criado_em DESC);
"""

def db():
    if not DB:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg.connect(DB, row_factory=dict_row)

def init_db():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS data_validade DATE")
            cur.execute("INSERT INTO setores (nome) VALUES ('Alimentos'), ('Limpeza') ON CONFLICT DO NOTHING")
            admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip()
            admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123").strip()
            admin_name = os.environ.get("ADMIN_NAME", "Administrador").strip()
            cur.execute("SELECT id FROM usuarios WHERE usuario=%s", (admin_user,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO usuarios (nome,usuario,senha_hash,perfil) VALUES (%s,%s,%s,'admin')",
                    (admin_name, admin_user, generate_password_hash(admin_pass))
                )
        conn.commit()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("uid") or session.get("perfil") != "admin":
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def page(title, body, **ctx):
    return render_template_string(BASE, title=title, body=body, **ctx)

BASE = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} - Mercado YAMAGAWA</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f4f6f8;color:#222}
header{background:#fff;padding:10px 16px;display:flex;align-items:center;gap:14px;box-shadow:0 1px 5px #bbb}
header img{height:54px;max-width:180px;object-fit:contain}
.login-logo{display:block;width:220px;max-width:80%;height:auto;margin:0 auto 18px;object-fit:contain}
nav a{margin-right:10px;text-decoration:none;color:#174a7e;font-weight:bold}
main{max-width:1100px;margin:20px auto;padding:0 12px}
.card{background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 5px #ddd;margin-bottom:16px}
input,select,button{padding:10px;margin:4px 0;border:1px solid #bbb;border-radius:7px;font-size:15px}
button,.btn{background:#174a7e;color:#fff;border:0;padding:10px 14px;text-decoration:none;display:inline-block;border-radius:7px}
.danger{background:#a52a2a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.stat{font-size:28px;font-weight:bold}.low{background:#fff0f0}
table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}
.flash{padding:10px;border-radius:7px;background:#fff4cc;margin-bottom:10px}
.actions a{margin-right:5px}.small{font-size:13px;color:#666}
</style>
</head>
<body>
<header>
{% if session.get('uid') %}
<img src="{{ url_for('static',filename='logo.jpg') }}" onerror="this.style.display='none'">
<div>
<nav>
<a href="{{ url_for('dashboard') }}">Início</a>
<a href="{{ url_for('products') }}">Produtos</a>
<a href="{{ url_for('movement') }}">Movimentar</a>
<a href="{{ url_for('history') }}">Histórico</a>
{% if session.get('perfil')=='admin' %}<a href="{{ url_for('users') }}">Usuários</a>{% endif %}
<a href="{{ url_for('logout') }}">Sair</a>
</nav>
<div class="small">Usuário: {{ session.get('nome') }}</div>
</div>
{% endif %}
</header>
<main>
{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}
{{ body|safe }}
</main>
</body></html>
"""

@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("uid") else url_for("login"))

@app.route("/health")
def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1")
        return "OK", 200
    except Exception as e:
        return f"ERRO: {e}", 500

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("usuario","").strip()
        p = request.form.get("senha","")
        with db() as conn:
            cur = conn.execute("SELECT * FROM usuarios WHERE usuario=%s AND ativo=TRUE", (u,))
            user = cur.fetchone()
        if user and check_password_hash(user["senha_hash"], p):
            session.clear()
            session["uid"], session["nome"], session["perfil"] = user["id"], user["nome"], user["perfil"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha inválidos.")
    body = """
    <div class="card" style="max-width:420px;margin:60px auto;text-align:center">
      <img src="/static/logo.jpg" alt="Mercado Yamagawa" class="login-logo">
      <h2>Mercado YAMAGAWA</h2>
      <p>Controle de estoque online</p>
      <form method="post">
        <input name="usuario" placeholder="Usuário" required style="width:95%">
        <input name="senha" type="password" placeholder="Senha" required style="width:95%">
        <button>Entrar</button>
      </form>
      <p class="small">O administrador inicial é definido pelas variáveis ADMIN_USERNAME e ADMIN_PASSWORD no Render.</p>
    </div>"""
    return page("Login", body)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as conn:
    total = conn.execute(
        "SELECT COUNT(*) c FROM produtos WHERE ativo"
    ).fetchone()["c"]

    estoque = conn.execute(
        "SELECT COALESCE(SUM(estoque),0) s FROM produtos WHERE ativo"
    ).fetchone()["s"]

    baixos = conn.execute(
        "SELECT COUNT(*) c FROM produtos WHERE ativo AND estoque <= estoque_minimo"
    ).fetchone()["c"]

    vencidos = conn.execute("""
        SELECT COUNT(*) c
        FROM produtos
        WHERE ativo
          AND data_validade IS NOT NULL
          AND data_validade < CURRENT_DATE
    """).fetchone()["c"]

    vencendo = conn.execute("""
        SELECT COUNT(*) c
        FROM produtos
        WHERE ativo
          AND data_validade IS NOT NULL
          AND data_validade >= CURRENT_DATE
          AND data_validade <= CURRENT_DATE + INTERVAL '30 days'
    """).fetchone()["c"]

    recentes = conn.execute("""
        SELECT p.nome,m.tipo,m.quantidade,m.criado_em
        FROM movimentacoes m
        JOIN produtos p ON p.id=m.produto_id
        ORDER BY m.criado_em DESC
        LIMIT 8
    """).fetchall()
    body = render_template_string("""
    <h1>Painel</h1>
    <div class="grid">
  <div class="card">
    <div class="stat">{{total}}</div>
    Produtos
  </div>

  <div class="card">
    <div class="stat">{{estoque}}</div>
    Itens em estoque
  </div>

  <div class="card low">
    <div class="stat">{{baixos}}</div>
    Estoque baixo
  </div>

  <div class="card" style="background:#ffe5e5">
    <div class="stat">{{vencidos}}</div>
    🔴 Produtos vencidos
  </div>

  <div class="card" style="background:#fff2d9">
    <div class="stat">{{vencendo}}</div>
    🟠 Vencendo em até 30 dias
  </div>
</div>
    </div>
    <div class="card">
      <h3>Últimas movimentações</h3>
      <table><tr><th>Produto</th><th>Tipo</th><th>Qtd.</th><th>Data</th></tr>
      {% for r in recentes %}<tr><td>{{r.nome}}</td><td>{{r.tipo}}</td><td>{{r.quantidade}}</td><td>{{r.criado_em.strftime('%d/%m/%Y %H:%M')}}</td></tr>{% endfor %}
      </table>
    </div>
    """,
total=total,
estoque=estoque,
baixos=baixos,
vencidos=vencidos,
vencendo=vencendo,
recentes=recentes
)
    return page("Painel", body)

@app.route("/produtos")
@login_required
def products():
    q = request.args.get("q","").strip()
    with db() as conn:
        rows = conn.execute("""SELECT p.*,s.nome setor FROM produtos p JOIN setores s ON s.id=p.setor_id
          WHERE p.ativo AND (%s='' OR p.nome ILIKE '%%'||%s||'%%' OR COALESCE(p.codigo_barras,'') ILIKE '%%'||%s||'%%')
          ORDER BY p.nome""",(q,q,q)).fetchall()
    body = render_template_string("""
...
""",
rows=rows,
q=q,
date=date,
timedelta=timedelta
)

return page("Produtos", body)

FORM = """
<h1>{{titulo}}</h1>
<div class="card">
<form method="post">
<label>Nome<br><input name="nome" value="{{p.nome if p else ''}}" required style="width:95%"></label><br>
<label>Código de barras<br><input id="barcode" name="codigo_barras" value="{{p.codigo_barras if p else ''}}" style="width:70%">
<button type="button" onclick="scan()">📷 Ler código</button></label><br>
<label>Setor<br><select name="setor_id" required>{% for s in setores %}<option value="{{s.id}}" {% if p and p.setor_id==s.id %}selected{% endif %}>{{s.nome}}</option>{% endfor %}</select></label><br>
<label>Unidade<br><input name="unidade" value="{{p.unidade if p else 'un'}}"></label><br>
<label>Estoque inicial<br><input type="number" step="0.001" min="0" name="estoque" value="{{p.estoque if p else 0}}"></label><br>
<label>Estoque mínimo<br><input type="number" step="0.001" min="0" name="estoque_minimo" value="{{p.estoque_minimo if p else 0}}"></label><br>
<label>Custo<br><input type="number" step="0.01" min="0" name="custo" value="{{p.custo if p else 0}}"></label><br>
<label>Preço de venda<br><input type="number" step="0.01" min="0" name="preco_venda" value="{{p.preco_venda if p else 0}}"></label><br>
<label>Data de validade<br><input type="date" name="data_validade" value="{{p.data_validade if p and p.data_validade else ''}}"></label><br>
<button>Salvar</button> <a class="btn" href="{{url_for('products')}}">Cancelar</a>
</form></div>
<script>
async function scan(){
  if(!('BarcodeDetector' in window)){ alert('O navegador não oferece leitura de código de barras. Digite o código manualmente.'); return; }
  try{
    const detector=new BarcodeDetector();
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}});
    const v=document.createElement('video'); v.srcObject=stream; v.setAttribute('playsinline',''); await v.play();
    const box=document.createElement('div'); box.style='position:fixed;inset:10%;background:white;z-index:9999;padding:20px;border-radius:10px;text-align:center';
    box.innerHTML='<h3>Aponte a câmera para o código</h3><p>Toque na tela para cancelar.</p>'; box.appendChild(v); document.body.appendChild(box);
    box.onclick=()=>{stream.getTracks().forEach(t=>t.stop());box.remove()};
    const timer=setInterval(async()=>{try{const codes=await detector.detect(v);if(codes.length){document.getElementById('barcode').value=codes[0].rawValue;clearInterval(timer);stream.getTracks().forEach(t=>t.stop());box.remove()}}catch(e){}},300);
  }catch(e){alert('Não foi possível abrir a câmera. Verifique a permissão do navegador.');}
}
</script>
"""

@app.route("/produto/novo", methods=["GET","POST"])
@login_required
def product_new():
    if request.method=="POST":
        f=request.form
        with db() as conn:
            conn.execute("""INSERT INTO produtos(
    nome,codigo_barras,setor_id,unidade,estoque,estoque_minimo,custo,preco_venda,data_validade
)
VALUES(
    %s,NULLIF(%s,''),%s,%s,%s,%s,%s,%s,CAST(NULLIF(%s,'') AS DATE)
)""",
(
    f["nome"].strip(),
    f.get("codigo_barras","").strip(),
    f["setor_id"],
    f.get("unidade","un"),
    f["estoque"],
    f["estoque_minimo"],
    f["custo"],
    f["preco_venda"],
    f.get("data_validade","")
))
            conn.commit()
        flash("Produto cadastrado.")
        return redirect(url_for("products"))
    with db() as conn: setores=conn.execute("SELECT * FROM setores WHERE ativo ORDER BY nome").fetchall()
    return page("Novo produto", render_template_string(FORM,titulo="Novo produto",p=None,setores=setores))

@app.route("/produto/<int:pid>/editar", methods=["GET","POST"])
@login_required
def product_edit(pid):
    with db() as conn:
        if request.method=="POST":
            f=request.form
            conn.execute("""UPDATE produtos SET
  nome=%s,
  codigo_barras=NULLIF(%s,''),
  setor_id=%s,
  unidade=%s,
  estoque=%s,
  estoque_minimo=%s,
  custo=%s,
  preco_venda=%s,
  data_validade=CAST(NULLIF(%s,'') AS DATE),
  atualizado_em=NOW()
WHERE id=%s""",
(
  f["nome"].strip(),
  f.get("codigo_barras","").strip(),
  f["setor_id"],
  f.get("unidade","un"),
  f["estoque"],
  f["estoque_minimo"],
  f["custo"],
  f["preco_venda"],
  f.get("data_validade",""),
  pid
))
            conn.commit(); flash("Produto atualizado."); return redirect(url_for("products"))
        p=conn.execute("SELECT * FROM produtos WHERE id=%s",(pid,)).fetchone()
        setores=conn.execute("SELECT * FROM setores WHERE ativo ORDER BY nome").fetchall()
    return page("Editar produto", render_template_string(FORM,titulo="Editar produto",p=p,setores=setores))

@app.route("/movimentar", methods=["GET","POST"])
@login_required
def movement():
    with db() as conn:
        if request.method=="POST":
            pid=int(request.form["produto_id"]); tipo=request.form["tipo"]; qtd=float(request.form["quantidade"])
            with conn.cursor() as cur:
                cur.execute("SELECT estoque FROM produtos WHERE id=%s FOR UPDATE",(pid,))
                p=cur.fetchone()
                if not p: flash("Produto não encontrado.")
                else:
                    old=float(p["estoque"])
                    if tipo=="entrada": new=old+qtd
                    elif tipo=="saida": new=old-qtd
                    else: new=qtd
                    if new<0: flash("A saída não pode deixar o estoque negativo.")
                    else:
                        cur.execute("UPDATE produtos SET estoque=%s,atualizado_em=NOW() WHERE id=%s",(new,pid))
                        cur.execute("""INSERT INTO movimentacoes(produto_id,usuario_id,tipo,quantidade,estoque_anterior,estoque_posterior,observacao)
                          VALUES(%s,%s,%s,%s,%s,%s,%s)""",(pid,session["uid"],tipo,qtd,old,new,request.form.get("observacao","")))
                        conn.commit(); flash("Movimentação registrada."); return redirect(url_for("movement"))
        produtos=conn.execute("SELECT id,nome,estoque,unidade FROM produtos WHERE ativo ORDER BY nome").fetchall()
    selected=request.args.get("produto","")
    body=render_template_string("""
    <h1>Movimentar estoque</h1><div class="card"><form method="post">
    <label>Produto<br><select name="produto_id" required style="width:95%">{% for p in produtos %}<option value="{{p.id}}" {% if selected|string==p.id|string %}selected{% endif %}>{{p.nome}} — {{p.estoque}} {{p.unidade}}</option>{% endfor %}</select></label><br>
    <label>Tipo<br><select name="tipo"><option value="entrada">Entrada</option><option value="saida">Saída</option><option value="ajuste">Ajuste</option></select></label><br>
    <label>Quantidade<br><input type="number" name="quantidade" step="0.001" min="0.001" required></label><br>
    <label>Observação<br><input name="observacao" style="width:95%"></label><br>
    <button>Registrar</button></form></div>""",produtos=produtos,selected=selected)
    return page("Movimentar",body)

@app.route("/historico")
@login_required
def history():
    with db() as conn:
        rows=conn.execute("""SELECT m.*,p.nome produto,u.nome usuario FROM movimentacoes m
          JOIN produtos p ON p.id=m.produto_id LEFT JOIN usuarios u ON u.id=m.usuario_id
          ORDER BY m.criado_em DESC LIMIT 300""").fetchall()
    body=render_template_string("""<h1>Histórico</h1><div class="card"><table>
    <tr><th>Data</th><th>Produto</th><th>Tipo</th><th>Qtd.</th><th>Antes</th><th>Depois</th><th>Usuário</th></tr>
    {% for r in rows %}<tr><td>{{r.criado_em.strftime('%d/%m/%Y %H:%M')}}</td><td>{{r.produto}}</td><td>{{r.tipo}}</td><td>{{r.quantidade}}</td><td>{{r.estoque_anterior}}</td><td>{{r.estoque_posterior}}</td><td>{{r.usuario or ''}}</td></tr>{% endfor %}
    </table></div>""",rows=rows)
    return page("Histórico",body)

@app.route("/usuarios")
@admin_required
def users():
    with db() as conn: rows=conn.execute("SELECT id,nome,usuario,perfil,ativo FROM usuarios ORDER BY nome").fetchall()
    body=render_template_string("""<h1>Usuários</h1><p><a class="btn" href="{{url_for('user_new')}}">+ Novo usuário</a></p>
    <div class="card"><table><tr><th>Nome</th><th>Usuário</th><th>Perfil</th><th>Ativo</th></tr>
    {% for u in rows %}<tr><td>{{u.nome}}</td><td>{{u.usuario}}</td><td>{{u.perfil}}</td><td>{{'Sim' if u.ativo else 'Não'}}</td></tr>{% endfor %}
    </table></div>""",rows=rows)
    return page("Usuários",body)

@app.route("/usuario/novo",methods=["GET","POST"])
@admin_required
def user_new():
    if request.method=="POST":
        f=request.form
        with db() as conn:
            conn.execute("INSERT INTO usuarios(nome,usuario,senha_hash,perfil) VALUES(%s,%s,%s,%s)",
                         (f["nome"],f["usuario"],generate_password_hash(f["senha"]),f["perfil"]))
            conn.commit()
        flash("Usuário criado."); return redirect(url_for("users"))
    body="""<h1>Novo usuário</h1><div class="card"><form method="post">
    <input name="nome" placeholder="Nome" required><br><input name="usuario" placeholder="Usuário" required><br>
    <input name="senha" type="password" placeholder="Senha" required><br>
    <select name="perfil"><option value="operador">Operador</option><option value="admin">Administrador</option></select><br>
    <button>Salvar</button></form></div>"""
    return page("Novo usuário",body)

# Initialize lazily so Render can start even while environment variables are being configured.
@app.before_request
def ensure_db():
    if request.endpoint != "health":
        init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","10000")))

