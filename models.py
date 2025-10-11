class Transacao:
    def __init__(self, descricao, valor, tipo, categoria, data):
        self.descricao = descricao
        self.valor = valor
        self.tipo = tipo
        self.categoria = categoria
        self.data = data
    
    def to_dict(self):
        return {
            'descricao': self.descricao,
            'valor': self.valor,
            'tipo': self.tipo,
            'categoria': self.categoria,
            'data': self.data
        }