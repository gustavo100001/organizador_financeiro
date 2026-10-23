class Usuario:
    def __init__(self, nome, email, senha_hash, telefone="", tema='light', input_pix=0, tentativas_login=0, bloqueado_ate=None, codigo_recuperacao=None, data_cadastro=None, data_exclusao=None, id=None):
        self.id = id
        self.nome = nome
        self.email = email
        self.telefone = telefone
        self.senha_hash = senha_hash
        self.tema = tema
        self.input_pix = input_pix
        self.tentativas_login = tentativas_login
        self.bloqueado_ate = bloqueado_ate
        self.codigo_recuperacao = codigo_recuperacao
        self.data_cadastro = data_cadastro
        self.data_exclusao = data_exclusao # Adicionado aqui!
        
class Transacao:
    # Adicionado o usuario_id no modelo
    def __init__(self, usuario_id, tipo, categoria, data, valor_centavos, icone, descricao="", id=None):
        self.id = id
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.categoria = categoria
        self.descricao = descricao
        self.data = data
        self.valor_centavos = valor_centavos
        self.icone = icone

    def formatar_valor(self):
        return f"{(self.valor_centavos / 100.0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')