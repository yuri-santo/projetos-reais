from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
import sqlite3
import io

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

DATABASE = 'chamados.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            chamado TEXT,
            localidade TEXT,
            n_medidor TEXT,
            uc_instalacao TEXT,
            responsavel TEXT,
            descricao TEXT,
            status TEXT
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
        horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        localidade = request.form.get("localidade")
        n_medidor = request.form.get("n_medidor")
        uc_instalacao = request.form.get("uc_instalacao")
        responsavel = request.form.get("responsavel")
        descricao = request.form.get("descricao")
        status = request.form.get("status")

        conn.execute('''
            INSERT INTO chamados (
                data_hora, chamado, localidade, n_medidor,
                uc_instalacao, responsavel, descricao, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (horario, chamado, localidade, n_medidor, uc_instalacao, responsavel, descricao, status))
        conn.commit()
        return redirect(url_for('index', success='create'))

    success = request.args.get('success')
    

    chamados = conn.execute('SELECT * FROM chamados').fetchall()

    localidades = conn.execute('SELECT DISTINCT localidade FROM chamados WHERE localidade IS NOT NULL AND localidade != ""').fetchall()

    conn.close()

    return render_template(
        'form.html',
        success=success,
        localidades=[row['localidade'] for row in localidades],  # passa lista de localidades
        chamados=chamados,  # passa todos os chamados
        now=datetime.now()
    )

@app.route('/editar/<int:id>', methods=['POST'])
def editar_chamado(id):
    conn = get_db_connection()
    chamado = conn.execute('SELECT * FROM chamados WHERE id = ?', (id,)).fetchone()

    if not chamado:
        conn.close()
        return "Chamado não encontrado", 404

    chamado_novo = request.form.get('chamado')
    localidade = request.form.get('localidade')
    n_medidor = request.form.get('n_medidor')
    uc_instalacao = request.form.get('uc_instalacao')
    responsavel = request.form.get('responsavel')
    descricao = request.form.get('descricao')
    status = request.form.get('status')

    conn.execute('''
        UPDATE chamados
        SET chamado = ?, localidade = ?, n_medidor = ?, uc_instalacao = ?, 
            responsavel = ?, descricao = ?, status = ?
        WHERE id = ?
    ''', (chamado_novo, localidade, n_medidor, uc_instalacao, responsavel, descricao, status, id))

    conn.commit()
    conn.close()
    return redirect(url_for('index', success='edit'))

@app.route('/deletar_chamado/<int:id>', methods=['POST'])
def deletar_chamado(id):
    conn = sqlite3.connect('chamados.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chamados WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index', success='delete'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
