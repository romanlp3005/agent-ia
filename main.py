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
    body { font-family: 'Inter', sans-serif; background-color: #020617; color: #f8fafc; }
    .glass-card { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    .sidebar-active { background: rgba(79, 70, 229, 0.1); border-right: 4px solid #6366f1; color: #818cf8; }
</style>
"""

def get_sidebar(active_page):
    links = [
        ('Dashboard', '/master-admin', 'fa-th-large'),
        ('Clients', '/master-clients', 'fa-users'),
        ('Logs Appels', '/master-logs', 'fa-phone-volume'),
        ('Paramètres', '/master-settings', 'fa-cog')
    ]
    html = f"""
    <div class="fixed w-72 h-screen bg-[#020617] border-r border-slate-800 flex flex-col p-6">
        <div class="flex items-center gap-3 mb-12 px-2">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <i class="fas fa-microchip text-white"></i>
            </div>
            <span class="text-xl font-extrabold tracking-tight italic text-indigo-500">DIGITAGPRO</span>
        </div>
        <nav class="flex-1 space-y-2">
    """
    for name, url, icon in links:
        active_class = "sidebar-active" if active_page == url else "text-slate-400 hover:text-white"
        html += f'<a href="{url}" class="flex items-center gap-3 p-4 rounded-xl transition font-medium {active_class}"><i class="fas {icon} w-5"></i> {name}</a>'
    
    html += """
        </nav>
        <div class="mt-auto pt-6 border-t border-slate-800">
            <a href="/logout" class="flex items-center gap-3 p-4 rounded-xl text-red-400 hover:bg-red-500/10 transition font-bold uppercase text-xs tracking-widest"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
        </div>
    </div>
    """
    return html

# --- ROUTES PRINCIPALES ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('master_admin' if user.is_admin else 'dashboard'))
    return render_template_string(f"{BASE_HEAD} <div class='min-h-screen bg-slate-950 flex items-center justify-center p-6'> <div class='max-w-md w-full glass-card p-10 rounded-[2.5rem] shadow-2xl border border-slate-800'> <div class='text-center mb-10'> <h2 class='text-3xl font-black mb-2'>Connexion</h2> <p class='text-slate-400 text-sm italic font-bold'>Passerelle Administrateur</p> </div> <form method='POST' class='space-y-5'> <div><label class='text-[10px] font-bold text-slate-500 uppercase ml-1 mb-2 block'>Email Pro</label><input name='email' type='email' class='w-full p-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:border-indigo-500 outline-none transition' placeholder='admin@digitag.pro'></div> <div><label class='text-[10px] font-bold text-slate-500 uppercase ml-1 mb-2 block'>Mot de passe</label><input name='password' type='password' class='w-full p-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:border-indigo-500 outline-none transition' placeholder='••••••••'></div> <button class='w-full bg-indigo-600 hover:bg-indigo-500 text-white p-4 rounded-2xl font-bold shadow-lg shadow-indigo-500/20 transition transform hover:-translate-y-1'>Ouvrir le Système</button> </form> </div> </div>")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- DASHBOARD MASTER (ACCUEIL) ---
@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    if request.method == 'POST' and 'update_client_id' in request.form:
        u = User.query.get(request.form.get('update_client_id'))
        if u: u.business_name = request.form.get('b_name'); u.prices_info = request.form.get('p_info'); db.session.commit()
    
    users = User.query.all()
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).limit(10).all()
    
    html = f"""
    {BASE_HEAD}
    <div class="flex">
        {get_sidebar('/master-admin')}
        <main class="ml-72 flex-1 p-12 bg-[#020617] min-h-screen">
            <h1 class="text-4xl font-black mb-10">Command Center</h1>
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <div class="glass-card p-8 rounded-[2rem]">
                    <h2 class="text-xl font-bold mb-6 text-indigo-400">Modification Rapide</h2>
                    {% for u in users %}
                    <form method="POST" class="mb-6 p-4 border border-slate-800 rounded-2xl">
                        <input type="hidden" name="update_client_id" value="{{ u.id }}">
                        <input name="b_name" value="{{ u.business_name }}" class="bg-transparent font-bold text-lg focus:outline-none mb-2 w-full border-b border-transparent focus:border-indigo-500">
                        <textarea name="p_info" class="w-full bg-slate-950 p-3 rounded-xl text-xs border border-slate-800 focus:outline-none focus:border-indigo-500" rows="2">{{ u.prices_info }}</textarea>
                        <button class="mt-2 text-[10px] font-bold text-indigo-500 uppercase tracking-widest hover:text-white transition">Appliquer</button>
                    </form>
                    {% endfor %}
                </div>
                <div class="glass-card p-8 rounded-[2rem]">
                    <h2 class="text-xl font-bold mb-6 text-emerald-400 font-bold italic underline">Derniers Appels</h2>
                    <div class="space-y-4">
                        {% for rdv in all_rdv %}
                        <div class="p-4 bg-slate-950/50 rounded-xl border border-slate-800">
                            <p class="text-[10px] font-bold text-slate-500 uppercase">{{ rdv.owner.business_name }} - {{ rdv.date_str }}</p>
                            <p class="text-sm italic">"{{ rdv.details }}"</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </main>
    </div>
    """
    return render_template_string(html, users=users, all_rdv=all_rdv)

# --- PAGE CLIENTS ---
@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return "Accès refusé", 403
    users = User.query.all()
    html = f"""
    {BASE_HEAD}
    <div class="flex">
        {get_sidebar('/master-clients')}
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10">Portefeuille Clients</h1>
            <div class="glass-card rounded-[2.5rem] overflow-hidden border border-slate-800">
                <table class="w-full text-left">
                    <thead class="bg-slate-900/50 text-slate-500 text-xs font-bold uppercase tracking-widest border-b border-slate-800">
                        <tr>
                            <th class="p-6">Client</th><th class="p-6">Email</th><th class="p-6">Secteur</th><th class="p-6 text-center">Action</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {% for u in users %}
                        <tr class="hover:bg-slate-900/20 transition">
                            <td class="p-6 font-bold">{{ u.business_name }}</td>
                            <td class="p-6 text-slate-400">{{ u.email }}</td>
                            <td class="p-6"><span class="px-3 py-1 bg-indigo-500/10 text-indigo-400 rounded-full text-[10px] font-bold uppercase">{{ u.activity_sector }}</span></td>
                            <td class="p-6 text-center"><a href="/voice/{{ u.id }}" class="text-indigo-500 hover:text-white"><i class="fas fa-phone"></i></a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </main>
    </div>
    """
    return render_template_string(html, users=users)

# --- PAGE LOGS ---
@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return "Accès refusé", 403
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).all()
    html = f"""
    {BASE_HEAD}
    <div class="flex">
        {get_sidebar('/master-logs')}
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10 italic">Transcriptions & Logs</h1>
            <div class="space-y-4">
                {% for rdv in all_rdv %}
                <div class="glass-card p-6 rounded-3xl border border-slate-800 flex justify-between items-center">
                    <div>
                        <span class="text-[10px] text-indigo-400 font-black uppercase tracking-widest">{{ rdv.owner.business_name }}</span>
                        <p class="text-slate-300 mt-1">"{{ rdv.details }}"</p>
                    </div>
                    <div class="text-right text-xs text-slate-500 font-bold uppercase">{{ rdv.date_str }}</div>
                </div>
                {% endfor %}
            </div>
        </main>
    </div>
    """
    return render_template_string(html, all_rdv=all_rdv)

# --- PAGE PARAMETRES ---
@app.route('/master-settings', methods=['GET', 'POST'])
@login_required
def master_settings():
    if not current_user.is_admin: return "Accès refusé", 403
    if request.method == 'POST':
        current_user.password = request.form.get('new_pass')
        db.session.commit()
        flash("Mot de passe mis à jour !")
    
    html = f"""
    {BASE_HEAD}
    <div class="flex">
        {get_sidebar('/master-settings')}
        <main class="ml-72 flex-1 p-12">
            <h1 class="text-3xl font-black mb-10">Paramètres Système</h1>
            <div class="max-w-xl glass-card p-8 rounded-[2.5rem] border border-slate-800">
                <h3 class="font-bold mb-6 text-indigo-400">Modifier mon mot de passe</h3>
                <form method="POST" class="space-y-4">
                    <input name="new_pass" type="password" placeholder="Nouveau mot de passe" class="w-full p-4 bg-slate-950 border border-slate-800 rounded-2xl focus:border-indigo-500 outline-none">
                    <button class="w-full bg-indigo-600 p-4 rounded-2xl font-bold">Sauvegarder</button>
                </form>
            </div>
        </main>
    </div>
    """
    return render_template_string(html)

@app.route('/devenir-master-vite')
def dev_master():
    user = User.query.filter_by(email='romanlayani@gmail.com').first()
    if user: user.is_admin = True; db.session.commit(); return "Status: MASTER"
    return "Not Found"

# --- IA VOICE (TWILIO) ---
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