from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
import sqlite3
import socket
import pandas as pd
from io import BytesIO
import getpass

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

DATABASE = 'chamados.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn

def registrar_log(operacao, status):
    hostname = socket.gethostname()
    username = getpass.getuser()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha_log = f"[{agora}] Host: {hostname} | Usuário: {username} | Operação: {operacao} | status: {status}\n"
    with open('log.txt', 'a', encoding='utf-8') as arquivo_log:
        arquivo_log.write(linha_log)

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_ocorrencia DATE,
            hr_inicio TIME,
            hr_fim TIME,
            chamado TEXT,
            localidade TEXT,
            n_medidor TEXT,
            uc_instalacao TEXT,
            responsavel TEXT,
            descricao TEXT,
            status TEXT DEFAULT 'Aberto'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=["GET", "POST"])
def index():
    conn = get_db_connection()

    if request.method == "POST":
        chamado = request.form.get("chamado")
        data_ocorrencia = request.form.get("data_ocorrencia")      
        hr_inicio = request.form.get("hr_inicio")       
        hr_fim = request.form.get("hr_fim")             
        localidade = request.form.get("localidade")
        n_medidor = request.form.get("n_medidor")
        uc_instalacao = request.form.get("uc_instalacao")
        responsavel = request.form.get("responsavel")
        descricao = request.form.get("descricao")
        status = "Aberto"

        conn.execute('''
            INSERT INTO chamados (
                data_ocorrencia, chamado, localidade, n_medidor,
                uc_instalacao, responsavel, descricao, status,
                hr_inicio, hr_fim
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data_ocorrencia, chamado, localidade, n_medidor, uc_instalacao,
              responsavel, descricao, status, hr_inicio, hr_fim))

        conn.commit()
        conn.close()

        registrar_log('Inserção', f'Chamado inserido: "{chamado}" em {localidade}, medidor {n_medidor}, status {status}')
        return redirect(url_for('index', success='create'))

    success = request.args.get('success')

    filtro_localidade = request.args.get('localidade')
    filtro_status = request.args.get('status')
    filtro_data = request.args.get('data_ocorrencia')

    query = 'SELECT * FROM chamados WHERE 1=1'
    params = []

    if filtro_localidade and filtro_localidade != 'Todos':
        query += ' AND localidade = ?'
        params.append(filtro_localidade)
    
    if filtro_status and filtro_status != 'Todos':
        query += ' AND status = ?'
        params.append(filtro_status)
    
    if filtro_data:
        query += ' AND data_ocorrencia = ?'
        params.append(filtro_data)

    chamados = conn.execute(query, params).fetchall()

    datas_ocorrencia = conn.execute('SELECT DISTINCT data_ocorrencia FROM chamados WHERE data_ocorrencia IS NOT NULL AND data_ocorrencia != ""').fetchall()
    localidades = conn.execute('SELECT DISTINCT localidade FROM chamados WHERE localidade IS NOT NULL AND localidade != ""').fetchall()
    status = conn.execute('SELECT DISTINCT status FROM chamados WHERE status IS NOT NULL AND status != ""').fetchall()

    conn.close()

    return render_template(
        'form.html',
        success=success,
        localidades=[row['localidade'] for row in localidades],
        status=[row['status'] for row in status],
        datas_ocorrencia=[row['data_ocorrencia'] for row in datas_ocorrencia],
        chamados=chamados,
        now=datetime.now(),
        filtro_localidade=filtro_localidade or 'Todos',
        filtro_status=filtro_status or 'Todos',
        filtro_data=filtro_data or ''
    )

@app.route('/editar/<int:id>', methods=['POST'])
def editar_chamado(id):
    conn = get_db_connection()
    chamado_antigo = conn.execute('SELECT * FROM chamados WHERE id = ?', (id,)).fetchone()

    if not chamado_antigo:
        conn.close()
        return "Chamado não encontrado", 404

    status = request.form.get('status')
    hr_fim = request.form.get('hr_fim')

    conn.execute('UPDATE chamados SET status = ?, hr_fim = ? WHERE id = ?', (status, hr_fim, id))
    conn.commit()
    conn.close()

    registrar_log('Edição', f'Status do chamado ID {id} alterado. De: "{chamado_antigo["status"]}" Para: "{status}"')
    return redirect(url_for('index', success='edit'))

@app.route('/deletar_chamado/<int:id>', methods=['POST'])
def deletar_chamado(id):
    conn = get_db_connection()
    chamado_antigo = conn.execute('SELECT * FROM chamados WHERE id = ?', (id,)).fetchone()

    if not chamado_antigo:
        conn.close()
        return "Chamado não encontrado", 404

    status = "cancelado"
    conn.execute('UPDATE chamados SET status = ? WHERE id = ?', (status, id,)).fetchone()
    conn.commit()
    conn.close()
    
    registrar_log('Edição', f'Status do chamado ID {id} alterado. De: "{chamado_antigo["status"]}" Para: "{status}"')
    return redirect(url_for('index', success='cancelado'))

@app.route('/exportar_excel')
def exportar_excel():
    try:
        conn = get_db_connection()
        
        filtro_localidade = request.args.get('localidade')
        filtro_status = request.args.get('status')
        filtro_data = request.args.get('data_ocorrencia')  # <-- ADICIONADO AQUI

        query = 'SELECT * FROM chamados WHERE 1=1'
        params = []

        if filtro_localidade and filtro_localidade != 'Todos':
            query += ' AND localidade = ?'
            params.append(filtro_localidade)

        if filtro_status and filtro_status != 'Todos':
            query += ' AND status = ?'
            params.append(filtro_status)

        if filtro_data:
            query += ' AND data_ocorrencia = ?'   # <-- ADICIONADO AQUI
            params.append(filtro_data)

        df = pd.read_sql_query(query, conn, params=params if params else None)
        conn.close()

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Chamados', index=False)
        writer.close()
        output.seek(0)

        filename = "chamados_exportados"
        if filtro_localidade and filtro_localidade != 'Todos':
            filename += f"_{filtro_localidade}"
        if filtro_status and filtro_status != 'Todos':
            filename += f"_{filtro_status}"
        if filtro_data:
            filename += f"_{filtro_data}"
        filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        registrar_log('Exportação', f'Dados exportados para Excel com filtros: localidade={filtro_localidade}, status={filtro_status}, data_ocorrencia={filtro_data}')

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        registrar_log('Exportação', f'Falha na exportação: {str(e)}')
        return redirect(url_for('index', error='export'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
