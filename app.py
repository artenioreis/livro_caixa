from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from datetime import datetime, timedelta
import sqlite3
import io
import json
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
    
    # Inserir dados de exemplo
    transacoes_exemplo = [
        ('Salário Mensal', 5000.00, 'receita', 'Salário', '2024-01-05'),
        ('Aluguel', 1500.00, 'despesa', 'Moradia', '2024-01-10'),
        ('Supermercado', 450.00, 'despesa', 'Alimentação', '2024-01-12'),
        ('Freelance Site', 1200.00, 'receita', 'Freelance', '2024-01-15'),
        ('Academia', 120.00, 'despesa', 'Saúde', '2024-01-20'),
        ('Combustível', 200.00, 'despesa', 'Transporte', '2024-01-22'),
        ('Dividendos', 350.00, 'receita', 'Investimentos', '2024-01-25'),
        ('Restaurante', 80.00, 'despesa', 'Alimentação', '2024-01-28'),
        ('Curso Online', 299.00, 'despesa', 'Educação', '2024-02-01'),
        ('Venda Notebook', 1200.00, 'receita', 'Vendas', '2024-02-05')
    ]
    
    for transacao in transacoes_exemplo:
        conn.execute('''
            INSERT OR IGNORE INTO transacoes (descricao, valor, tipo, categoria, data)
            VALUES (?, ?, ?, ?, ?)
        ''', transacao)
    
    conn.commit()
    conn.close()

# Rotas principais
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

# API para transações
@app.route('/api/transacoes', methods=['GET', 'POST'])
def api_transacoes():
    conn = get_db_connection()
    
    if request.method == 'GET':
        # Buscar todas as transações
        transacoes = conn.execute('''
            SELECT t.*, c.cor 
            FROM transacoes t 
            LEFT JOIN categorias c ON t.categoria = c.nome AND t.tipo = c.tipo
            ORDER BY t.data DESC, t.id DESC
        ''').fetchall()
        
        result = []
        for transacao in transacoes:
            result.append({
                'id': transacao['id'],
                'descricao': transacao['descricao'],
                'valor': float(transacao['valor']),
                'tipo': transacao['tipo'],
                'categoria': transacao['categoria'],
                'cor': transacao['cor'] or '#6c757d',
                'data': transacao['data'],
                'created_at': transacao['created_at']
            })
        
        conn.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        try:
            conn.execute('''
                INSERT INTO transacoes (descricao, valor, tipo, categoria, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['descricao'],
                data['valor'],
                data['tipo'],
                data['categoria'],
                data['data']
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Transação adicionada com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/transacoes/<int:id>', methods=['PUT', 'DELETE'])
def transacao_detail(id):
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        
        try:
            conn.execute('''
                UPDATE transacoes 
                SET descricao = ?, valor = ?, tipo = ?, categoria = ?, data = ?
                WHERE id = ?
            ''', (
                data['descricao'],
                data['valor'],
                data['tipo'],
                data['categoria'],
                data['data'],
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Transação atualizada com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'DELETE':
        try:
            conn.execute('DELETE FROM transacoes WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Transação excluída com sucesso!'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)})

# API para categorias
@app.route('/api/categorias')
def api_categorias():
    conn = get_db_connection()
    
    categorias = conn.execute('''
        SELECT * FROM categorias ORDER BY tipo, nome
    ''').fetchall()
    
    result = {
        'receita': [],
        'despesa': []
    }
    
    for categoria in categorias:
        result[categoria['tipo']].append({
            'id': categoria['id'],
            'nome': categoria['nome'],
            'cor': categoria['cor']
        })
    
    conn.close()
    return jsonify(result)

# API para relatórios e dashboard
@app.route('/api/relatorios/saldo')
def saldo_total():
    conn = get_db_connection()
    
    # Saldo total
    receitas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita"'
    ).fetchone()['total'] or 0
    
    despesas = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa"'
    ).fetchone()['total'] or 0
    
    saldo = float(receitas) - float(despesas)
    
    # Últimos 30 dias
    data_30_dias = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    receitas_30 = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "receita" AND data >= ?',
        (data_30_dias,)
    ).fetchone()['total'] or 0
    
    despesas_30 = conn.execute(
        'SELECT SUM(valor) as total FROM transacoes WHERE tipo = "despesa" AND data >= ?',
        (data_30_dias,)
    ).fetchone()['total'] or 0
    
    saldo_30 = float(receitas_30) - float(despesas_30)
    
    conn.close()
    
    return jsonify({
        'geral': {
            'receitas': float(receitas),
            'despesas': float(despesas),
            'saldo': saldo
        },
        'ultimos_30_dias': {
            'receitas': float(receitas_30),
            'despesas': float(despesas_30),
            'saldo': saldo_30
        }
    })

@app.route('/api/relatorios/categorias')
def relatorio_categorias():
    conn = get_db_connection()
    
    categorias_receita = conn.execute('''
        SELECT categoria, SUM(valor) as total, COUNT(*) as quantidade,
               (SELECT cor FROM categorias WHERE nome = transacoes.categoria AND tipo = 'receita' LIMIT 1) as cor
        FROM transacoes 
        WHERE tipo = "receita" 
        GROUP BY categoria
        ORDER BY total DESC
    ''').fetchall()
    
    categorias_despesa = conn.execute('''
        SELECT categoria, SUM(valor) as total, COUNT(*) as quantidade,
               (SELECT cor FROM categorias WHERE nome = transacoes.categoria AND tipo = 'despesa' LIMIT 1) as cor
        FROM transacoes 
        WHERE tipo = "despesa" 
        GROUP BY categoria
        ORDER BY total DESC
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'receitas': [{
            'categoria': cat['categoria'],
            'total': float(cat['total']),
            'quantidade': cat['quantidade'],
            'cor': cat['cor'] or '#28a745'
        } for cat in categorias_receita],
        'despesas': [{
            'categoria': cat['categoria'],
            'total': float(cat['total']),
            'quantidade': cat['quantidade'],
            'cor': cat['cor'] or '#dc3545'
        } for cat in categorias_despesa]
    })

