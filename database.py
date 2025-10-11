import sqlite3

def get_db_connection():
    conn = sqlite3.connect('livro_caixa.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            data DATE NOT NULL
        )
    ''')
    
    # Inserir dados de exemplo
    transacoes_exemplo = [
        ('Salário', 5000.00, 'receita', 'Salário', '2024-01-05'),
        ('Aluguel', 1500.00, 'despesa', 'Moradia', '2024-01-10'),
        ('Supermercado', 450.00, 'despesa', 'Alimentação', '2024-01-12'),
        ('Freelance', 1200.00, 'receita', 'Trabalho Extra', '2024-01-15'),
        ('Academia', 120.00, 'despesa', 'Saúde', '2024-01-20')
    ]
    
    for transacao in transacoes_exemplo:
        conn.execute('''
            INSERT OR IGNORE INTO transacoes (descricao, valor, tipo, categoria, data)
            VALUES (?, ?, ?, ?, ?)
        ''', transacao)
    
    conn.commit()
    conn.close()