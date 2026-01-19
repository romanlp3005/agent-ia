from flask import Flask, request, render_template_string, redirect, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import json
import os

app = Flask(__name__)

# --- CONFIGURATION ---
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)
DB_FILE = 'database.json'

# --- LOGIQUE MULTI-CLIENTS ---
def load_db():
    if not os.path.exists(DB_FILE):
        # On crée une base de données avec deux exemples pour tester le multi-client
        initial_data = {
            "demo": {
                "nom": "Salon Démo",
                "activite": "Coiffeur",
                "ton": "Amical",
                "tarifs": "Coupe: 20€",
                "rendez_vous": []
            },
            "barber": {
                "nom": "The Real Barber",
                "activite": "Barbier",
                "ton": "Stylé et relax",
                "tarifs": "Barbe: 15€, Coupe: 25€",
                "rendez_vous": []
            }
        }
        save_db(initial_data)
        return initial_data
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- FRONTEND (Dashboard Dynamique) ---
@app.route('/')
def home():
    return "<h1>HairForMe AI - Plateforme SaaS</h1><p>Accédez à votre dashboard via /dashboard/votre-nom</p>"

@app.route('/dashboard/<client_id>', methods=['GET', 'POST'])
def dashboard(client_id):
    db = load_db()
    if client_id not in db:
        return "<h1>Erreur : Client inconnu</h1><p>Ce salon n'existe pas encore dans notre base.</p>", 404
    
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
    
    # Template HTML (Identique au précédent mais adapté au client_id)
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
            <a href="#" class="menu-item active"><i class="fas fa-home"></i> {{ data.nom }}</a>
            <div style="margin-top: auto; font-size: 11px; color: #9CA3AF;">Identifiant : {{ client_id }}</div>
        </div>
        <div class="main">
            <h1>Espace Client : {{ data.nom }}</h1>
            <div class="stats-grid">
                <div class="card"><div class="stat-label">Rendez-vous</div><div class="stat-value">{{ nb_rdv }}</div></div>
                <div class="card"><div class="stat-label">Statut</div><div class="stat-value" style="color: #10B981;">Actif</div></div>
                <div class="card"><div class="stat-label">Frais</div><div class="stat-value">0.00 €</div></div>
            </div>
            <div class="content-grid">
                <div class="card">
                    <h3>Configuration de l'IA</h3>
                    <form method="POST">
                        <label>Nom du Salon</label><input type="text" name="nom" value="{{ data.nom }}">
                        <label>Personnalité</label><input type="text" name="ton" value="{{ data.ton }}">
                        <label>Base de connaissances (Tarifs/Infos)</label><textarea name="tarifs" rows="5">{{ data.tarifs }}</textarea>
                        <button type="submit">Sauvegarder les réglages</button>
                    </form>
                </div>
                <div class="card">
                    <h3>Historique des Rendez-vous</h3>
                    {% if data.rendez_vous|length == 0 %}
                        <p>Aucun RDV pour le moment.</p>
                    {% else %}
                        {% for rdv in data.rendez_vous|reverse %}
                        <div class="rdv-item">
                            <i class="fas fa-calendar-check" style="margin-right: 10px; color: #4F46E5;"></i>
                            <div><strong>{{ rdv.resume }}</strong><br><small>Le {{ rdv.date }}</small></div>
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

# --- IA (Route Multi-Clients) ---
@app.route("/voice/<client_id>", methods=['POST'])
def voice(client_id):
    db = load_db()
    if client_id not in db:
        resp = VoiceResponse()
        resp.say("Erreur de configuration. Identifiant inconnu.", language='fr-FR')
        return str(resp)
        
    config = db[client_id]
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    date_info = datetime.now().strftime("%A %d %B à %Hh%M")
    
    system_prompt = f"""
    Tu es l'assistant de '{config['nom']}'. Activité: {config['activite']}.
    Consigne: Sois bref (15 mots max).
    Si le RDV est validé, commence par CONFIRMATION_RDV: [Détail].
    Infos utiles: {config['tarifs']}. Date actuelle: {date_info}.
    """

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
                nouvel_rdv = {"date": datetime.now().strftime("%d/%m à %H:%M"), "resume": parts[1].strip()}
                config['rendez_vous'].append(nouvel_rdv)
                db[client_id] = config
                save_db(db)
                ai_response = parts[0] if parts[0] else "C'est noté pour votre rendez-vous !"
            else:
                ai_response = raw
        except:
            ai_response = "Un petit problème technique est survenu."

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{client_id}') # On redirige vers la route spécifique au client
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)