@app.route('/api/relatorios/mensal')
def relatorio_mensal():
    conn = get_db_connection()
    
    # Últimos 6 meses
    meses = []
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=30*i)
        meses.append(date.strftime('%Y-%m'))
    
    dados_mensais = []
    
    for mes in meses:
        receitas = conn.execute('''
            SELECT SUM(valor) as total FROM transacoes 
            WHERE tipo = "receita" AND strftime('%Y-%m', data) = ?
        ''', (mes,)).fetchone()['total'] or 0
        
        despesas = conn.execute('''
            SELECT SUM(valor) as total FROM transacoes 
            WHERE tipo = "despesa" AND strftime('%Y-%m', data) = ?
        ''', (mes,)).fetchone()['total'] or 0
        
        # Quantidade de transações
        qtd_receitas = conn.execute('''
            SELECT COUNT(*) as total FROM transacoes 
            WHERE tipo = "receita" AND strftime('%Y-%m', data) = ?
        ''', (mes,)).fetchone()['total'] or 0
        
        qtd_despesas = conn.execute('''
            SELECT COUNT(*) as total FROM transacoes 
            WHERE tipo = "despesa" AND strftime('%Y-%m', data) = ?
        ''', (mes,)).fetchone()['total'] or 0
        
        dados_mensais.append({
            'mes': mes,
            'receitas': float(receitas),
            'despesas': float(despesas),
            'saldo': float(receitas) - float(despesas),
            'quantidade_transacoes': qtd_receitas + qtd_despesas
        })
    
    conn.close()
    return jsonify(dados_mensais)

