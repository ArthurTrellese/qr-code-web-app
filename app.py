from flask import Flask, render_template, request, jsonify, redirect, url_for
import qrcode
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json

app = Flask(__name__)

# Inicializar o Firebase Admin SDK com suas credenciais
firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')  # Pega o conteúdo da variável de ambiente
cred = credentials.Certificate(json.loads(firebase_credentials))  # Converte o conteúdo JSON para credenciais
firebase_admin.initialize_app(cred)

print(firebase_credentials)

# Função para inicializar os participantes no Firestore (caso ainda não estejam lá)
def initialize_participants():
    participants_ref = db.collection('participants')
    for i in range(1, 3001):
        participant_id = f"G-{i:04d}"
        participants_ref.document(participant_id).set({
            "name": "",
            "email": "",
            "contact": "",
            "match": "",  # Inicializando o campo "match" em branco
            "status": "pending"
        })

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
    # Verifica se o participante existe no Firestore
    participant_ref = db.collection('participants').document(participant_id)
    participant = participant_ref.get()

    if not participant.exists:
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
    participant_ref = db.collection('participants').document(participant_id)
    participant = participant_ref.get()
    
    if participant.exists():
        if participant.to_dict().get("status") == "pending":
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

    # Atualiza os dados do participante no Firestore
    participant_ref = db.collection('participants').document(participant_id)
    participant_ref.update({
        'name': name,
        'email': email,
        'contact': contact,
        'status': 'registered'
    })
    
    return redirect(url_for('scan_qr', participant_id=participant_id))  # Redireciona para a página de escaneamento

# Página para escanear o QR code de outro participante
@app.route('/scan/<participant_id>', methods=['GET'])
def scan_qr(participant_id):
    participant_ref = db.collection('participants').document(participant_id)
    participant = participant_ref.get()
    
    if participant.exists:
        return render_template('scan.html', participant_id=participant_id)
    else:
        return f"Erro: ID {participant_id} não encontrado!", 404

# Rota para verificar o Match
@app.route('/check_match', methods=['POST'])
def check_match():
    participant_id = request.form['participant_id']
    scanned_id = request.form['scanned_id']

    # Verifica os participantes no Firestore
    participant_ref = db.collection('participants').document(participant_id)
    participant = participant_ref.get()

    if participant.exists and participant.to_dict().get('match') == scanned_id:
        return jsonify({"status": "MATCH encontrado!", "success": True})
    else:
        return jsonify({"status": "Nenhum MATCH encontrado, continue procurando.", "success": False})

# Rota para visualizar todos os participantes sem paginação
@app.route('/view_participants', methods=['GET'])
def view_participants():
    participants_ref = db.collection('participants')
    participants = participants_ref.stream()

    participants_list = {}
    for participant in participants:
        participants_list[participant.id] = participant.to_dict()

    if not participants_list:
        return "Erro: Nenhum participante encontrado.", 400

    return render_template('view_participants.html', participants=participants_list)

# Rota para atualizar o match manualmente
@app.route('/update_match', methods=['POST'])
def update_match():
    participant_id = request.form['participant_id']
    new_match_id = request.form['new_match_id']

    participant_ref = db.collection('participants').document(participant_id)
    match_ref = db.collection('participants').document(new_match_id)

    if participant_ref.get().exists and match_ref.get().exists:
        participant_ref.update({
            'match': new_match_id
        })
        return redirect(url_for('view_participants'))
    else:
        return "Erro: ID do participante ou match inválido!", 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
