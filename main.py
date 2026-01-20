from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_master_key_2026'

# Configuration SQL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÈLES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    activity_sector = db.Column(db.String(100), default="Services")
    is_admin = db.Column(db.Boolean, default=False)  # NOUVEAU : Pour ton accès Maître
    slots = db.Column(db.Integer, default=1)
    avg_duration = db.Column(db.Integer, default=30)
    prices_info = db.Column(db.Text, default="Services standards")
    appointments = db.relationship('Appointment', backref='owner', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- DESIGN ---
BASE_HEAD = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
"""

# --- ROUTES AUTH ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(email=request.form.get('email'), password=request.form.get('password'), 
                    business_name=request.form.get('business_name'), activity_sector=request.form.get('activity_sector'))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(f"{BASE_HEAD} <div class='min-h-screen bg-slate-50 flex items-center justify-center'> <div class='max-w-md w-full bg-white p-10 rounded-3xl shadow-xl'> <h2 class='text-2xl font-bold mb-6 text-center'>Inscription DigitagPro IA</h2> <form method='POST' class='space-y-4'> <input name='business_name' placeholder='Nom Entreprise' class='w-full p-3 bg-slate-100 rounded-xl' required> <input name='activity_sector' placeholder='Secteur (ex: Garage)' class='w-full p-3 bg-slate-100 rounded-xl' required> <input name='email' type='email' placeholder='Email' class='w-full p-3 bg-slate-100 rounded-xl' required> <input name='password' type='password' placeholder='Mot de passe' class='w-full p-3 bg-slate-100 rounded-xl' required> <button class='w-full bg-indigo-600 text-white p-4 rounded-xl font-bold'>Créer mon espace</button> </form> </div> </div>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('master_admin' if user.is_admin else 'dashboard'))
    return render_template_string(f"{BASE_HEAD} <div class='min-h-screen bg-slate-50 flex items-center justify-center'> <div class='max-w-md w-full bg-white p-10 rounded-3xl shadow-xl'> <h2 class='text-2xl font-bold mb-6 text-center'>Connexion DigitagPro</h2> <form method='POST' class='space-y-4'> <input name='email' type='email' placeholder='Email' class='w-full p-3 bg-slate-100 rounded-xl'> <input name='password' type='password' placeholder='Mot de passe' class='w-full p-3 bg-slate-100 rounded-xl'> <button class='w-full bg-slate-900 text-white p-4 rounded-xl font-bold'>Entrer</button> </form> </div> </div>")

# --- DASHBOARD CLIENT ---
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        current_user.business_name = request.form.get('business_name')
        current_user.slots = int(request.form.get('slots'))
        current_user.avg_duration = int(request.form.get('avg_duration'))
        current_user.prices_info = request.form.get('prices_info')
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    html = """
    BASE_HEAD_HERE
    <div class="flex min-h-screen bg-slate-50">
        <div class="w-64 bg-slate-900 text-white p-8 flex flex-col">
            <div class="font-bold text-xl mb-10">DigitagPro <span class="text-indigo-400">IA</span></div>
            <a href="/logout" class="mt-auto text-slate-400 hover:text-white">Déconnexion</a>
        </div>
        <div class="flex-1 p-10">
            <h1 class="text-3xl font-black mb-8">{{ current_user.business_name }}</h1>
            <div class="grid grid-cols-2 gap-10">
                <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                    <h3 class="font-bold mb-6 italic">Réglages de l'Agent IA</h3>
                    <form method="POST" class="space-y-4">
                        <input name="business_name" value="{{ current_user.business_name }}" class="w-full p-3 bg-slate-50 rounded-xl border">
                        <div class="flex gap-4">
                            <input name="slots" type="number" value="{{ current_user.slots }}" class="w-1/2 p-3 bg-slate-50 rounded-xl border">
                            <input name="avg_duration" type="number" value="{{ current_user.avg_duration }}" class="w-1/2 p-3 bg-slate-50 rounded-xl border">
                        </div>
                        <textarea name="prices_info" class="w-full p-3 bg-slate-50 rounded-xl border" rows="4">{{ current_user.prices_info }}</textarea>
                        <button class="w-full bg-indigo-600 text-white p-4 rounded-xl font-bold">Sauvegarder</button>
                    </form>
                    <div class="mt-6 p-4 bg-indigo-50 rounded-xl text-indigo-700 text-sm font-mono text-center">
                        Webhook : /voice/{{ current_user.id }}
                    </div>
                </div>
                <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                    <h3 class="font-bold mb-6 italic">Appels Récents</h3>
                    {% for rdv in current_user.appointments|reverse %}
                    <div class="p-4 border-b last:border-0">{{ rdv.details }} <br> <span class="text-xs text-slate-400">{{ rdv.date_str }}</span></div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html)

