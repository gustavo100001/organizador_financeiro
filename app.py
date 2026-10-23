from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal
from database import DatabaseManager
from models import Usuario, Transacao
from repositories import UsuarioRepository, TransacaoRepository
import random

app = Flask(__name__)
# OBRIGATÓRIO: Chave secreta para criptografar os cookies de sessão dos usuários
app.secret_key = 'sua_chave_secreta_super_segura_aqui_mude_em_producao'

db_manager = DatabaseManager('financas.db')
db_manager.init_db()

usuario_repo = UsuarioRepository(db_manager)
transacao_repo = TransacaoRepository(db_manager)

MESES = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

# MIDDLEWARE DE PROTEÇÃO: Se não tiver sessão ativa, é expulso para o Login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Injeta os dados APENAS do usuário logado na interface
@app.context_processor
def inject_globals():
    if 'usuario_id' in session:
        uid = session['usuario_id']
        usr = usuario_repo.buscar_por_id(uid)
        hoje = datetime.now().strftime('%Y-%m-%d')
        cats_ganho = transacao_repo.buscar_categorias_unicas(uid, 'ganho')
        cats_gasto = transacao_repo.buscar_categorias_unicas(uid, 'gasto')
        return dict(usuario_global=usr, hoje_data=hoje, cats_ganho=cats_ganho, cats_gasto=cats_gasto)
    return dict()


