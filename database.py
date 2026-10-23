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
            
            # 1. Criação das tabelas base (se ainda não existirem)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
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
            
            # 2. MOTOR DE MIGRAÇÃO INTELIGENTE (Não apaga dados, apenas adiciona colunas novas)
            # Ele lê a estrutura atual da tabela "usuario"
            cursor.execute("PRAGMA table_info(usuario)")
            colunas_usuario = [col['name'] for col in cursor.fetchall()]

            # Verifica e adiciona cada coluna caso ela não exista
            if 'telefone' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN telefone TEXT DEFAULT ''")
                
            if 'tema' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN tema TEXT DEFAULT 'light'")
                
            if 'input_pix' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN input_pix BOOLEAN DEFAULT 0")
                
            if 'tentativas_login' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN tentativas_login INTEGER DEFAULT 0")
                
            if 'bloqueado_ate' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN bloqueado_ate TEXT")
                
            if 'codigo_recuperacao' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN codigo_recuperacao TEXT")

            if 'data_exclusao' not in colunas_usuario:
                cursor.execute("ALTER TABLE usuario ADD COLUMN data_exclusao TEXT")

            conn.commit()

            conn.commit()