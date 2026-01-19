from flask import Flask, request, render_template_string, redirect, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import json
import os

app = Flask(__name__)

# --- CONFIGURATION (CORRIGÉE) ---
# On cherche la clé dans les variables Render, sinon on utilise la tienne par défaut
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)
# IMPORTANT : Définition du fichier de base de données
DB_FILE = 'config_salon.json'

# --- BACKEND ---
def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "nom": "Mon Salon Premium",
            "activite": "Coiffeur",
            "ton": "Sympa et professionnel",
            "tarifs": "Coupe Homme: 25€\nCoupe Femme: 45€",
            "rendez_vous": []
        }
        save_db(default_data)
        return default_data
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except:
            data = {"nom": "Mon Salon Premium", "rendez_vous": []}
        if "rendez_vous" not in data: data["rendez_vous"] = []
        return data

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- FRONTEND ---
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    data = load_db()
    if request.method == 'POST':
        data['nom'] = request.form.get('nom')
        data['activite'] = request.form.get('activite')
        data['ton'] = request.form.get('ton')
        data['tarifs'] = request.form.get('tarifs')
        save_db(data)
        return redirect(url_for('dashboard'))

    nb_rdv = len(data.get('rendez_vous', []))
    
    html_template = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Admin | {{ data.nom }}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            :root { --primary: #4F46E5; --bg: #F3F4F6; --text: #1F2937; --white: #ffffff; }
            body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; }
            .sidebar { width: 260px; background: var(--white); padding: 20px; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; }
            .logo { font-size: 20px; font-weight: 700; color: var(--primary); margin-bottom: 40px; display: flex; align-items: center; gap: 10px; }
            .menu-item { padding: 12px 15px; margin-bottom: 5px; border-radius: 8px; color: #4B5563; text-decoration: none; display: flex; align-items: center; gap: 12px; font-weight: 500; }
            .menu-item.active { background-color: #EEF2FF; color: var(--primary); }
            .main { flex: 1; padding: 30px; overflow-y: auto; }
            .card { background: var(--white); padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
            .stat-value { font-size: 28px; font-weight: 700; }
            .content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #D1D5DB; border-radius: 6px; margin-bottom: 15px; }
            button { width: 100%; background: var(--primary); color: white; padding: 12px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
            .rdv-item { display: flex; align-items: center; padding: 15px; border-bottom: 1px solid #f3f4f6; }
        </style>
        <meta http-equiv="refresh" content="10">
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><i class="fas fa-robot"></i> HairForMe AI</div>
            <a href="/" class="menu-item active"><i class="fas fa-home"></i> Tableau de bord</a>
            <div style="margin-top: auto; font-size: 12px; color: #9CA3AF;">v1.0.4 PRO</div>
        </div>
        <div class="main">
            <h1>Bonjour, {{ data.nom }} 👋</h1>
            <div class="stats-grid">
                <div class="card"><div class="stat-label">RDV pris</div><div class="stat-value">{{ nb_rdv }}</div></div>
                <div class="card"><div class="stat-label">Appels</div><div class="stat-value">En ligne</div></div>
                <div class="card"><div class="stat-label">Statut</div><div class="stat-value" style="color: #10B981;">Actif</div></div>
            </div>
            <div class="content-grid">
                <div class="card">
                    <h3>Configuration</h3>
                    <form method="POST">
                        <label>Nom</label><input type="text" name="nom" value="{{ data.nom }}">
                        <label>Tarifs</label><textarea name="tarifs" rows="5">{{ data.tarifs }}</textarea>
                        <button type="submit">Mettre à jour</button>
                    </form>
                </div>
                <div class="card">
                    <h3>Derniers RDV</h3>
                    {% for rdv in data.rendez_vous|reverse %}
                    <div class="rdv-item"><strong>{{ rdv.resume }}</strong></div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, data=data, nb_rdv=nb_rdv)

# --- IA ---
@app.route("/voice", methods=['POST'])
def voice():
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    config = load_db()
    date_info = datetime.now().strftime("%A %d %B à %Hh%M")
    
    system_prompt = f"Tu es l'IA de {config['nom']}. Sois bref (15 mots max). Si RDV validé, écris CONFIRMATION_RDV: [Détails]. Infos: {config['tarifs']}."

    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {config['nom']}. Comment puis-je vous aider ?"
    else:
        try:
            chat = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
            )
            raw = chat.choices[0].message.content
            if "CONFIRMATION_RDV:" in raw:
                parts = raw.split("CONFIRMATION_RDV:")
                nouvel_rdv = {"date": datetime.now().strftime("%d/%m %H:%M"), "resume": parts[1].strip()}
                config['rendez_vous'].append(nouvel_rdv)
                save_db(config)
                ai_response = parts[0] if parts[0] else "C'est noté !"
            else:
                ai_response = raw
        except:
            ai_response = "Je n'ai pas bien compris."

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)