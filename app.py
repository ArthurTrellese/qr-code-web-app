from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import qrcode
import json
import os
import io
from PIL import Image
from math import ceil

app = Flask(__name__)

# Caminho para o arquivo JSON que vai armazenar os dados dos participantes
db_file = 'participants.json'

# Função para carregar o arquivo JSON e inicializar se necessário
def load_participants():
    if not os.path.exists(db_file) or os.stat(db_file).st_size == 0:
        initialize_participants()  # Inicializar se o arquivo não existir ou estiver vazio
    with open(db_file, 'r') as f:
        return json.load(f)

# Função para salvar os dados no arquivo JSON
def save_participants(data):
    with open(db_file, 'w') as f:
        json.dump(data, f, indent=4)

# Função para inicializar os participantes no arquivo JSON (matches em branco)
def initialize_participants():
    participants = {}
    for i in range(1, 3001):
        participant_id = f"G-{i:04d}"
        participants[participant_id] = {
            "name": "",
            "email": "",
            "contact": "",
            "match": "",  # Inicializando o campo "match" em branco
            "status": "pending"
        }
    save_participants(participants)

# Função para garantir que o diretório 'static' exista
def ensure_static_dir():
    if not os.path.exists('static'):
        os.makedirs('static')

# Rota para o menu principal (index)
@app.route('/')
def index():
    return render_template('index.html')

# Geração do QR Code e envio da imagem diretamente
@app.route('/generate_qr/<participant_id>')
def generate_qr(participant_id):
    participants = load_participants()

    if participant_id not in participants:
        return f"Erro: ID {participant_id} não encontrado!", 404

    # Gera o QR code com o link para o formulário do participante
    qr_code_data = f"https://gowork.up.railway.app/form/{participant_id}"
    img = qrcode.make(qr_code_data)

    # Verifica se a pasta 'static' existe e cria, se necessário
    ensure_static_dir()

    # Salva a imagem do QR code no diretório 'static'
    qr_image_path = f'static/{participant_id}.png'
    img.save(qr_image_path)

    # Envia o QR code gerado diretamente como resposta
    return f'QR code gerado para {participant_id}. <a href="/{qr_image_path}">Clique aqui para ver o QR code</a>'

# Exibir o formulário HTML
@app.route('/form/<participant_id>', methods=['GET'])
def show_form(participant_id):
    participants = load_participants()
    if participant_id in participants:
        if participants[participant_id]["status"] == "pending":
            # Exibe o formulário para cadastrar os dados
            return render_template('form.html', participant_id=participant_id)
        else:
            # Se o cadastro já foi feito, redireciona para a página de escanear QR codes
            return redirect(url_for('scan_qr', participant_id=participant_id))
    else:
        return f"Erro: ID {participant_id} não encontrado!", 404

# Receber dados do formulário
@app.route('/submit', methods=['POST'])
def submit_form():
    participant_id = request.form['participant_id']
    name = request.form['name']
    email = request.form['email']
    contact = request.form['contact']

    # Carrega os dados existentes
    participants = load_participants()

    # Atualiza os dados do participante
    if participant_id in participants:
        participants[participant_id]['name'] = name
        participants[participant_id]['email'] = email
        participants[participant_id]['contact'] = contact
        participants[participant_id]['status'] = 'registered'  # Atualiza o status para "registered"
        save_participants(participants)
        return redirect(url_for('scan_qr', participant_id=participant_id))  # Redireciona para a página de escaneamento
    else:
        return "Erro: ID do participante não encontrado!"

# Página para escanear o QR code de outro participante
@app.route('/scan/<participant_id>', methods=['GET'])
def scan_qr(participant_id):
    participants = load_participants()
    if participant_id in participants:
        return render_template('scan.html', participant_id=participant_id)
    else:
        return f"Erro: ID {participant_id} não encontrado!", 404

# Rota para verificar o Match
@app.route('/check_match', methods=['POST'])
def check_match():
    participant_id = request.form['participant_id']
    scanned_id = request.form['scanned_id']

    participants = load_participants()

    if participant_id in participants and participants[participant_id]['match'] == scanned_id:
        return jsonify({"status": "MATCH encontrado!", "success": True})
    else:
        return jsonify({"status": "Nenhum MATCH encontrado, continue procurando.", "success": False})

# Rota para exibir a lista de participantes e seus dados (matches editáveis) com paginação e busca
@app.route('/view_participants', methods=['GET'])
def view_participants():
    participants = load_participants()

    # Implementando a busca
    search_query = request.args.get('search', '').lower()
    if search_query:
        participants = {pid: details for pid, details in participants.items() if search_query in pid.lower() or search_query in details['name'].lower()}

    # Implementando a paginação
    page = int(request.args.get('page', 1))
    per_page = 20  # número de registros por página
    total_participants = len(participants)
    total_pages = ceil(total_participants / per_page)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Lista de participantes paginada
    paginated_participants = dict(list(participants.items())[start_idx:end_idx])

    return render_template(
        'view_participants.html',
        participants=paginated_participants,
        current_page=page,
        total_pages=total_pages
    )

# Rota para atualizar o match manualmente
@app.route('/update_match', methods=['POST'])
def update_match():
    participant_id = request.form['participant_id']
    new_match_id = request.form['new_match_id']

    participants = load_participants()

    if participant_id in participants and new_match_id in participants:
        participants[participant_id]['match'] = new_match_id
        save_participants(participants)
        return redirect(url_for('view_participants'))
    else:
        return "Erro: ID do participante ou match inválido!", 400

# Rota para atualizar as informações do participante
@app.route('/update_participant', methods=['POST'])
def update_participant():
    participant_id = request.form['participant_id']
    name = request.form['name']
    email = request.form['email']
    contact = request.form['contact']
    match = request.form['match']

    participants = load_participants()

    if participant_id in participants:
        # Atualiza as informações do participante
        participants[participant_id]['name'] = name
        participants[participant_id]['email'] = email
        participants[participant_id]['contact'] = contact
        participants[participant_id]['match'] = match
        save_participants(participants)
        return redirect(url_for('view_participants'))
    else:
        return "Erro: ID do participante não encontrado!", 400

# Rota para atualizar todos os participantes
@app.route('/update_all_participants', methods=['POST'])
def update_all_participants():
    participants_data = request.form.get('participants')
    participants = load_participants()

    for participant_id, details in participants_data.items():
        if participant_id in participants:
            participants[participant_id]['name'] = details.get('name', participants[participant_id]['name'])
            participants[participant_id]['email'] = details.get('email', participants[participant_id]['email'])
            participants[participant_id]['contact'] = details.get('contact', participants[participant_id]['contact'])
            participants[participant_id]['match'] = details.get('match', participants[participant_id]['match'])

    save_participants(participants)
    return redirect(url_for('view_participants'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
