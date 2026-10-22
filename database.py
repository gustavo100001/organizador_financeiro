import sqlite3

class DatabaseManager:
    def __init__(self, db_name='financas.db'):
        self.db_name = db_name

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Tabela de Usuários atualizada com Temas, Pix e Segurança
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    tema TEXT DEFAULT 'light',
                    input_pix BOOLEAN DEFAULT 0,
                    tentativas_login INTEGER DEFAULT 0,
                    bloqueado_ate TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    descricao TEXT,
                    data DATE NOT NULL,
                    valor INTEGER NOT NULL, 
                    icone TEXT NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuario (id)
                )
            ''')
            conn.commit()