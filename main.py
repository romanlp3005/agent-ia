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

# --- UI COMPONENTS ---
BASE_HEAD = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }
    .sidebar-link:hover { background: rgba(99, 102, 241, 0.1); border-right: 3px solid #6366f1; }
    .glass-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
</style>
"""

SIDEBAR = """
<div class="fixed w-72 h-screen bg-[#020617] border-r border-slate-800 flex flex-col p-6">
    <div class="flex items-center gap-3 mb-12 px-2">
        <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <i class="fas fa-microchip text-white"></i>
        </div>
        <span class="text-xl font-extrabold tracking-tight">DigitagPro <span class="text-indigo-500 text-sm">IA</span></span>
    </div>
    
    <nav class="flex-1 space-y-2">
        <a href="/master-admin" class="flex items-center gap-3 p-3 rounded-xl sidebar-link text-indigo-400 bg-indigo-500/5 font-medium">
            <i class="fas fa-th-large w-5"></i> Dashboard Master
        </a>
        <a href="#" class="flex items-center gap-3 p-3 rounded-xl sidebar-link text-slate-400 hover:text-white transition">
            <i class="fas fa-users w-5"></i> Clients
        </a>
        <a href="#" class="flex items-center gap-3 p-3 rounded-xl sidebar-link text-slate-400 hover:text-white transition">
            <i class="fas fa-phone-volume w-5"></i> Logs d'appels
        </a>
        <a href="#" class="flex items-center gap-3 p-3 rounded-xl sidebar-link text-slate-400 hover:text-white transition">
            <i class="fas fa-cog w-5"></i> Paramètres
        </a>
    </nav>

    <div class="mt-auto pt-6 border-t border-slate-800">
        <div class="flex items-center gap-3 mb-6 px-2">
            <div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold uppercase">RL</div>
            <div class="text-xs">
                <p class="font-bold">Roman L.</p>
                <p class="text-slate-500 italic">Administrateur</p>
            </div>
        </div>
        <a href="/logout" class="flex items-center gap-3 p-3 rounded-xl text-red-400 hover:bg-red-500/10 transition font-medium">
            <i class="fas fa-sign-out-alt"></i> Déconnexion
        </a>
    </div>
</div>
"""

# --- ROUTES ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('master_admin' if user.is_admin else 'dashboard'))
    return render_template_string(f"{BASE_HEAD} <div class='min-h-screen bg-slate-950 flex items-center justify-center p-6'> <div class='max-w-md w-full glass-card p-10 rounded-[2.5rem] shadow-2xl'> <div class='text-center mb-10'> <h2 class='text-3xl font-black mb-2'>Connexion</h2> <p class='text-slate-400 text-sm'>Accédez à votre passerelle DigitagPro</p> </div> <form method='POST' class='space-y-5'> <div><label class='text-xs font-bold text-slate-500 uppercase ml-1 mb-2 block'>Email Business</label><input name='email' type='email' class='w-full p-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:border-indigo-500 outline-none transition' placeholder='admin@digitag.pro'></div> <div><label class='text-xs font-bold text-slate-500 uppercase ml-1 mb-2 block'>Mot de passe</label><input name='password' type='password' class='w-full p-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:border-indigo-500 outline-none transition' placeholder='••••••••'></div> <button class='w-full bg-indigo-600 hover:bg-indigo-500 text-white p-4 rounded-2xl font-bold shadow-lg shadow-indigo-500/20 transition transform hover:-translate-y-1'>Se connecter</button> </form> </div> </div>")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    
    if request.args.get('delete_user'):
        u = User.query.get(request.args.get('delete_user'))
        if u and not u.is_admin: db.session.delete(u); db.session.commit()
        return redirect(url_for('master_admin'))

    if request.method == 'POST' and 'update_client_id' in request.form:
        u = User.query.get(request.form.get('update_client_id'))
        if u: u.business_name = request.form.get('b_name'); u.prices_info = request.form.get('p_info'); db.session.commit()
        return redirect(url_for('master_admin'))

    users = User.query.all()
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).all()
    
    html = """
    BASE_HEAD_HERE
    <div class="flex">
        SIDEBAR_HERE
        <main class="ml-72 flex-1 p-12 bg-slate-950 min-h-screen">
            <header class="flex justify-between items-center mb-12">
                <div>
                    <h1 class="text-3xl font-black">Dashboard Master</h1>
                    <p class="text-slate-400 text-sm mt-1">Supervision globale des agents IA</p>
                </div>
                <div class="flex gap-4">
                    <div class="glass-card px-6 py-3 rounded-2xl text-center">
                        <p class="text-[10px] text-slate-500 font-bold uppercase">Clients</p>
                        <p class="text-xl font-black text-indigo-400">{{ users|length }}</p>
                    </div>
                    <div class="glass-card px-6 py-3 rounded-2xl text-center">
                        <p class="text-[10px] text-slate-500 font-bold uppercase">Appels Totaux</p>
                        <p class="text-xl font-black text-emerald-400">{{ all_rdv|length }}</p>
                    </div>
                </div>
            </header>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-12">
                <div class="xl:col-span-2 space-y-8">
                    <h2 class="text-lg font-bold flex items-center gap-2 mb-4"><i class="fas fa-bolt text-yellow-400"></i> Agents en Temps Réel</h2>
                    {% for u in users %}
                    <div class="glass-card rounded-[2rem] p-8 transition hover:shadow-indigo-500/5 hover:shadow-2xl">
                        <form method="POST">
                            <input type="hidden" name="update_client_id" value="{{ u.id }}">
                            <div class="flex justify-between items-start mb-6">
                                <div class="w-full">
                                    <span class="text-[10px] bg-slate-800 text-slate-400 px-3 py-1 rounded-full font-bold uppercase tracking-widest">ID #{{ u.id }}</span>
                                    <input name="b_name" value="{{ u.business_name }}" class="bg-transparent text-2xl font-black w-full mt-2 focus:outline-none focus:text-indigo-400 border-b border-transparent focus:border-indigo-500/30 transition">
                                </div>
                                <div class="flex gap-2">
                                    <a href="/voice/{{ u.id }}" class="w-10 h-10 flex items-center justify-center bg-indigo-500/10 text-indigo-400 rounded-xl hover:bg-indigo-600 hover:text-white transition"><i class="fas fa-phone-alt"></i></a>
                                    {% if not u.is_admin %}<a href="/master-admin?delete_user={{ u.id }}" class="w-10 h-10 flex items-center justify-center bg-red-500/10 text-red-400 rounded-xl hover:bg-red-500 hover:text-white transition"><i class="fas fa-trash-alt"></i></a>{% endif %}
                                </div>
                            </div>
                            <div class="mb-6">
                                <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Prompt d'expertise (Tarifs & Savoir-faire)</label>
                                <textarea name="p_info" rows="3" class="w-full bg-slate-900/40 border border-slate-800 rounded-2xl p-5 text-sm text-slate-300 focus:border-indigo-500/50 outline-none transition">{{ u.prices_info }}</textarea>
                            </div>
                            <button class="w-full bg-indigo-600/10 border border-indigo-600/30 text-indigo-400 py-3 rounded-2xl font-bold hover:bg-indigo-600 hover:text-white transition">Appliquer les modifications</button>
                        </form>
                    </div>
                    {% endfor %}
                </div>

                <div class="space-y-8">
                    <h2 class="text-lg font-bold flex items-center gap-2 mb-4"><i class="fas fa-list text-indigo-400"></i> Activité Globale</h2>
                    <div class="glass-card rounded-[2rem] p-6 max-h-[900px] overflow-y-auto space-y-4">
                        {% for rdv in all_rdv %}
                        <div class="p-4 bg-slate-900/40 rounded-2xl border-l-2 border-indigo-500/50">
                            <div class="flex justify-between items-center mb-1">
                                <span class="text-[10px] font-black text-indigo-400 uppercase tracking-tighter">{{ rdv.owner.business_name }}</span>
                                <span class="text-[10px] text-slate-500">{{ rdv.date_str }}</span>
                            </div>
                            <p class="text-sm text-slate-300">{{ rdv.details }}</p>
                        </div>
                        {% else %}
                        <div class="text-center py-20 text-slate-600">
                            <i class="fas fa-clock text-4xl mb-4 opacity-20"></i>
                            <p class="text-sm">En attente d'appels...</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </main>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD).replace("SIDEBAR_HERE", SIDEBAR)
    return render_template_string(html, users=users, all_rdv=all_rdv)

@app.route('/devenir-master-vite')
def dev_master():
    user = User.query.filter_by(email='romanlayani@gmail.com').first()
    if user: user.is_admin = True; db.session.commit(); return "Status: MASTER"
    return "Not Found"

# --- IA VOICE (UNCHANGED) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    system_prompt = f"Tu es l'assistant IA de '{commercant.business_name}'. Tarifs/Infos: {commercant.prices_info}. Si RDV validé, commence par CONFIRMATION_RDV: [Détail]."
    if not user_input: ai_response = f"Bonjour, bienvenue chez {commercant.business_name}, comment puis-je vous aider ?"
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