# NOVAS ROTAS PARA RELATÓRIOS DETALHADOS
@app.route('/api/relatorios/detalhado')
def relatorio_detalhado():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    categoria = request.args.get('categoria', 'todas')
    
    conn = get_db_connection()
    
    # Construir query dinâmica
    query = '''
        SELECT t.*, c.cor 
        FROM transacoes t 
        LEFT JOIN categorias c ON t.categoria = c.nome AND t.tipo = c.tipo
        WHERE t.data BETWEEN ? AND ?
    '''
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND t.tipo = ?'
        params.append(tipo)
    
    if categoria != 'todas':
        query += ' AND t.categoria = ?'
        params.append(categoria)
    
    query += ' ORDER BY t.data, t.id'
    
    transacoes = conn.execute(query, params).fetchall()
    
    result = []
    for transacao in transacoes:
        result.append({
            'id': transacao['id'],
            'descricao': transacao['descricao'],
            'valor': float(transacao['valor']),
            'tipo': transacao['tipo'],
            'categoria': transacao['categoria'],
            'cor': transacao['cor'] or '#6c757d',
            'data': transacao['data']
        })
    
    # Calcular totais
    query_totais = '''
        SELECT 
            tipo,
            COUNT(*) as quantidade,
            SUM(valor) as total
        FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    params_totais = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query_totais += ' AND tipo = ?'
        params_totais.append(tipo)
    
    if categoria != 'todas':
        query_totais += ' AND categoria = ?'
        params_totais.append(categoria)
    
    query_totais += ' GROUP BY tipo'
    
    totais = conn.execute(query_totais, params_totais).fetchall()
    
    # Estatísticas adicionais
    total_transacoes = len(transacoes)
    maior_receita = conn.execute('''
        SELECT MAX(valor) as max FROM transacoes 
        WHERE tipo = "receita" AND data BETWEEN ? AND ?
    ''', [data_inicio, data_fim]).fetchone()['max'] or 0
    
    maior_despesa = conn.execute('''
        SELECT MAX(valor) as max FROM transacoes 
        WHERE tipo = "despesa" AND data BETWEEN ? AND ?
    ''', [data_inicio, data_fim]).fetchone()['max'] or 0
    
    conn.close()
    
    totais_dict = {}
    for total in totais:
        totais_dict[total['tipo']] = {
            'quantidade': total['quantidade'],
            'total': float(total['total'])
        }
    
    return jsonify({
        'transacoes': result,
        'totais': totais_dict,
        'estatisticas': {
            'total_transacoes': total_transacoes,
            'maior_receita': float(maior_receita),
            'maior_despesa': float(maior_despesa)
        },
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim
        },
        'filtros': {
            'tipo': tipo,
            'categoria': categoria
        }
    })

@app.route('/relatorio/pdf')
def gerar_pdf():
    # Parâmetros do relatório
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    categoria = request.args.get('categoria', 'todas')
    
    # Buscar dados
    conn = get_db_connection()
    
    query = '''
        SELECT t.*, c.cor 
        FROM transacoes t 
        LEFT JOIN categorias c ON t.categoria = c.nome AND t.tipo = c.tipo
        WHERE t.data BETWEEN ? AND ?
    '''
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND t.tipo = ?'
        params.append(tipo)
    
    if categoria != 'todas':
        query += ' AND t.categoria = ?'
        params.append(categoria)
    
    query += ' ORDER BY t.data, t.tipo'
    
    transacoes = conn.execute(query, params).fetchall()
    
    # Calcular totais
    query_totais = '''
        SELECT 
            tipo,
            COUNT(*) as quantidade,
            SUM(valor) as total
        FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    params_totais = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query_totais += ' AND tipo = ?'
        params_totais.append(tipo)
    
    if categoria != 'todas':
        query_totais += ' AND categoria = ?'
        params_totais.append(categoria)
    
    query_totais += ' GROUP BY tipo'
    
    totais = conn.execute(query_totais, params_totais).fetchall()
    
    conn.close()
    
    # Criar PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)
    
    # Estilos
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=1  # Centralizado
    )
    
    estilo_subtitulo = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#7f8c8d'),
        spaceAfter=20
    )
    
    # Conteúdo do PDF
    conteudo = []
    
    # Título
    titulo = Paragraph("RELATÓRIO FINANCEIRO DETALHADO", estilo_titulo)
    conteudo.append(titulo)
    
    # Informações do período
    data_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M')
    periodo_texto = f"Período: {formatar_data_ptbr(data_inicio)} a {formatar_data_ptbr(data_fim)}"
    tipo_texto = f"Tipo: {tipo.capitalize()}" if tipo != 'todos' else "Tipo: Todos"
    categoria_texto = f"Categoria: {categoria}" if categoria != 'todas' else "Categoria: Todas"
    
    info_periodo = f"{periodo_texto} | {tipo_texto} | {categoria_texto} | Emitido em: {data_emissao}"
    conteudo.append(Paragraph(info_periodo, estilo_subtitulo))
    conteudo.append(Spacer(1, 20))
    
    # Tabela de transações
    if transacoes:
        # Cabeçalho da tabela
        dados_tabela = [['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor (R$)']]
        
        for transacao in transacoes:
            data_formatada = formatar_data_ptbr(transacao['data'])
            tipo_formatado = 'Receita' if transacao['tipo'] == 'receita' else 'Despesa'
            valor_formatado = f"R$ {transacao['valor']:,.2f}"
            
            dados_tabela.append([
                data_formatada,
                transacao['descricao'],
                transacao['categoria'],
                tipo_formatado,
                valor_formatado
            ])
        
        # Criar tabela
        tabela = Table(dados_tabela, colWidths=[60, 180, 80, 60, 80])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        conteudo.append(tabela)
        conteudo.append(Spacer(1, 30))
    
    # Resumo
    total_receitas = 0
    total_despesas = 0
    
    for total in totais:
        if total['tipo'] == 'receita':
            total_receitas = float(total['total'])
        else:
            total_despesas = float(total['total'])
    
    saldo = total_receitas - total_despesas
    
    # Tabela de resumo
    dados_resumo = [
        ['RESUMO DO PERÍODO', ''],
        ['Total de Receitas', f'R$ {total_receitas:,.2f}'],
        ['Total de Despesas', f'R$ {total_despesas:,.2f}'],
        ['SALDO FINAL', f'R$ {saldo:,.2f}']
    ]
    
    tabela_resumo = Table(dados_resumo, colWidths=[200, 150])
    tabela_resumo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Destacar saldo
    if saldo >= 0:
        cor_saldo = colors.HexColor('#27ae60')
    else:
        cor_saldo = colors.HexColor('#e74c3c')
    
    tabela_resumo.setStyle(TableStyle([
        ('BACKGROUND', (0, 3), (-1, 3), cor_saldo),
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.white),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
    ]))
    
    conteudo.append(tabela_resumo)
    
    # Gerar PDF
    doc.build(conteudo)
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    
    nome_arquivo = f'relatorio_financeiro_{data_inicio}_{data_fim}.pdf'
    if tipo != 'todos':
        nome_arquivo = f'relatorio_{tipo}_{data_inicio}_{data_fim}.pdf'
    
    response.headers['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
    
    return response

@app.route('/api/relatorios/exportar-csv')
def exportar_csv():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo = request.args.get('tipo', 'todos')
    
    conn = get_db_connection()
    
    query = '''
        SELECT * FROM transacoes 
        WHERE data BETWEEN ? AND ?
    '''
    params = [data_inicio, data_fim]
    
    if tipo != 'todos':
        query += ' AND tipo = ?'
        params.append(tipo)
    
    query += ' ORDER BY data, tipo'
    
    transacoes = conn.execute(query, params).fetchall()
    conn.close()
    
    # Criar CSV
    output = io.StringIO()
    output.write('Data,Descrição,Categoria,Tipo,Valor\n')
    
    for transacao in transacoes:
        data_formatada = formatar_data_ptbr(transacao['data'])
        output.write(f'"{data_formatada}","{transacao["descricao"]}","{transacao["categoria"]}","{transacao["tipo"]}",{transacao["valor"]}\n')
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{data_inicio}_{data_fim}.csv'
    
    return response

# Funções auxiliares
def formatar_data_ptbr(data_iso):
    """Converte data ISO para formato brasileiro"""
    try:
        data_obj = datetime.strptime(data_iso, '%Y-%m-%d')
        return data_obj.strftime('%d/%m/%Y')
    except:
        return data_iso

# Rota para estatísticas em tempo real
@app.route('/api/estatisticas/tempo-real')
def estatisticas_tempo_real():
    conn = get_db_connection()
    
    # Transações do dia
    hoje = datetime.now().strftime('%Y-%m-%d')
    transacoes_hoje = conn.execute('''
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END) as receitas,
               SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END) as despesas
        FROM transacoes 
        WHERE data = ?
    ''', (hoje,)).fetchone()
    
    # Próximas despesas (próximos 7 dias)
    data_futura = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    proximas_despesas = conn.execute('''
        SELECT descricao, valor, data 
        FROM transacoes 
        WHERE tipo = 'despesa' AND data BETWEEN ? AND ?
        ORDER BY data
        LIMIT 5
    ''', (hoje, data_futura)).fetchall()
    
    # Categoria com maior gasto no mês
    mes_atual = datetime.now().strftime('%Y-%m')
    categoria_maior_gasto = conn.execute('''
        SELECT categoria, SUM(valor) as total
        FROM transacoes 
        WHERE tipo = 'despesa' AND strftime('%Y-%m', data) = ?
        GROUP BY categoria 
        ORDER BY total DESC 
        LIMIT 1
    ''', (mes_atual,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'hoje': {
            'transacoes': transacoes_hoje['total'] or 0,
            'receitas': float(transacoes_hoje['receitas'] or 0),
            'despesas': float(transacoes_hoje['despesas'] or 0)
        },
        'proximas_despesas': [{
            'descricao': despesa['descricao'],
            'valor': float(despesa['valor']),
            'data': despesa['data']
        } for despesa in proximas_despesas],
        'categoria_maior_gasto': {
            'categoria': categoria_maior_gasto['categoria'] if categoria_maior_gasto else 'Nenhuma',
            'total': float(categoria_maior_gasto['total']) if categoria_maior_gasto else 0
        } if categoria_maior_gasto else None
    })

# Inicialização
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)