# ==========================================
# 1. ROTAS DE AUTENTICAÇÃO E SEGURANÇA
# ==========================================

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email').strip().lower()
        telefone = request.form.get('telefone').strip()
        senha = request.form.get('senha')
        
        # VALIDAÇÃO DA SENHA: Mínimo de 6 caracteres (letras, números ou símbolos)
        if not senha or len(senha) < 6:
            flash('A senha deve conter no mínimo 6 caracteres.', 'danger')
            return redirect(url_for('cadastro'))

        if usuario_repo.buscar_por_email(email):
            flash('Este e-mail já está registado.', 'danger')
            return redirect(url_for('cadastro'))

        senha_criptografada = generate_password_hash(senha)
        usuario_repo.salvar(Usuario(nome=nome, email=email, telefone=telefone, senha_hash=senha_criptografada))
        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        senha = request.form.get('senha')
        user = usuario_repo.buscar_por_email(email)
        
        if user:
            agora = datetime.now()
            if user.bloqueado_ate:
                bloqueio = datetime.strptime(user.bloqueado_ate, "%Y-%m-%d %H:%M:%S")
                if agora < bloqueio:
                    restante = (bloqueio - agora).seconds // 60 + 1
                    flash(f'Segurança: Conta bloqueada. Tente novamente em {restante} minuto(s).', 'danger')
                    return render_template('login.html')

            if check_password_hash(user.senha_hash, senha):
                # VERIFICA SE A CONTA ESTÁ AGENDADA PARA EXCLUSÃO
                if user.data_exclusao:
                    data_limite = datetime.strptime(user.data_exclusao, "%Y-%m-%d %H:%M:%S")
                    if agora <= data_limite:
                        # Cria uma sessão temporária e envia para a tela de decisão
                        session['recuperacao_usuario_id'] = user.id
                        return redirect(url_for('recuperar_conta'))
                    else:
                        flash('Esta conta foi permanentemente excluída e já não pode ser acedida.', 'danger')
                        return render_template('login.html')

                # Login normal se não houver exclusão agendada
                usuario_repo.limpar_falhas_login(email)
                session['usuario_id'] = user.id
                return redirect(url_for('index'))
            else:
                falhas = user.tentativas_login + 1
                if falhas >= 5:
                    bloqueio_ate = (agora + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                    usuario_repo.registrar_falha_login(email, falhas, bloqueio_ate)
                    flash('Segurança: Conta bloqueada por 5 minutos devido a múltiplas falhas.', 'danger')
                else:
                    usuario_repo.registrar_falha_login(email, falhas)
                    flash(f'Senha incorreta. Tentativa {falhas}/5.', 'danger')
        else:
            flash('E-mail não encontrado.', 'danger')
            
    return render_template('login.html')

@app.route('/recuperar_conta', methods=['GET', 'POST'])
def recuperar_conta():
    # Verifica se o utilizador passou pelo login com sucesso
    uid_recuperacao = session.get('recuperacao_usuario_id')
    if not uid_recuperacao:
        return redirect(url_for('login'))
        
    user = usuario_repo.buscar_por_id(uid_recuperacao)
    
    if request.method == 'POST':
        acao = request.form.get('acao')
        
        if acao == 'restaurar':
            # Cancela a exclusão, limpa a sessão temporária e faz o login real
            usuario_repo.cancelar_exclusao(uid_recuperacao)
            usuario_repo.limpar_falhas_login(user.email)
            session.pop('recuperacao_usuario_id', None)
            session['usuario_id'] = uid_recuperacao
            flash('Bem-vindo de volta! A exclusão foi cancelada e a sua conta está totalmente ativa.', 'success')
            return redirect(url_for('index'))
            
        elif acao == 'manter_exclusao':
            # Limpa a sessão temporária e volta para o login
            session.pop('recuperacao_usuario_id', None)
            flash('A sua conta continua agendada para exclusão.', 'info')
            return redirect(url_for('login'))

    # Para exibir a data limite formatada no HTML
    data_formatada = datetime.strptime(user.data_exclusao, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    return render_template('recuperar_conta.html', data_limite=data_formatada)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        passo = request.form.get('passo')
        
        # PASSO 1: O utilizador informa o e-mail para receber o código
        if passo == '1':
            email = request.form.get('email').strip().lower()
            user = usuario_repo.buscar_por_email(email)
            if user:
                # Gera um código aleatório de 6 dígitos
                codigo = str(random.randint(100000, 999999))
                usuario_repo.salvar_codigo_recuperacao(email, codigo)
                
                # Simulação de envio por SMS/E-mail (Exibe no terminal e na tela)
                print(f"\n[SISTEMA SMS/EMAIL] O código para {user.nome} ({user.telefone}) é: {codigo}\n")
                flash(f'Simulação de Envio: Um SMS foi enviado para {user.telefone} com o código: {codigo}', 'info')
                
                return render_template('recuperar_senha.html', passo=2, email=email)
            else:
                flash('E-mail não encontrado no sistema.', 'danger')
                return redirect(url_for('recuperar_senha'))
                
        # PASSO 2: O utilizador insere o código e a nova senha
        elif passo == '2':
            email = request.form.get('email')
            codigo_digitado = request.form.get('codigo')
            nova_senha = request.form.get('nova_senha')
            
            if usuario_repo.validar_codigo(email, codigo_digitado):
                usuario_repo.atualizar_senha(email, generate_password_hash(nova_senha))
                usuario_repo.salvar_codigo_recuperacao(email, None) # Invalida o código após uso
                usuario_repo.limpar_falhas_login(email)
                flash('Senha redefinida com sucesso! Pode fazer login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Código de verificação incorreto.', 'danger')
                return render_template('recuperar_senha.html', passo=2, email=email)

    return render_template('recuperar_senha.html', passo=1)

# ==========================================
# 2. ROTAS DO PERFIL E CONFIGURAÇÕES
# ==========================================

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    uid = session['usuario_id']
    user = usuario_repo.buscar_por_id(uid)
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email').strip().lower()
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')

        if not check_password_hash(user.senha_hash, senha_atual):
            flash('A senha atual está incorreta.', 'danger')
            return redirect(url_for('editar_perfil'))

        hash_nova = generate_password_hash(nova_senha) if nova_senha else None
        usuario_repo.atualizar_perfil(uid, nome, email, hash_nova)
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil'))
        
    return render_template('editar_perfil.html', user=user)

@app.route('/perfil/excluir', methods=['GET', 'POST'])
@login_required
def excluir_conta():
    uid = session['usuario_id']
    user = usuario_repo.buscar_por_id(uid)
    passo = request.args.get('passo', '1')

    if request.method == 'POST':
        senha = request.form.get('senha')
        
        # Verifica se a senha está correta
        if not check_password_hash(user.senha_hash, senha):
            flash('Senha incorreta. A exclusão foi cancelada por segurança.', 'danger')
            return redirect(url_for('excluir_conta', passo='2'))
        
        # Agenda a exclusão para 30 dias a partir de hoje
        data_exclusao = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        usuario_repo.solicitar_exclusao(uid, data_exclusao)
        
        # Desloga o utilizador
        session.clear()
        flash('Sua conta foi agendada para exclusão e será apagada permanentemente em 30 dias.', 'info')
        return redirect(url_for('login'))
        
    return render_template('excluir_conta.html', passo=passo)

@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    uid = session['usuario_id']
    if request.method == 'POST':
        tema = request.form.get('tema')
        input_pix = 1 if request.form.get('input_pix') == 'on' else 0
        usuario_repo.atualizar_configuracoes(uid, tema, input_pix)
        flash('Configurações aplicadas!', 'success')
        return redirect(url_for('perfil'))
    return render_template('configuracoes.html')


# ==========================================
# 3. ROTAS PRINCIPAIS DO SISTEMA
# ==========================================

@app.route('/')
@login_required
def index():
    uid = session['usuario_id']
    agora = datetime.now()
    mes_atual = int(request.args.get('mes', agora.month))
    ano_atual = int(request.args.get('ano', agora.year))
    
    mes_ant = 12 if mes_atual == 1 else mes_atual - 1
    ano_ant = ano_atual - 1 if mes_atual == 1 else ano_atual
    mes_prox = 1 if mes_atual == 12 else mes_atual + 1
    ano_prox = ano_atual + 1 if mes_atual == 12 else ano_atual

    ganhos = transacao_repo.obter_total_por_tipo_mes(uid, 'ganho', ano_atual, mes_atual) / 100.0
    gastos = transacao_repo.obter_total_por_tipo_mes(uid, 'gasto', ano_atual, mes_atual) / 100.0
    transacoes = transacao_repo.buscar_por_mes(uid, ano_atual, mes_atual)[:5]
        
    return render_template('index.html', 
                           mes_nome=MESES[mes_atual], ano=ano_atual,
                           mes_ant=mes_ant, ano_ant=ano_ant, mes_prox=mes_prox, ano_prox=ano_prox,
                           ganhos=f"{ganhos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           gastos=f"{gastos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           transacoes=transacoes)

@app.route('/transacoes')
@login_required
def transacoes():
    uid = session['usuario_id']
    tipo_filtro = request.args.get('tipo', '')
    mes_filtro = request.args.get('mes', str(datetime.now().month))
    ano_filtro = request.args.get('ano', str(datetime.now().year))
    
    lista = transacao_repo.buscar_com_filtro(uid, tipo_filtro, mes_filtro, ano_filtro)
    return render_template('transacoes.html', transacoes=lista, tipo_f=tipo_filtro, mes_f=mes_filtro, ano_f=ano_filtro, meses=MESES)

@app.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    uid = session['usuario_id']
    tipo = request.form.get('tipo')
    categoria = request.form.get('categoria').strip()
    descricao = request.form.get('descricao', '').strip()
    valor_centavos = int(Decimal(request.form.get('valor').replace(',', '.')) * 100)
    data = request.form.get('data') or datetime.now().strftime('%Y-%m-%d')
    icone = 'bi-arrow-up-right' if tipo == 'ganho' else 'bi-cart3'
    
    transacao_repo.salvar(Transacao(uid, tipo, categoria, data, valor_centavos, icone, descricao))
    return redirect(request.referrer)

@app.route('/editar/<int:id>', methods=['POST'])
@login_required
def editar(id):
    uid = session['usuario_id']
    tipo = request.form.get('tipo')
    categoria = request.form.get('categoria').strip()
    descricao = request.form.get('descricao', '').strip()
    valor_centavos = int(Decimal(request.form.get('valor').replace(',', '.')) * 100)
    data = request.form.get('data') or datetime.now().strftime('%Y-%m-%d')
    
    transacao_repo.atualizar(id, uid, tipo, categoria, descricao, data, valor_centavos)
    return redirect(request.referrer)

@app.route('/deletar/<int:id>', methods=['POST'])
@login_required
def deletar(id):
    uid = session['usuario_id']
    transacao_repo.deletar(id, uid)
    return redirect(request.referrer)

@app.route('/relatorios')
@login_required
def relatorios():
    uid = session['usuario_id']
    agora = datetime.now()
    mes_atual = int(request.args.get('mes', agora.month))
    ano_atual = int(request.args.get('ano', agora.year))

    receitas = transacao_repo.obter_total_por_tipo_mes(uid, 'ganho', ano_atual, mes_atual) / 100.0
    despesas = transacao_repo.obter_total_por_tipo_mes(uid, 'gasto', ano_atual, mes_atual) / 100.0
    saldo = receitas - despesas

    dados_cat = transacao_repo.agrupar_gastos_categoria(uid, ano_atual, mes_atual)
    total_gastos_mes = sum(d['total'] for d in dados_cat)
    
    categorias_relatorio = []
    for d in dados_cat:
        percent = (d['total'] / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
        categorias_relatorio.append({
            'nome': d['categoria'],
            'valor_formatado': f"{(d['total'] / 100.0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'percent': percent
        })

    evol_labels, evol_gastos = [], []
    for i in range(5, -1, -1):
        m = agora.month - i
        a = agora.year
        if m <= 0:
            m += 12; a -= 1
        evol_labels.append(f"{m:02d}/{str(a)[2:]}")
        evol_gastos.append(transacao_repo.obter_total_por_tipo_mes(uid, 'gasto', a, m) / 100.0)

    return render_template('relatorios.html', 
                           mes_nome=MESES[mes_atual], ano=ano_atual, mes_atual=mes_atual, ano_atual=ano_atual,
                           receitas=f"{receitas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           despesas=f"{despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           saldo=f"{saldo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           categorias_relatorio=categorias_relatorio, evol_labels=evol_labels, evol_gastos=evol_gastos)

@app.route('/imprimir')
@login_required
def imprimir():
    uid = session['usuario_id']
    agora = datetime.now()
    mes_filtro = request.args.get('mes', agora.month, type=int)
    ano_filtro = request.args.get('ano', agora.year, type=int)
    receitas = transacao_repo.obter_total_por_tipo_mes(uid, 'ganho', ano_filtro, mes_filtro) / 100.0
    despesas = transacao_repo.obter_total_por_tipo_mes(uid, 'gasto', ano_filtro, mes_filtro) / 100.0
    transacoes = transacao_repo.buscar_por_mes(uid, ano_filtro, mes_filtro)
    
    return render_template('imprimir.html', 
                           mes_nome=MESES[mes_filtro], ano=ano_filtro, 
                           receitas=f"{receitas:,.2f}", despesas=f"{despesas:,.2f}", 
                           saldo=f"{(receitas-despesas):,.2f}", transacoes=transacoes)


if __name__ == '__main__':
    app.run(debug=True)