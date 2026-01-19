from flask import Flask, request, render_template_string, redirect, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import json
import os

app = Flask(__name__)

# --- CONFIGURATION ---
client = OpenAI(api_key="COLLER_TA_CLE_ICI")
DB_FILE = 'config_salon.json'

# --- BACKEND (La logique reste la même) ---
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
        data = json.load(f)
        if "rendez_vous" not in data: data["rendez_vous"] = []
        return data

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- FRONTEND (Le Nouveau Design PRO) ---
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

    # Calcul des stats pour faire "SaaS"
    nb_rdv = len(data['rendez_vous'])
    
    html_template = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin | {{ data.nom }}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            :root { --primary: #4F46E5; --bg: #F3F4F6; --text: #1F2937; --white: #ffffff; }
            body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; }
            
            /* Sidebar */
            .sidebar { width: 260px; background: var(--white); padding: 20px; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; }
            .logo { font-size: 20px; font-weight: 700; color: var(--primary); margin-bottom: 40px; display: flex; align-items: center; gap: 10px; }
            .menu-item { padding: 12px 15px; margin-bottom: 5px; border-radius: 8px; color: #4B5563; text-decoration: none; display: flex; align-items: center; gap: 12px; font-weight: 500; transition: 0.2s; }
            .menu-item:hover, .menu-item.active { background-color: #EEF2FF; color: var(--primary); }
            
            /* Main Content */
            .main { flex: 1; padding: 30px; overflow-y: auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
            h1 { font-size: 24px; font-weight: 600; margin: 0; }
            
            /* Stats Cards */
            .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
            .card { background: var(--white); padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; }
            .stat-value { font-size: 28px; font-weight: 700; color: var(--text); margin-top: 5px; }
            .stat-label { font-size: 14px; color: #6B7280; }
            
            /* Layout Grid */
            .content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
            
            /* Form Styling */
            label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #374151; }
            input, select, textarea { width: 100%; padding: 10px 12px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 14px; margin-bottom: 16px; box-sizing: border-box; transition: 0.2s; font-family: 'Inter', sans-serif;}
            input:focus, textarea:focus { outline: none; border-color: var(--primary); ring: 2px solid #EEF2FF; }
            button { width: 100%; background: var(--primary); color: white; padding: 12px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; }
            button:hover { background: #4338ca; }
            
            /* Agenda Styling */
            .rdv-item { display: flex; align-items: center; padding: 15px; border-bottom: 1px solid #f3f4f6; }
            .rdv-item:last-child { border-bottom: none; }
            .rdv-icon { width: 40px; height: 40px; background: #EEF2FF; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--primary); margin-right: 15px; }
            .rdv-info strong { display: block; font-size: 14px; color: var(--text); }
            .rdv-info span { font-size: 13px; color: #6B7280; }
            .empty-state { text-align: center; padding: 40px; color: #9CA3AF; }
        </style>
        <meta http-equiv="refresh" content="10">
    </head>
    <body>
        
        <div class="sidebar">
            <div class="logo"><i class="fas fa-robot"></i> HairForMe AI</div>
            <a href="#" class="menu-item active"><i class="fas fa-home"></i> Tableau de bord</a>
            <a href="#" class="menu-item"><i class="fas fa-calendar"></i> Agenda</a>
            <a href="#" class="menu-item"><i class="fas fa-users"></i> Clients</a>
            <a href="#" class="menu-item"><i class="fas fa-cog"></i> Réglages</a>
            <div style="margin-top: auto; font-size: 12px; color: #9CA3AF;">v1.0.4 PRO</div>
        </div>

        <div class="main">
            <div class="header">
                <div>
                    <h1>Bonjour, {{ data.nom }} 👋</h1>
                    <p style="color: #6B7280; margin-top: 5px;">Voici ce qui se passe dans votre salon aujourd'hui.</p>
                </div>
                <div style="background: white; padding: 8px 16px; border-radius: 20px; border: 1px solid #e5e7eb; font-size: 14px; font-weight: 500;">
                    <span style="color: #10B981;">●</span> En ligne
                </div>
            </div>

            <div class="stats-grid">
                <div class="card">
                    <div class="stat-label">Rendez-vous pris</div>
                    <div class="stat-value">{{ nb_rdv }}</div>
                </div>
                <div class="card">
                    <div class="stat-label">Appels reçus aujourd'hui</div>
                    <div class="stat-value">12</div>
                </div>
                <div class="card">
                    <div class="stat-label">Économies réalisées</div>
                    <div class="stat-value">~140 €</div>
                </div>
            </div>

            <div class="content-grid">
                
                <div class="card">
                    <h3 style="margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-sliders-h" style="color: var(--primary);"></i> Configuration IA
                    </h3>
                    <form method="POST">
                        <label>Nom de l'établissement</label>
                        <input type="text" name="nom" value="{{ data.nom }}">

                        <label>Activité</label>
                        <select name="activite">
                            <option value="Coiffeur" {% if data.activite == 'Coiffeur' %}selected{% endif %}>Coiffeur</option>
                            <option value="Garage" {% if data.activite == 'Garage' %}selected{% endif %}>Garage</option>
                            <option value="Restaurant" {% if data.activite == 'Restaurant' %}selected{% endif %}>Restaurant</option>
                            <option value="Immobilier" {% if data.activite == 'Immobilier' %}selected{% endif %}>Agence Immo</option>
                        </select>

                        <label>Personnalité de l'assistant</label>
                        <input type="text" name="ton" value="{{ data.ton }}" placeholder="Ex: Chaleureux, Haut de gamme...">

                        <label>Tarifs & Informations (Base de connaissance)</label>
                        <textarea name="tarifs" rows="6">{{ data.tarifs }}</textarea>

                        <button type="submit">Mettre à jour l'Assistant</button>
                    </form>
                </div>

                <div class="card">
                    <h3 style="margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-clock" style="color: var(--primary);"></i> Derniers Rendez-vous
                    </h3>
                    
                    {% if data.rendez_vous|length == 0 %}
                        <div class="empty-state">
                            <i class="fas fa-calendar-times" style="font-size: 40px; margin-bottom: 10px; display: block;"></i>
                            Aucun rendez-vous pour le moment.<br>L'IA attend les appels...
                        </div>
                    {% else %}
                        {% for rdv in data.rendez_vous|reverse %}
                        <div class="rdv-item">
                            <div class="rdv-icon"><i class="fas fa-user-check"></i></div>
                            <div class="rdv-info">
                                <strong>{{ rdv.resume }}</strong>
                                <span><i class="far fa-calendar-alt"></i> Pris le {{ rdv.date }}</span>
                            </div>
                        </div>
                        {% endfor %}
                    {% endif %}
                </div>

            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, data=data, nb_rdv=nb_rdv)

# --- IA (Logique inchangée) ---
@app.route("/voice", methods=['POST'])
def voice():
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    
    config = load_db()
    date_info = datetime.now().strftime("%A %d %B à %Hh%M")
    
    system_prompt = f"""
    RÔLE: Assistant vocal ultra-efficace pour '{config['nom']}'.
    CONSIGNES STRICTES:
    1. Réponds en maximum 15 mots. 
    2. Ne divague jamais. Si tu ne sais pas, propose de rappeler.
    3. Ton objectif unique: Prendre le nom et l'heure du RDV.
    4. Si le client confirme (ex: "ok pour 14h"), tu DOIS écrire : CONFIRMATION_RDV: [Détail]
    
    INFOS SALON: {config['tarifs']}.
    DATE ACTUELLE: {date_info}.
    """

    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {config['nom']}. Je vous écoute ?"
    else:
        try:
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                max_tokens=100
            )
            raw_response = chat_completion.choices[0].message.content
            
            if "CONFIRMATION_RDV:" in raw_response:
                parts = raw_response.split("CONFIRMATION_RDV:")
                phrase_vocale = parts[0].strip()
                detail_rdv = parts[1].strip()
                if not phrase_vocale: phrase_vocale = "C'est noté, je confirme le rendez-vous."
                
                # Sauvegarde
                nouvel_rdv = {"date": datetime.now().strftime("%d/%m à %Hh%M"), "resume": detail_rdv}
                config['rendez_vous'].append(nouvel_rdv)
                save_db(config)
                
                ai_response = phrase_vocale
            else:
                ai_response = raw_response

        except Exception:
            ai_response = "Désolé, je ne vous entends pas bien."

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

if __name__ == "__main__":
    print("💎 INTERFACE PREMIUM ACTIVÉE : http://localhost:5000")
    app.run(port=5000, debug=True)