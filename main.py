from flask import Flask, request, render_template_string, redirect, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import json
import os

app = Flask(__name__)

# --- CONFIGURATION ---
# La clé OpenAI est récupérée depuis les variables d'environnement de Render
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)
DB_FILE = 'database.json'

# --- LOGIQUE DE SAUVEGARDE ET CHARGEMENT ---
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_db():
    data = {}
    # Si le fichier existe, on le lit
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                data = {}

    # FORCE la création des deux salons s'ils n'existent pas dans le fichier
    if "demo" not in data or "barber" not in data:
        data["demo"] = {
            "nom": "Salon Démo",
            "activite": "Coiffeur",
            "ton": "Amical",
            "tarifs": "Coupe: 20€",
            "rendez_vous": []
        }
        data["barber"] = {
            "nom": "The Real Barber",
            "activite": "Barbier",
            "ton": "Stylé et relax",
            "tarifs": "Barbe: 15€, Coupe: 25€",
            "rendez_vous": []
        }
        save_db(data)
    return data

# --- ROUTES FRONTEND ---

@app.route('/')
def home():
    # Redirection automatique vers demo pour éviter l'erreur Not Found
    return redirect(url_for('dashboard', client_id='demo'))

@app.route('/dashboard/<client_id>', methods=['GET', 'POST'])
def dashboard(client_id):
    db = load_db()
    if client_id not in db:
        return f"<h1>Erreur</h1><p>Le client '{client_id}' n'existe pas.</p>", 404
    
    client_data = db[client_id]

    if request.method == 'POST':
        client_data['nom'] = request.form.get('nom')
        client_data['activite'] = request.form.get('activite')
        client_data['ton'] = request.form.get('ton')
        client_data['tarifs'] = request.form.get('tarifs')
        db[client_id] = client_data
        save_db(db)
        return redirect(url_for('dashboard', client_id=client_id))

    nb_rdv = len(client_data.get('rendez_vous', []))
    
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
        <meta http-equiv="refresh" content="15">
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><i class="fas fa-robot"></i> HairForMe AI</div>
            <a href="/dashboard/demo" class="menu-item {% if client_id == 'demo' %}active{% endif %}">Salon Démo</a>
            <a href="/dashboard/barber" class="menu-item {% if client_id == 'barber' %}active{% endif %}">The Real Barber</a>
            <div style="margin-top: auto; font-size: 11px; color: #9CA3AF;">ID Client : {{ client_id }}</div>
        </div>
        <div class="main">
            <h1>Tableau de bord : {{ data.nom }}</h1>
            <div class="stats-grid">
                <div class="card"><div class="stat-label">RDV cumulés</div><div class="stat-value">{{ nb_rdv }}</div></div>
                <div class="card"><div class="stat-label">Statut Serveur</div><div class="stat-value" style="color: #10B981;">ONLINE</div></div>
            </div>
            <div class="content-grid">
                <div class="card">
                    <h3><i class="fas fa-cog"></i> Réglages de l'IA</h3>
                    <form method="POST">
                        <label>Nom de l'entreprise</label><input type="text" name="nom" value="{{ data.nom }}">
                        <label>Personnalité (ton)</label><input type="text" name="ton" value="{{ data.ton }}">
                        <label>Base de connaissances (Infos/Tarifs)</label><textarea name="tarifs" rows="6">{{ data.tarifs }}</textarea>
                        <button type="submit">Enregistrer</button>
                    </form>
                </div>
                <div class="card">
                    <h3><i class="fas fa-calendar-alt"></i> Derniers Rendez-vous</h3>
                    {% if data.rendez_vous|length == 0 %}
                        <p>Aucun rendez-vous noté pour le moment.</p>
                    {% else %}
                        {% for rdv in data.rendez_vous|reverse %}
                        <div class="rdv-item">
                            <i class="fas fa-check-circle" style="color: #4F46E5; margin-right: 12px;"></i>
                            <div><strong>{{ rdv.resume }}</strong><br><small>{{ rdv.date }}</small></div>
                        </div>
                        {% endfor %}
                    {% endif %}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, data=client_data, nb_rdv=nb_rdv, client_id=client_id)

# --- ROUTE IA (TWILIO) ---

@app.route("/voice/<client_id>", methods=['POST'])
def voice(client_id):
    db = load_db()
    if client_id not in db:
        resp = VoiceResponse()
        resp.say("Erreur de configuration. Client inconnu.", language='fr-FR')
        return str(resp)
        
    config = db[client_id]
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    date_info = datetime.now().strftime("%A %d %B à %Hh%M")
    
    system_prompt = f"""
    Tu es l'assistant vocal de '{config['nom']}'. 
    Sois très concis (15 mots max). 
    Si un RDV est pris, écris : CONFIRMATION_RDV: [Détails].
    Données salon: {config['tarifs']}. Date actuelle: {date_info}.
    """

    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {config['nom']}. Je vous écoute ?"
    else:
        try:
            chat = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
            )
            raw = chat.choices[0].message.content
            if "CONFIRMATION_RDV:" in raw:
                parts = raw.split("CONFIRMATION_RDV:")
                # Sauvegarde du RDV
                nouvel_rdv = {"date": datetime.now().strftime("%d/%m %H:%M"), "resume": parts[1].strip()}
                config['rendez_vous'].append(nouvel_rdv)
                db[client_id] = config
                save_db(db)
                ai_response = parts[0] if parts[0] else "C'est bien noté pour votre rendez-vous."
            else:
                ai_response = raw
        except:
            ai_response = "Désolé, j'ai un problème technique."

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{client_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)