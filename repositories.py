from models import Usuario, Transacao

class UsuarioRepository:
    def __init__(self, db_manager):
        self.db = db_manager

    def salvar(self, usuario: Usuario):
        with self.db.get_connection() as conn:
            conn.execute("INSERT INTO usuario (nome, email, senha_hash) VALUES (?, ?, ?)", 
                         (usuario.nome, usuario.email, usuario.senha_hash))
            conn.commit()

    def buscar_por_email(self, email):
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM usuario WHERE email = ?", (email,)).fetchone()
            if row: return Usuario(**row)
            return None

    def buscar_por_id(self, id_usuario):
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM usuario WHERE id = ?", (id_usuario,)).fetchone()
            if row: return Usuario(**row)
            return None

    # --- NOVAS FUNÇÕES DE SEGURANÇA E PERFIL ---
    def registrar_falha_login(self, email, tentativas, bloqueado_ate=None):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE usuario SET tentativas_login = ?, bloqueado_ate = ? WHERE email = ?", (tentativas, bloqueado_ate, email))
            conn.commit()

    def limpar_falhas_login(self, email):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE usuario SET tentativas_login = 0, bloqueado_ate = NULL WHERE email = ?", (email,))
            conn.commit()

    def atualizar_senha(self, email, nova_senha_hash):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE usuario SET senha_hash = ? WHERE email = ?", (nova_senha_hash, email))
            conn.commit()

    def atualizar_perfil(self, id_usuario, nome, email, nova_senha_hash=None):
        with self.db.get_connection() as conn:
            if nova_senha_hash:
                conn.execute("UPDATE usuario SET nome = ?, email = ?, senha_hash = ? WHERE id = ?", (nome, email, nova_senha_hash, id_usuario))
            else:
                conn.execute("UPDATE usuario SET nome = ?, email = ? WHERE id = ?", (nome, email, id_usuario))
            conn.commit()

    def atualizar_configuracoes(self, id_usuario, tema, input_pix):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE usuario SET tema = ?, input_pix = ? WHERE id = ?", (tema, input_pix, id_usuario))
            conn.commit()

class TransacaoRepository:
    def __init__(self, db_manager):
        self.db = db_manager

    def salvar(self, transacao: Transacao):
        with self.db.get_connection() as conn:
            conn.execute("INSERT INTO transacoes (usuario_id, tipo, categoria, descricao, data, valor, icone) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                         (transacao.usuario_id, transacao.tipo, transacao.categoria, transacao.descricao, transacao.data, transacao.valor_centavos, transacao.icone))
            conn.commit()

    def atualizar(self, id_transacao, usuario_id, tipo, categoria, descricao, data, valor_centavos):
        icone = 'bi-arrow-up-right' if tipo == 'ganho' else 'bi-cart3'
        with self.db.get_connection() as conn:
            # O WHERE valida tanto o ID da transação quanto o Dono (segurança extra)
            conn.execute("""
                UPDATE transacoes 
                SET tipo = ?, categoria = ?, descricao = ?, data = ?, valor = ?, icone = ?
                WHERE id = ? AND usuario_id = ?
            """, (tipo, categoria, descricao, data, valor_centavos, icone, id_transacao, usuario_id))
            conn.commit()

    def deletar(self, id_transacao, usuario_id):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM transacoes WHERE id = ? AND usuario_id = ?", (id_transacao, usuario_id))
            conn.commit()

    def buscar_por_mes(self, usuario_id, ano, mes):
        prefixo = f"{ano}-{mes:02d}-%"
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM transacoes WHERE usuario_id = ? AND data LIKE ? ORDER BY data DESC", (usuario_id, prefixo,)).fetchall()
            return [Transacao(id=r['id'], usuario_id=r['usuario_id'], tipo=r['tipo'], categoria=r['categoria'], descricao=r['descricao'], data=r['data'], valor_centavos=r['valor'], icone=r['icone']) for r in rows]

    def buscar_com_filtro(self, usuario_id, tipo=None, mes=None, ano=None):
        query = "SELECT * FROM transacoes WHERE usuario_id = ?"
        params = [usuario_id]
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)
        if mes and ano:
            query += " AND data LIKE ?"
            params.append(f"{ano}-{int(mes):02d}-%")
            
        query += " ORDER BY data DESC, id DESC"
        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Transacao(id=r['id'], usuario_id=r['usuario_id'], tipo=r['tipo'], categoria=r['categoria'], descricao=r['descricao'], data=r['data'], valor_centavos=r['valor'], icone=r['icone']) for r in rows]

    def obter_total_por_tipo_mes(self, usuario_id, tipo, ano, mes):
        prefixo = f"{ano}-{mes:02d}-%"
        with self.db.get_connection() as conn:
            return conn.execute("SELECT SUM(valor) FROM transacoes WHERE usuario_id = ? AND tipo = ? AND data LIKE ?", (usuario_id, tipo, prefixo)).fetchone()[0] or 0

    def agrupar_gastos_categoria(self, usuario_id, ano, mes):
        prefixo = f"{ano}-{mes:02d}-%"
        with self.db.get_connection() as conn:
            return conn.execute("SELECT categoria, SUM(valor) as total FROM transacoes WHERE usuario_id = ? AND tipo = 'gasto' AND data LIKE ? GROUP BY categoria ORDER BY total DESC", (usuario_id, prefixo,)).fetchall()

    def buscar_categorias_unicas(self, usuario_id, tipo):
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT categoria FROM transacoes WHERE usuario_id = ? AND tipo = ? ORDER BY categoria", (usuario_id, tipo)).fetchall()
            return [r['categoria'] for r in rows]