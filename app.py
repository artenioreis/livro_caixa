from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response, send_from_directory
from datetime import datetime, timedelta
import sqlite3
import io
import json
import os
import re
from werkzeug.utils import secure_filename

# --- Bibliotecas para OCR ---
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# Se você instalou o Tesseract em um local não padrão no Windows, descomente e ajuste a linha abaixo:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# -----------------------------

from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.secret_key = 'livro_caixa_financeiro_2024'

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
        conn.execute('''
            INSERT OR IGNORE INTO categorias (nome, tipo, cor)
            VALUES (?, ?, ?)
        ''', categoria)
    
    for categoria in categorias_despesa:
        conn.execute('''
            INSERT OR IGNORE INTO categorias (nome, tipo, cor)
            VALUES (?, ?, ?)
        ''', categoria)
    
    conn.commit()
    conn.close()

# Rota para servir os arquivos de anexo
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Rotas principais
@app.route('/')
@app.route('/index') # >>> ROTA ADICIONADA PARA CONSISTÊNCIA <<<
def index():
    return render_template('index.html')

@app.route('/lancamentos')
def lancamentos():
    return render_template('lancamentos.html')

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

# >>> ROTA PARA OCR CORRIGIDA <<<
@app.route('/api/ocr/processar', methods=['POST'])
def processar_ocr():
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
        # CORREÇÃO: 'endsWith' -> 'endswith' (minúsculo)
        if filename.lower().endswith('.pdf'):
            pages = convert_from_path(filepath, 200)
            for page in pages:
                text += pytesseract.image_to_string(page, lang='por') + '\n'
        else:
            text = pytesseract.image_to_string(Image.open(filepath), lang='por')
        
        matches = re.findall(r'(\d+[\.,]\d{2})', text)
        valor_encontrado = 0.0
        if matches:
            max_valor = 0
            for match in matches:
                valor_numerico = float(match.replace(',', '.'))
                if valor_numerico > max_valor:
                    max_valor = valor_numerico
            valor_encontrado = max_valor

        return jsonify({'success': True, 'valor': valor_encontrado, 'texto': text})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao processar o arquivo: {str(e)}'})

# API para transações
@app.route('/api/transacoes', methods=['GET', 'POST'])
def api_transacoes():
    conn = get_db_connection()
    
    if request.method == 'GET':
        query = '''
            SELECT t.*, c.cor 
            FROM transacoes t 
            LEFT JOIN categorias c ON t.categoria = c.nome AND t.tipo = c.tipo
            ORDER BY t.data DESC, t.id DESC
        '''
        transacoes = conn.execute(query).fetchall()
        
        result = []
        for transacao in transacoes:
            transacao_dict = dict(transacao)
            transacao_dict['valor'] = float(transacao_dict['valor'])
            result.append(transacao_dict)
        
        conn.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        try:
            descricao = request.form['descricao']
            valor = request.form['valor']
            tipo = request.form['tipo']
            categoria = request.form['categoria']
            data = request.form['data']
            forma_pagamento = request.form.get('forma_pagamento')
            observacoes = request.form.get('observacoes')
            
            anexo_filename = None
            if 'anexo' in request.files:
                file = request.files['anexo']
                if file and file.filename and allowed_file(file.filename):
                    anexo_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], anexo_filename))

            conn.execute('''
                INSERT INTO transacoes (descricao, valor, tipo, categoria, data, forma_pagamento, anexo, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                descricao, valor, tipo, categoria, data, forma_pagamento, anexo_filename, observacoes
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Transação adicionada com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/transacoes/<int:id>', methods=['DELETE'])
def api_excluir_transacao(id):
    conn = get_db_connection()
    try:
        # Primeiro, verifique se existe um anexo para excluir
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

# API para relatórios
@app.route('/api/relatorios/saldo')
def api_saldo():
    conn = get_db_connection()
    
    # Calcular totais
    receitas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita"'
    ).fetchone()['total'] or 0
    
    despesas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa"'
    ).fetchone()['total'] or 0
    
    saldo = receitas - despesas
    
    conn.close()
    
    return jsonify({
        'receitas': float(receitas),
        'despesas': float(despesas),
        'saldo': float(saldo)
    })

@app.route('/api/relatorios/mensal')
def api_mensal():
    conn = get_db_connection()
    
    query = '''
        SELECT 
            strftime('%Y-%m', data) as mes,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END) as receitas,
            SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END) as despesas,
            SUM(CASE WHEN tipo = 'receita' THEN valor ELSE -valor END) as saldo
        FROM transacoes
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT 12
    '''
    
    resultados = conn.execute(query).fetchall()
    conn.close()
    
    dados = []
    for row in resultados:
        dados.append({
            'mes': row['mes'],
            'receitas': float(row['receitas']),
            'despesas': float(row['despesas']),
            'saldo': float(row['saldo'])
        })
    
    return jsonify(dados[::-1])  # Inverter para ordem cronológica

@app.route('/api/relatorios/categorias')
def api_categorias():
    conn = get_db_connection()
    
    receitas = conn.execute('''
        SELECT categoria, SUM(valor) as total 
        FROM transacoes 
        WHERE tipo = 'receita' 
        GROUP BY categoria 
        ORDER BY total DESC
    ''').fetchall()
    
    despesas = conn.execute('''
        SELECT categoria, SUM(valor) as total 
        FROM transacoes 
        WHERE tipo = 'despesa' 
        GROUP BY categoria 
        ORDER BY total DESC
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'receitas': [dict(row) for row in receitas],
        'despesas': [dict(row) for row in despesas]
    })

