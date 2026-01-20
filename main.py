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
    prices_info = db.Column(db.Text, default="Services standards")
    appointments = db.relationship('Appointment', backref='owner', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

with app.app_context(): db.create_all()

# --- BLOCS DESIGN (SANS F-STRING POUR ÉVITER LES CRASH) ---
BASE_HEAD = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    body { font-family: 'Inter', sans-serif; background-color: #020617; color: #f8fafc; }
    .glass-card { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    .sidebar-active { background: rgba(79, 70, 229, 0.1); border-right: 4px solid #6366f1; color: #818cf8; }
</style>
"""

SIDEBAR_TEMPLATE = """
<div class="fixed w-72 h-screen bg-[#020617] border-r border-slate-800 flex flex-col p-6">
    <div class="flex items-center gap-3 mb-12 px-2">
        <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center"><i class="fas fa-microchip text-white"></i></div>
        <span class="text-xl font-extrabold italic text-indigo-500 uppercase">DigitagPro</span>
    </div>
    <nav class="flex-1 space-y-2">
        <a href="/master-admin" class="flex items-center gap-3 p-4 rounded-xl transition font-medium {% if active == 'admin' %}sidebar-active text-indigo-400{% else %}text-slate-400 hover:text-white{% endif %}"><i class="fas fa-th-large w-5"></i> Dashboard</a>
        <a href="/master-clients" class="flex items-center gap-3 p-4 rounded-xl transition font-medium {% if active == 'clients' %}sidebar-active text-indigo-400{% else %}text-slate-400 hover:text-white{% endif %}"><i class="fas fa-users w-5"></i> Clients</a>
        <a href="/master-logs" class="flex items-center gap-3 p-4 rounded-xl transition font-medium {% if active == 'logs' %}sidebar-active text-indigo-400{% else %}text-slate-400 hover:text-white{% endif %}"><i class="fas fa-phone-volume w-5"></i> Logs Appels</a>
        <a href="/master-settings" class="flex items-center gap-3 p-4 rounded-xl transition font-medium {% if active == 'settings' %}sidebar-active text-indigo-400{% else %}text-slate-400 hover:text-white{% endif %}"><i class="fas fa-cog w-5"></i> Paramètres</a>
    </nav>
    <div class="mt-auto pt-6 border-t border-slate-800">
        <a href="/logout" class="flex items-center gap-3 p-4 text-red-400 font-bold uppercase text-xs tracking-widest"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
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
    return render_template_string(BASE_HEAD + """
    <div class='min-h-screen bg-slate-950 flex items-center justify-center p-6'>
        <div class='max-w-md w-full glass-card p-10 rounded-[2.5rem] shadow-2xl border border-slate-800 text-center'>
            <h2 class='text-3xl font-black mb-10 text-indigo-500 italic uppercase'>DigitagPro</h2>
            <form method='POST' class='space-y-5'>
                <input name='email' type='email' class='w-full p-4 bg-slate-900 border border-slate-700 rounded-2xl text-white outline-none' placeholder='Email Pro'>
                <input name='password' type='password' class='w-full p-4 bg-slate-900 border border-slate-700 rounded-2xl text-white outline-none' placeholder='Mot de passe'>
                <button class='w-full bg-indigo-600 hover:bg-indigo-500 text-white p-4 rounded-2xl font-bold transition'>Ouvrir le Système</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    if request.method == 'POST':
        u = User.query.get(request.form.get('id'))
        if u: u.business_name = request.form.get('n'); u.prices_info = request.form.get('p'); db.session.commit()
    users = User.query.all()
    logs = Appointment.query.order_by(Appointment.id.desc()).limit(5).all()
    return render_template_string(BASE_HEAD + "<div class='flex'>" + SIDEBAR_TEMPLATE + """
        <main class="ml-72 flex-1 p-12 bg-[#020617]">
            <h1 class="text-4xl font-black mb-10">Command Center</h1>
            <div class="grid grid-cols-2 gap-8">
                <div class="glass-card p-8 rounded-[2rem]">
                    <h2 class="text-xl font-bold mb-6 text-indigo-400">Modification Rapide</h2>
                    {% for u in users %}
                    <form method="POST" class="mb-6 p-6 bg-slate-950/50 border border-slate-800 rounded-3xl">
                        <input type="hidden" name="id" value="{{ u.id }}">
                        <input name="n" value="{{ u.business_name }}" class="bg-transparent font-bold text-xl mb-4 w-full border-b border-transparent focus:border-indigo-500 outline-none">
                        <textarea name="p" class="w-full bg-slate-900 p-4 rounded-2xl text-sm border border-slate-800 outline-none h-24">{{ u.prices_info }}</textarea>
                        <button class="mt-4 bg-indigo-600/20 text-indigo-400 px-6 py-2 rounded-xl text-xs font-bold hover:bg-indigo-600 hover:text-white transition uppercase">Mettre à jour</button>
                    </form>
                    {% endfor %}
                </div>
                <div class="glass-card p-8 rounded-[2rem]">
                    <h2 class="text-xl font-bold mb-6 text-emerald-400 italic">Dernière activité</h2>
                    {% for r in logs %}
                    <div class="p-4 bg-slate-950/50 rounded-2xl border border-slate-800 mb-4">
                        <p class="text-[10px] font-bold text-indigo-400 uppercase mb-2">{{ r.owner.business_name }}</p>
                        <p class="text-sm italic">"{{ r.details }}"</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </main>
    </div>""", users=users, logs=logs, active='admin')

@app.route('/master-clients')
@login_required
def master_clients():
    users = User.query.all()
    return render_template_string(BASE_HEAD + "<div class='flex'>" + SIDEBAR_TEMPLATE + """
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10">Portefeuille Clients</h1>
            <div class="glass-card rounded-3xl border border-slate-800 overflow-hidden">
                <table class="w-full text-left">
                    <thead class="bg-slate-900 text-xs text-slate-500 uppercase font-bold tracking-widest"><tr class="border-b border-slate-800"><th class="p-6">Client</th><th class="p-6">Secteur</th><th class="p-6">Statut</th></tr></thead>
                    <tbody>
                    {% for u in users %}
                    <tr class="border-b border-slate-800/50 hover:bg-slate-800/20 transition">
                        <td class="p-6 font-bold text-lg">{{ u.business_name }}</td>
                        <td class="p-6 text-slate-400">{{ u.activity_sector }}</td>
                        <td class="p-6"><span class="px-3 py-1 bg-green-500/10 text-green-500 rounded-full text-[10px] font-bold">ACTIF</span></td>
                    </tr>
                    {% endfor %}
                    </tbody>
                </table>
            </div>
        </main></div>""", users=users, active='clients')

@app.route('/master-logs')
@login_required
def master_logs():
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    return render_template_string(BASE_HEAD + "<div class='flex'>" + SIDEBAR_TEMPLATE + """
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10">Logs Complets</h1>
            {% for r in logs %}
            <div class="glass-card p-6 rounded-3xl border border-slate-800 mb-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-bold text-indigo-400">{{ r.owner.business_name }}</span>
                    <span class="text-[10px] text-slate-500 uppercase">{{ r.date_str }}</span>
                </div>
                <p class="text-sm text-slate-300">"{{ r.details }}"</p>
            </div>
            {% endfor %}
        </main></div>""", logs=logs, active='logs')

@app.route('/master-settings', methods=['GET', 'POST'])
@login_required
def master_settings():
    if request.method == 'POST': current_user.password = request.form.get('p'); db.session.commit()
    return render_template_string(BASE_HEAD + "<div class='flex'>" + SIDEBAR_TEMPLATE + """
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10">Sécurité</h1>
            <div class="max-w-md glass-card p-8 rounded-3xl border border-slate-800">
                <form method="POST" class="space-y-4">
                    <input name="p" type="password" placeholder="Nouveau mot de passe" class="w-full p-4 bg-slate-900 border border-slate-800 rounded-2xl text-white outline-none">
                    <button class="w-full bg-indigo-600 p-4 rounded-2xl font-bold">Mettre à jour</button>
                </form>
            </div>
        </main></div>""", active='settings')

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "Status: MASTER"
    return "Not Found"

# --- IA VOICE (TWILIO) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    if not txt: ai = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": f"Tu es l'assistant de {c.business_name}. Tarifs/Infos: {c.prices_info}. Si RDV validé, CONFIRMATION_RDV: [Détail]."}, {"role": "user", "content": txt}])
        ai = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in ai:
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=ai.split("CONFIRMATION_RDV:")[1].strip(), user_id=c.id)
            db.session.add(new_rdv); db.session.commit()
            ai = ai.split("CONFIRMATION_RDV:")[0]
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)