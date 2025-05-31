from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
import sqlite3
import socket
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

DATABASE = 'chamados.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn


def registrar_log(operacao, status):
    hostname = socket.gethostname()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha_log = f"[{agora}] Host: {hostname} | Operação: {operacao} | status: {status}\n"
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
        data_ocorrencia = request.form.get("data_ocorrencia")       # Data e hora do chamado
        hr_inicio = request.form.get("hr_inicio")       # Hora início
        hr_fim = request.form.get("hr_fim")             # Hora fim
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

    chamados = conn.execute('SELECT * FROM chamados').fetchall()

    localidades = conn.execute('SELECT DISTINCT localidade FROM chamados WHERE localidade IS NOT NULL AND localidade != ""').fetchall()
    status = conn.execute('SELECT DISTINCT status FROM chamados WHERE status IS NOT NULL AND status != ""').fetchall()

    conn.close()

    return render_template(
        'form.html',
        success=success,
        localidades=[row['localidade'] for row in localidades],
        status=[row['status'] for row in status],
        chamados=chamados,
        now=datetime.now()
    )

@app.route('/editar/<int:id>', methods=['POST'])
def editar_chamado(id):
    conn = get_db_connection()
    chamado_antigo = conn.execute('SELECT * FROM chamados WHERE id = ?', (id,)).fetchone()

    if not chamado_antigo:
        conn.close()
        return "Chamado não encontrado", 404

    status = request.form.get('status')

    conn.execute('UPDATE chamados SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()

    registrar_log('Edição', f'Status do chamado ID {id} alterado. De: "{chamado_antigo["status"]}" Para: "{status}"')
    return redirect(url_for('index', success='edit'))


@app.route('/deletar_chamado/<int:id>', methods=['POST'])
def deletar_chamado(id):
    conn = get_db_connection()
    chamado = conn.execute('SELECT * FROM chamados WHERE id = ?', (id,)).fetchone()
    if not chamado:
        conn.close()
        return "Chamado não encontrado", 404
    conn.execute("DELETE FROM chamados WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    registrar_log('Deleção', f'Chamado ID {id} deletado: "{chamado["chamado"]}"')
    return redirect(url_for('index', success='delete'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
