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
    is_admin = db.Column(db.Boolean, default=False)
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

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

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
            <div class="font-bold text-xl mb-10 text-indigo-400">DigitagPro IA</div>
            <a href="/logout" class="mt-auto text-slate-400 hover:text-white font-bold">Déconnexion</a>
        </div>
        <div class="flex-1 p-10">
            <h1 class="text-3xl font-black mb-8">{{ current_user.business_name }}</h1>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                    <h3 class="font-bold mb-6 italic text-slate-400">Configuration de votre Agent</h3>
                    <form method="POST" class="space-y-4">
                        <input name="business_name" value="{{ current_user.business_name }}" class="w-full p-3 bg-slate-50 rounded-xl border">
                        <textarea name="prices_info" class="w-full p-3 bg-slate-50 rounded-xl border" rows="5">{{ current_user.prices_info }}</textarea>
                        <button class="w-full bg-indigo-600 text-white p-4 rounded-xl font-bold">Enregistrer</button>
                    </form>
                </div>
                <div class="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                    <h3 class="font-bold mb-6 italic text-slate-400">Rendez-vous récents</h3>
                    {% for rdv in current_user.appointments|reverse %}
                    <div class="p-4 border-b last:border-0"><span class="font-bold text-indigo-600">{{ rdv.date_str }}</span> : {{ rdv.details }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html)

# --- MASTER ADMIN ---
@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    
    if request.args.get('delete_user'):
        u_to_del = User.query.get(request.args.get('delete_user'))
        if u_to_del and not u_to_del.is_admin:
            db.session.delete(u_to_del); db.session.commit()
            return redirect(url_for('master_admin'))

    if request.method == 'POST' and 'update_client_id' in request.form:
        target_user = User.query.get(request.form.get('update_client_id'))
        if target_user:
            target_user.business_name = request.form.get('b_name')
            target_user.prices_info = request.form.get('p_info')
            db.session.commit()
            return redirect(url_for('master_admin'))

    users = User.query.all()
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).all()
    
    html = """
    BASE_HEAD_HERE
    <div class="min-h-screen bg-[#0a0c14] text-white p-8">
        <div class="flex justify-between items-center mb-12">
            <h1 class="text-4xl font-black bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">DIGITAGPRO COMMAND CENTER</h1>
            <a href="/logout" class="bg-slate-800 px-6 py-2 rounded-full text-sm">Quitter</a>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
            <div class="lg:col-span-2 space-y-8">
                {% for u in users %}
                <div class="bg-[#111420] border border-slate-800 p-8 rounded-[2rem]">
                    <form method="POST" class="space-y-4">
                        <input type="hidden" name="update_client_id" value="{{ u.id }}">
                        <div class="flex justify-between">
                            <input name="b_name" value="{{ u.business_name }}" class="bg-transparent text-2xl font-black focus:outline-none text-indigo-400">
                            <div class="flex gap-2">
                                <a href="/master-admin?delete_user={{ u.id }}" class="text-red-500 p-2"><i class="fas fa-trash"></i></a>
                            </div>
                        </div>
                        <textarea name="p_info" rows="3" class="w-full bg-[#0a0c14] border border-slate-800 rounded-2xl p-4 text-sm">{{ u.prices_info }}</textarea>
                        <button class="w-full bg-indigo-600 text-white py-3 rounded-2xl font-bold">Appliquer</button>
                    </form>
                </div>
                {% endfor %}
            </div>
            <div class="space-y-4">
                <h2 class="font-bold text-slate-400 uppercase tracking-widest text-sm">Activité Live</h2>
                {% for rdv in all_rdv %}
                <div class="p-4 bg-[#111420] rounded-2xl border-l-2 border-indigo-500">
                    <p class="text-[10px] font-bold text-indigo-400">{{ rdv.owner.business_name }}</p>
                    <p class="text-sm">{{ rdv.details }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html, users=users, all_rdv=all_rdv)

@app.route('/devenir-master-vite')
def dev_master():
    user = User.query.filter_by(email='romanlayani@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "Tu es maintenant le Maitre du systeme !"
    return "Utilisateur non trouve"

# --- IA VOICE ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    system_prompt = f"Tu es l'assistant IA de '{commercant.business_name}'. Tarifs/Infos: {commercant.prices_info}. Si RDV validé, commence par CONFIRMATION_RDV: [Détail]."
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