@app.route('/api/relatorios/detalhado')
def api_relatorio_detalhado():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    
    conn = get_db_connection()
    
    # Construir query base
    query = '''
        SELECT * FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND tipo = ?'
        params.append(tipo)
    
    query += ' ORDER BY data DESC, id DESC'
    
    transacoes = conn.execute(query, params).fetchall()
    
    # Calcular totais por tipo
    totais_query = '''
        SELECT 
            tipo,
            COUNT(*) as quantidade,
            SUM(valor) as total
        FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    totais_params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        totais_query += ' AND tipo = ?'
        totais_params.append(tipo)
    
    totais_query += ' GROUP BY tipo'
    
    totais_result = conn.execute(totais_query, totais_params).fetchall()
    
    totais = {'receita': {'quantidade': 0, 'total': 0}, 'despesa': {'quantidade': 0, 'total': 0}}
    for row in totais_result:
        totais[row['tipo']] = {
            'quantidade': row['quantidade'],
            'total': float(row['total'])
        }
    
    conn.close()
    
    return jsonify({
        'transacoes': [dict(transacao) for transacao in transacoes],
        'totais': totais,
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim,
            'tipo': tipo
        }
    })

@app.route('/relatorio/pdf')
def relatorio_pdf():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    
    # Buscar dados
    conn = get_db_connection()
    
    query = '''
        SELECT * FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND tipo = ?'
        params.append(tipo)
    
    query += ' ORDER BY data DESC'
    
    transacoes = conn.execute(query, params).fetchall()
    
    # Calcular totais
    receitas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita" AND data BETWEEN ? AND ?',
        (data_inicio, data_fim)
    ).fetchone()['total'] or 0
    
    despesas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa" AND data BETWEEN ? AND ?',
        (data_inicio, data_fim)
    ).fetchone()['total'] or 0
    
    saldo = receitas - despesas
    
    conn.close()
    
    # Gerar PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    # Título
    title = Paragraph(f'Relatório Financeiro - {data_inicio} a {data_fim}', title_style)
    elements.append(title)
    
    # Resumo
    resumo_data = [
        ['Receitas', formatar_moeda_pdf(receitas)],
        ['Despesas', formatar_moeda_pdf(despesas)],
        ['Saldo', formatar_moeda_pdf(saldo)]
    ]
    
    resumo_table = Table(resumo_data, colWidths=[300, 100])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(resumo_table)
    elements.append(Spacer(1, 20))
    
    # Tabela de transações
    if transacoes:
        table_data = [['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor']]
        
        for transacao in transacoes:
            table_data.append([
                transacao['data'],
                transacao['descricao'],
                transacao['categoria'],
                'Receita' if transacao['tipo'] == 'receita' else 'Despesa',
                formatar_moeda_pdf(transacao['valor'])
            ])
        
        transacoes_table = Table(table_data, colWidths=[60, 150, 80, 60, 60])
        transacoes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(transacoes_table)
    else:
        elements.append(Paragraph('Nenhuma transação encontrada para o período.', styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{data_inicio}_{data_fim}.pdf'
    
    return response

def formatar_moeda_pdf(valor):
    if valor is None:
        valor = 0
    return f'R$ {float(valor):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

# Inicialização
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)