@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    users = User.query.all()
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).all()
    
    html = """
    BASE_HEAD_HERE
    <div class="min-h-screen bg-slate-950 text-white p-8">
        <div class="flex justify-between items-center mb-10">
            <div>
                <h1 class="text-4xl font-black text-indigo-500 italic">COMMAND CENTER</h1>
                <p class="text-slate-400">Gestion totale de la flotte DigitagPro IA</p>
            </div>
            <a href="/logout" class="bg-red-500/20 text-red-400 px-6 py-2 rounded-full border border-red-500/50 hover:bg-red-500 hover:text-white transition">Déconnexion</a>
        </div>
        
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
            <div class="xl:col-span-2 space-y-6">
                <h2 class="text-xl font-bold flex items-center gap-2"><i class="fas fa-building text-indigo-400"></i> Portefeuille Clients</h2>
                {% for u in users %}
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 hover:border-indigo-500 transition">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <span class="bg-indigo-600 text-[10px] px-2 py-1 rounded uppercase font-bold tracking-widest">Client ID: {{ u.id }}</span>
                            <h3 class="text-2xl font-bold mt-2">{{ u.business_name }}</h3>
                            <p class="text-slate-500 text-sm">{{ u.email }} | Secteur: {{ u.activity_sector }}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-xs text-slate-500">Slots: {{ u.slots }}</p>
                            <p class="text-xs text-slate-500">Durée: {{ u.avg_duration }}min</p>
                        </div>
                    </div>
                    
                    <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 mb-4">
                        <p class="text-xs text-indigo-400 font-bold mb-2 uppercase">Prompt / Tarifs IA :</p>
                        <p class="text-sm text-slate-300 italic">"{{ u.prices_info[:150] }}..."</p>
                    </div>

                    <div class="flex gap-3">
                        <button onclick="alert('Fonctionnalité Edit ID {{ u.id }} bientôt dispo')" class="bg-slate-800 hover:bg-indigo-600 px-4 py-2 rounded-xl text-sm transition">Modifier Réglages</button>
                        <a href="/voice/{{ u.id }}" target="_blank" class="bg-slate-800 hover:bg-green-600 px-4 py-2 rounded-xl text-sm transition text-center">Tester l'IA</a>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div class="space-y-6">
                <h2 class="text-xl font-bold flex items-center gap-2"><i class="fas fa-calendar-check text-green-400"></i> Flux de Réservations</h2>
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-h-[800px] overflow-y-auto space-y-4">
                    {% for rdv in all_rdv %}
                    <div class="p-4 bg-slate-950 rounded-2xl border-l-4 border-indigo-500">
                        <div class="flex justify-between text-[10px] mb-2">
                            <span class="font-bold text-indigo-400 uppercase">{{ rdv.owner.business_name }}</span>
                            <span class="text-slate-600">{{ rdv.date_str }}</span>
                        </div>
                        <p class="text-sm text-slate-200">{{ rdv.details }}</p>
                    </div>
                    {% else %}
                    <p class="text-slate-600 text-center py-10 italic">Aucun rendez-vous pour le moment</p>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html, users=users, all_rdv=all_rdv))

# --- IA VOICE ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    system_prompt = f"Tu es l'assistant IA de '{commercant.business_name}'. Secteur: {commercant.activity_sector}. Tarifs/Infos: {commercant.prices_info}. Si RDV validé, commence par CONFIRMATION_RDV: [Détail]."
    
    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {commercant.business_name}, comment puis-je vous aider ?"
    else:
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}])
        raw = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in raw:
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=raw.split("CONFIRMATION_RDV:")[1].strip(), user_id=commercant.id)
            db.session.add(new_rdv); db.session.commit()
            ai_response = raw.split("CONFIRMATION_RDV:")[0]
        else: ai_response = raw
        
    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
@app.route('/devenir-master-vite')
def dev_master():
    user = User.query.filter_by(email='romanlayani@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "Tu es maintenant le Maitre du systeme !"
    return "Utilisateur non trouve"