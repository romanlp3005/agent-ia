from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_ultimate_2026'

# --- DATABASE CONFIG ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    activity_sector = db.Column(db.String(100), default="Services")
    is_admin = db.Column(db.Boolean, default=False)
    prices_info = db.Column(db.Text, default="Services et tarifs standards.")
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

with app.app_context(): db.create_all()

# --- UI ASSETS ---
HEAD = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    body { font-family: 'Inter', sans-serif; }
    .glass { background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
    .sidebar-item:hover { background: rgba(99, 102, 241, 0.1); color: #818cf8; }
    .active-nav { background: rgba(99, 102, 241, 0.15); border-right: 4px solid #6366f1; color: #818cf8; }
</style>
"""

def master_layout(content, page="admin"):
    sidebar = f"""
    <div class="fixed w-72 h-screen bg-[#020617] border-r border-slate-800 flex flex-col p-6 text-white">
        <div class="text-2xl font-black text-indigo-500 mb-12 italic uppercase tracking-tighter">DigitagPro IA</div>
        <nav class="flex-1 space-y-2">
            <a href="/master-admin" class="flex items-center gap-3 p-4 rounded-xl sidebar-item {'active-nav' if page=='admin' else ''} transition"><i class="fas fa-th-large w-5"></i> Dashboard</a>
            <a href="/master-clients" class="flex items-center gap-3 p-4 rounded-xl sidebar-item {'active-nav' if page=='clients' else ''} transition"><i class="fas fa-users w-5"></i> Clients</a>
            <a href="/master-logs" class="flex items-center gap-3 p-4 rounded-xl sidebar-item {'active-nav' if page=='logs' else ''} transition"><i class="fas fa-phone-volume w-5"></i> Logs d'appels</a>
        </nav>
        <div class="pt-6 border-t border-slate-800"><a href="/logout" class="text-red-400 font-bold p-4 text-xs uppercase">Déconnexion</a></div>
    </div>
    """
    return f"{HEAD}<body class='bg-[#020617] text-white flex'>{sidebar}<main class='ml-72 flex-1 p-12'>{content}</main></body>"

# --- CORE ROUTES ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('master_admin' if u.is_admin else 'dashboard'))
    return render_template_string(HEAD + """
    <body class="bg-slate-950 flex items-center justify-center h-screen">
        <form method="POST" class="bg-slate-900 p-12 rounded-[3rem] border border-slate-800 w-[400px] shadow-2xl">
            <h2 class="text-3xl font-black text-white mb-10 text-center italic text-indigo-500 uppercase">Connexion</h2>
            <div class="space-y-6">
                <input name="email" type="email" placeholder="Email Professionnel" class="w-full p-5 bg-slate-950 border border-slate-800 rounded-2xl text-white focus:border-indigo-500 outline-none transition">
                <input name="password" type="password" placeholder="Mot de passe" class="w-full p-5 bg-slate-950 border border-slate-800 rounded-2xl text-white focus:border-indigo-500 outline-none transition">
                <button class="w-full bg-indigo-600 p-5 rounded-2xl font-black text-white hover:bg-indigo-500 transition shadow-lg shadow-indigo-500/20">ENTRER DANS LE SYSTÈME</button>
            </div>
            <p class="text-center mt-8 text-slate-500 text-xs font-bold uppercase tracking-widest">DigitagPro © 2026</p>
        </form>
    </body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_u = User(email=request.form.get('email'), password=request.form.get('password'), 
                    business_name=request.form.get('b_name'), activity_sector=request.form.get('sector'))
        db.session.add(new_u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(HEAD + """<body class="bg-slate-50 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[3rem] shadow-xl w-[450px]">
        <h2 class="text-2xl font-black mb-8">Créer votre compte IA</h2>
        <div class="space-y-4">
            <input name="b_name" placeholder="Nom de votre entreprise" class="w-full p-4 bg-slate-100 rounded-2xl outline-none" required>
            <input name="sector" placeholder="Secteur (ex: Garage)" class="w-full p-4 bg-slate-100 rounded-2xl outline-none" required>
            <input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-100 rounded-2xl outline-none" required>
            <input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-100 rounded-2xl outline-none" required>
            <button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black mt-4 transition">DEMARRER MAINTENANT</button>
        </div></form></body>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- MASTER VIEWS ---
@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = User.query.get(request.form.get('id'))
        if u: u.business_name = request.form.get('n'); u.prices_info = request.form.get('p'); db.session.commit()
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(5).all()
    content = """
    <h1 class="text-4xl font-black mb-10">Command Center</h1>
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-10">
        <div class="glass p-10 rounded-[2.5rem]">
            <h3 class="text-indigo-400 font-bold mb-6 flex items-center gap-2 uppercase tracking-widest text-xs"><i class="fas fa-edit"></i> Pilotage des Agents</h3>
            {% for u in users %}<form method="POST" class="mb-8 p-6 bg-slate-900/50 rounded-3xl border border-slate-800">
                <input type="hidden" name="id" value="{{u.id}}">
                <input name="n" value="{{u.business_name}}" class="bg-transparent text-xl font-bold w-full mb-4 focus:text-indigo-400 outline-none border-b border-transparent focus:border-indigo-500/50">
                <textarea name="p" rows="3" class="w-full bg-slate-950 p-4 rounded-2xl text-sm text-slate-400 outline-none border border-slate-800 focus:border-indigo-500/50">{{u.prices_info}}</textarea>
                <button class="mt-4 bg-indigo-600/10 text-indigo-400 px-6 py-2 rounded-xl text-[10px] font-bold uppercase hover:bg-indigo-600 hover:text-white transition">Appliquer</button>
            </form>{% endfor %}
        </div>
        <div class="glass p-10 rounded-[2.5rem]">
            <h3 class="text-emerald-400 font-bold mb-6 flex items-center gap-2 uppercase tracking-widest text-xs"><i class="fas fa-broadcast-tower"></i> Activité Globale</h3>
            {% for r in logs %}<div class="p-6 bg-slate-950 rounded-3xl border border-slate-800 mb-4 border-l-4 border-emerald-500">
                <div class="flex justify-between mb-2"><span class="text-[10px] font-black uppercase text-emerald-500">{{r.owner.business_name}}</span><span class="text-[10px] text-slate-500 uppercase">{{r.date_str}}</span></div>
                <p class="text-sm italic text-slate-300">"{{r.details}}"</p>
            </div>{% endfor %}
        </div>
    </div>"""
    return render_template_string(master_layout(content, "admin"), users=users, logs=logs)

@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = """<h1 class="text-3xl font-black mb-10">Portefeuille Clients</h1>
    <div class="glass rounded-[2.5rem] overflow-hidden">
        <table class="w-full text-left">
            <thead class="bg-slate-900/50 text-xs font-bold uppercase tracking-widest text-slate-500"><tr><th class="p-8">Entreprise</th><th class="p-8">Secteur</th><th class="p-8">Identifiant</th><th class="p-8">Action</th></tr></thead>
            <tbody class="divide-y divide-slate-800">
                {% for u in users %}<tr><td class="p-8 font-bold text-lg">{{u.business_name}}</td><td class="p-8"><span class="bg-indigo-500/10 text-indigo-400 px-3 py-1 rounded-full text-[10px] font-bold uppercase">{{u.activity_sector}}</span></td><td class="p-8 text-slate-500">{{u.email}}</td><td class="p-8"><a href="/voice/{{u.id}}" class="text-indigo-500 hover:text-white"><i class="fas fa-phone"></i></a></td></tr>{% endfor %}
            </tbody>
        </table>
    </div>"""
    return render_template_string(master_layout(content, "clients"), users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = """<h1 class="text-3xl font-black mb-10">Historique Complet</h1>
    <div class="space-y-4">
        {% for r in logs %}<div class="glass p-8 rounded-[2rem] flex justify-between items-center">
            <div class="flex-1">
                <span class="text-xs font-black text-indigo-400 uppercase tracking-widest">{{r.owner.business_name}}</span>
                <p class="text-slate-200 mt-2 text-lg italic">"{{r.details}}"</p>
            </div>
            <div class="text-right ml-10"><p class="text-[10px] text-slate-600 font-bold uppercase">{{r.date_str}}</p></div>
        </div>{% endfor %}
    </div>"""
    return render_template_string(master_layout(content, "logs"), logs=logs)

# --- CLIENT DASHBOARD ---
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        current_user.business_name = request.form.get('b_name'); current_user.prices_info = request.form.get('p_info')
        db.session.commit(); return redirect(url_for('dashboard'))
    return render_template_string(HEAD + """<body class="bg-slate-50 text-slate-900 flex">
        <div class="fixed w-64 h-screen bg-slate-900 p-8 flex flex-col text-white">
            <div class="text-xl font-black mb-12">DIGITAGPRO IA</div>
            <nav class="flex-1 space-y-4"><a href="/dashboard" class="flex items-center gap-3 p-3 bg-indigo-600 rounded-xl"><i class="fas fa-home"></i> Mon Espace</a></nav>
            <a href="/logout" class="mt-auto text-slate-500 hover:text-white font-bold">Quitter</a>
        </div>
        <main class="ml-64 flex-1 p-16">
            <h1 class="text-4xl font-black mb-12">Mon Agent IA</h1>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-12">
                <div class="bg-white p-10 rounded-[3rem] shadow-sm border border-slate-100">
                    <h2 class="text-lg font-bold mb-8">Réglages de l'Agent</h2>
                    <form method="POST" class="space-y-6">
                        <input name="b_name" value="{{current_user.business_name}}" class="w-full p-4 bg-slate-50 rounded-2xl border-none" placeholder="Nom Commercial">
                        <textarea name="p_info" rows="8" class="w-full p-4 bg-slate-50 rounded-2xl border-none outline-none" placeholder="Décrivez vos services et tarifs...">{{current_user.prices_info}}</textarea>
                        <button class="w-full bg-slate-900 text-white p-5 rounded-2xl font-bold hover:bg-indigo-600 transition">SAUVEGARDER</button>
                    </form>
                </div>
                <div class="bg-white p-10 rounded-[3rem] shadow-sm border border-slate-100">
                    <h2 class="text-lg font-bold mb-8 italic">Dernières Réservations</h2>
                    {% for r in current_user.appointments|reverse %}<div class="p-5 border-b border-slate-50"><span class="text-indigo-600 font-bold text-sm">{{r.date_str}}</span><p class="text-slate-600 mt-2 italic text-sm">"{{r.details}}"</p></div>{% endfor %}
                </div>
            </div>
        </main></body>""")

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "OK MASTER"
    return "Not Found"

# --- IA ENGINE (VOICE) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    if not txt: ai = "Bonjour, bienvenue chez " + c.business_name + ", que puis-je faire pour vous ?"
    else:
        prompt = "Tu es l'assistant vocal de " + c.business_name + ". Infos/Tarifs: " + c.prices_info + ". Si le client valide un RDV, commence obligatoirement par 'CONFIRMATION_RDV: [détail du RDV]'."
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
        ai = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in ai:
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=ai.split("CONFIRMATION_RDV:")[1].strip(), user_id=c.id)
            db.session.add(new_rdv); db.session.commit(); ai = ai.split("CONFIRMATION_RDV:")[0]
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai, language='fr-FR'); resp.append(g); resp.redirect('/voice/' + str(user_id))
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)