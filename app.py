from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response, send_from_directory, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import io
import json
import os
import re
from werkzeug.utils import secure_filename
from functools import wraps
import pandas as pd 

# --- Bibliotecas para OCR ---
try:
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path
    
    # CONFIGURAÇÃO DO CAMINHO DO TESSERACT - AJUSTE MANUAL
    # Substitua pelo caminho correto no seu sistema, se necessário
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    # Verificar se o Tesseract está acessível
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
        print("✓ Tesseract OCR configurado com sucesso!")
        print(f"✓ Caminho: {pytesseract.pytesseract.tesseract_cmd}")
    except Exception as e:
        TESSERACT_AVAILABLE = False
        print(f"✗ Erro ao acessar Tesseract: {e}")
        
except ImportError as e:
    TESSERACT_AVAILABLE = False
    print(f"✗ Bibliotecas OCR não disponíveis: {e}")

from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_troque_por_algo_seguro' # IMPORTANTE: Troque por uma chave segura

# --- Configurações de Upload ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --------------------------------

# Configuração do banco de dados
def get_db_connection():
    conn = sqlite3.connect('livro_caixa.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Tabela de usuários
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Tabela de transações
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
            categoria TEXT NOT NULL,
            data DATE NOT NULL,
            forma_pagamento TEXT,
            anexo TEXT,
            observacoes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de categorias padrão
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
            cor TEXT DEFAULT '#6c757d'
        )
    ''')
    
    # Inserir categorias padrão
    categorias_receita = [
        ('Salário', 'receita', '#28a745'),
        ('Freelance', 'receita', '#20c997'),
        ('Investimentos', 'receita', '#17a2b8'),
        ('Vendas', 'receita', '#6f42c1'),
        ('Outros', 'receita', '#6c757d')
    ]
    
    categorias_despesa = [
        ('Alimentação', 'despesa', '#dc3545'),
        ('Moradia', 'despesa', '#fd7e14'),
        ('Transporte', 'despesa', '#ffc107'),
        ('Saúde', 'despesa', '#e83e8c'),
        ('Educação', 'despesa', '#6f42c1'),
        ('Lazer', 'despesa', '#20c997'),
        ('Outros', 'despesa', '#6c757d')
    ]
    
    for categoria in categorias_receita:
        conn.execute('INSERT OR IGNORE INTO categorias (nome, tipo, cor) VALUES (?, ?, ?)', categoria)
    
    for categoria in categorias_despesa:
        conn.execute('INSERT OR IGNORE INTO categorias (nome, tipo, cor) VALUES (?, ?, ?)', categoria)
    
    conn.commit()
    conn.close()

# --- Rotas de Autenticação e Sessão ---

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db_connection().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()
        error = None

        if not username:
            error = 'Nome de usuário é obrigatório.'
        elif not password:
            error = 'Senha é obrigatória.'
        
        if error is None:
            try:
                db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
                db.commit()
            except db.IntegrityError:
                error = f"Usuário {username} já está registrado."
            else:
                return redirect(url_for("login"))
        
        flash(error)

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db_connection()
        error = None
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'Usuário incorreto.'
        elif not check_password_hash(user['password'], password):
            error = 'Senha incorreta.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Rotas da Aplicação ---

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/lancamentos')
@login_required
def lancamentos():
    return render_template('lancamentos.html')

@app.route('/relatorios')
@login_required
def relatorios():
    return render_template('relatorios.html')

@app.route('/backup')
@login_required
def backup():
    try:
        db_filename = 'livro_caixa.db'
        root_dir = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(directory=root_dir, path=db_filename, as_attachment=True)
    except Exception as e:
        flash(f'Erro ao gerar o backup: {str(e)}', 'danger')
        return redirect(url_for('index'))

# --- API e Rotas de Funcionalidades ---

@app.route('/api/ocr/processar', methods=['POST'])
@login_required
def processar_ocr():
    if not TESSERACT_AVAILABLE:
        return jsonify({'success': False, 'error': 'Recurso OCR não disponível.'})

    if 'anexo' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado.'})

    file = request.files['anexo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Arquivo inválido ou não permitido.'})

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text = ''
        if filename.lower().endswith('.pdf'):
            try:
                pages = convert_from_path(filepath, 200)
                for page in pages:
                    text += pytesseract.image_to_string(page, lang='por') + '\n'
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro ao processar PDF: {str(e)}'})
        else:
            try:
                text = pytesseract.image_to_string(Image.open(filepath), lang='por')
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro ao processar imagem: {str(e)}'})
        
        matches = re.findall(r'(\d+[\.,]\d{2})', text)
        valor_encontrado = 0.0
        if matches:
            max_valor = 0
            for match in matches:
                try:
                    valor_numerico = float(match.replace(',', '.'))
                    if valor_numerico > max_valor:
                        max_valor = valor_numerico
                except ValueError:
                    continue
            valor_encontrado = max_valor

        return jsonify({
            'success': True, 
            'valor': valor_encontrado, 
            'texto': text,
            'mensagem': f'Valor R$ {valor_encontrado:.2f} extraído do anexo.' if valor_encontrado > 0 else 'Nenhum valor monetário encontrado no anexo.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao processar o arquivo: {str(e)}'})

@app.route('/api/transacoes', methods=['GET', 'POST'])
@login_required
def api_transacoes():
    conn = get_db_connection()
    if request.method == 'GET':
        transacoes = conn.execute('SELECT t.*, c.cor FROM transacoes t LEFT JOIN categorias c ON t.categoria = c.nome AND t.tipo = c.tipo ORDER BY t.data DESC, t.id DESC').fetchall()
        result = [dict(row) for row in transacoes]
        conn.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        try:
            data = request.form
            anexo_filename = None
            if 'anexo' in request.files:
                file = request.files['anexo']
                if file and file.filename and allowed_file(file.filename):
                    anexo_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], anexo_filename))

            conn.execute(
                'INSERT INTO transacoes (descricao, valor, tipo, categoria, data, forma_pagamento, anexo, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (data['descricao'], data['valor'], data['tipo'], data['categoria'], data['data'], data.get('forma_pagamento'), anexo_filename, data.get('observacoes'))
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Transação adicionada com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/transacoes/<int:id>', methods=['DELETE'])
@login_required
def api_excluir_transacao(id):
    conn = get_db_connection()
    try:
        transacao = conn.execute('SELECT anexo FROM transacoes WHERE id = ?', (id,)).fetchone()
        if transacao and transacao['anexo']:
            anexo_path = os.path.join(app.config['UPLOAD_FOLDER'], transacao['anexo'])
            if os.path.exists(anexo_path):
                os.remove(anexo_path)
        
        conn.execute('DELETE FROM transacoes WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Transação excluída com sucesso!'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/relatorios/saldo')
@login_required
def api_saldo():
    conn = get_db_connection()
    receitas = conn.execute('SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita"').fetchone()['total'] or 0
    despesas = conn.execute('SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa"').fetchone()['total'] or 0
    saldo = receitas - despesas
    conn.close()
    return jsonify({'receitas': receitas, 'despesas': despesas, 'saldo': saldo})

@app.route('/api/relatorios/mensal')
@login_required
def api_mensal():
    conn = get_db_connection()
    query = """
        SELECT 
            strftime('%Y-%m', data) as mes,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END) as receitas,
            SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END) as despesas,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE -valor END) as saldo
        FROM transacoes
        GROUP BY mes ORDER BY mes DESC LIMIT 12
    """
    resultados = conn.execute(query).fetchall()
    conn.close()
    dados = [dict(row) for row in resultados]
    return jsonify(dados[::-1])

@app.route('/api/relatorios/categorias')
@login_required
def api_categorias():
    conn = get_db_connection()
    receitas = conn.execute("SELECT categoria, SUM(valor) as total FROM transacoes WHERE tipo = 'receita' GROUP BY categoria ORDER BY total DESC").fetchall()
    despesas = conn.execute("SELECT categoria, SUM(valor) as total FROM transacoes WHERE tipo = 'despesa' GROUP BY categoria ORDER BY total DESC").fetchall()
    conn.close()
    return jsonify({
        'receitas': [dict(row) for row in receitas],
        'despesas': [dict(row) for row in despesas]
    })

@app.route('/api/relatorios/detalhado')
@login_required
def api_relatorio_detalhado():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    
    conn = get_db_connection()
    
    query = 'SELECT * FROM transacoes WHERE data BETWEEN ? AND ?'
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND tipo = ?'
        params.append(tipo)
    
    query += ' ORDER BY data DESC, id DESC'
    transacoes = conn.execute(query, params).fetchall()
    
    totais_query = 'SELECT tipo, COUNT(*) as quantidade, SUM(valor) as total FROM transacoes WHERE data BETWEEN ? AND ?'
    totais_params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        totais_query += ' AND tipo = ?'
        totais_params.append(tipo)
    
    totais_query += ' GROUP BY tipo'
    totais_result = conn.execute(totais_query, totais_params).fetchall()
    
    totais = {'receita': {'quantidade': 0, 'total': 0}, 'despesa': {'quantidade': 0, 'total': 0}}
    for row in totais_result:
        totais[row['tipo']] = {'quantidade': row['quantidade'], 'total': row['total']}
    
    conn.close()
    
    return jsonify({
        'transacoes': [dict(t) for t in transacoes],
        'totais': totais,
        'periodo': {'inicio': data_inicio, 'fim': data_fim, 'tipo': tipo}
    })

@app.route('/relatorio/pdf')
@login_required
def relatorio_pdf():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    
    conn = get_db_connection()
    
    query = 'SELECT * FROM transacoes WHERE data BETWEEN ? AND ?'
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND tipo = ?'
        params.append(tipo)
    
    query += ' ORDER BY data DESC'
    transacoes = conn.execute(query, params).fetchall()
    
    receitas = conn.execute('SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita" AND data BETWEEN ? AND ?', (data_inicio, data_fim)).fetchone()['total'] or 0
    despesas = conn.execute('SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa" AND data BETWEEN ? AND ?', (data_inicio, data_fim)).fetchone()['total'] or 0
    saldo = receitas - despesas
    
    conn.close()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=30, alignment=1)
    
    elements.append(Paragraph(f'Relatório Financeiro - {data_inicio} a {data_fim}', title_style))
    
    resumo_data = [['Receitas', f'R$ {receitas:,.2f}'], ['Despesas', f'R$ {despesas:,.2f}'], ['Saldo', f'R$ {saldo:,.2f}']]
    resumo_table = Table(resumo_data, colWidths=[300, 100])
    resumo_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey), ('TEXTCOLOR', (0, 0), (-1, -1), colors.black), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
    elements.append(resumo_table)
    elements.append(Spacer(1, 20))
    
    if transacoes:
        table_data = [['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor']]
        for t in transacoes:
            table_data.append([t['data'], t['descricao'], t['categoria'], t['tipo'].capitalize(), f"R$ {t['valor']:,.2f}"])
        
        transacoes_table = Table(table_data, colWidths=[60, 150, 80, 60, 60])
        transacoes_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        elements.append(transacoes_table)
    else:
        elements.append(Paragraph('Nenhuma transação encontrada para o período.', styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{data_inicio}_{data_fim}.pdf'
    
    return response
@app.route('/importar_planilha', methods=['POST'])
@login_required
def importar_planilha():
    if 'planilha' not in request.files:
        flash('Nenhum arquivo selecionado!', 'danger')
        return redirect(url_for('lancamentos'))

    file = request.files['planilha']

    if file.filename == '' or not file.filename.endswith('.xlsx'):
        flash('Arquivo inválido! Por favor, envie um arquivo .xlsx.', 'danger')
        return redirect(url_for('lancamentos'))

    try:
        # Ler o arquivo excel usando pandas
        df = pd.read_excel(file)

        # Verificar se as colunas obrigatórias existem
        colunas_obrigatorias = ['Data', 'Descricao', 'Valor', 'Tipo', 'Categoria']
        for coluna in colunas_obrigatorias:
            if coluna not in df.columns:
                flash(f'A coluna obrigatória "{coluna}" não foi encontrada na planilha.', 'danger')
                return redirect(url_for('lancamentos'))

        conn = get_db_connection()
        transacoes_importadas = 0

        # Iterar sobre cada linha da planilha
        for index, row in df.iterrows():
            # Validar e limpar os dados de cada linha
            data = pd.to_datetime(row['Data']).strftime('%Y-%m-%d')
            descricao = str(row['Descricao'])
            valor = float(row['Valor'])
            tipo = str(row['Tipo']).lower()
            categoria = str(row['Categoria'])

            if tipo not in ['receita', 'despesa']:
                continue # Pula linhas com tipo inválido

            # Inserir no banco de dados
            conn.execute(
                'INSERT INTO transacoes (data, descricao, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)',
                (data, descricao, valor, tipo, categoria)
            )
            transacoes_importadas += 1

        conn.commit()
        conn.close()

        flash(f'{transacoes_importadas} transações importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Ocorreu um erro ao processar a planilha: {e}', 'danger')

    return redirect(url_for('lancamentos'))

# --- Inicialização ---

if __name__ == '__main__':
    print("Iniciando Livro Caixa Financeiro...")
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)