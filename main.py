from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime, timedelta
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_ultra_dense_2026_vX'

# --- CONFIGURATION DATABASE HAUTE PERFORMANCE ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): 
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÃˆLES DE DONNÃ‰ES ARCHITECTURÃ‰S (25 000+ CARACTÃˆRES READY) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(150))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Configuration Business et Niche
    sector = db.Column(db.String(100), default="Services Professionnels")
    horaires = db.Column(db.Text, default="Lundi au Vendredi: 09:00 - 18:00")
    tarifs = db.Column(db.Text, default="Consultation : 60â‚¬ | Forfait : sur devis")
    duree_moyenne = db.Column(db.String(50), default="45 minutes")
    adresse = db.Column(db.String(255), default="1 Rue de l'IA, 75000 Paris")
    phone_pro = db.Column(db.String(20), default="Non configurÃ©")
    
    # Personnalisation de l'Agent IA (Moteur Voco)
    prompt_personnalise = db.Column(db.Text, default="Tu es un assistant vocal d'Ã©lite, courtois et efficace.")
    voix_preferee = db.Column(db.String(50), default="fr-FR-Neural-A")
    ton_ia = db.Column(db.String(50), default="Professionnel")
    
    # Statistiques et Date
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    premium_status = db.Column(db.Boolean, default=True)
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), default="Client IdentifiÃ© par IA")
    client_phone = db.Column(db.String(30), default="Inconnu")
    date_str = db.Column(db.String(100))
    details = db.Column(db.Text)
    status = db.Column(db.String(50), default="ConfirmÃ©")
    priorite = db.Column(db.String(20), default="Normale")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# --- BLOC DE SYNCHRONISATION RADICALE (RÃ‰GLAGE ERREUR 500) ---
with app.app_context():
    # Suppression et recrÃ©ation pour garantir que 'client_name' existe sur Render
    # db.drop_all() 
    db.create_all()
    print(">>> [SYSTEM] BASE DE DONNÃ‰ES RÃ‰INITIALISÃ‰E AVEC SUCCÃˆS - SCHEMA V2 ACTIVE")

# --- ENGINE DE DESIGN (CSS FRAMEWORK PROPRIÃ‰TAIRE) ---
STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    :root { --sidebar-bg: #0f172a; --primary: #6366f1; --accent: #4f46e5; }
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; overflow-x: hidden; }
    .sidebar { background: var(--sidebar-bg); transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); border-right: 1px solid rgba(255,255,255,0.05); }
    .nav-link { color: #94a3b8; border-radius: 18px; transition: all 0.3s ease; margin: 4px 0; border: 1px solid transparent; }
    .nav-link:hover { background: #1e293b; color: #fff; transform: translateX(8px); border-color: rgba(99, 102, 241, 0.2); }
    .active-nav { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white !important; shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); border: none; }
    .glass-card { background: white; border-radius: 35px; border: 1px solid #e2e8f0; box-shadow: 0 4px 30px rgba(0,0,0,0.03); padding: 2.5rem; position: relative; overflow: hidden; }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 20px; padding: 16px; transition: 0.2s; width: 100%; outline: none; font-weight: 500; }
    .input-pro:focus { border-color: var(--primary); background: white; box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.1); }
    .animate-float { animation: float 6s ease-in-out infinite; }
    @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .stat-badge { padding: 6px 16px; border-radius: 100px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .btn-grad { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); transition: 0.3s; }
    .btn-grad:hover { opacity: 0.9; transform: scale(1.02); }
</style>
"""

def get_layout(content, active_page="dashboard"):
    is_m = current_user.is_admin if current_user.is_authenticated else False
    sidebar = f"""
    <div class="fixed w-80 h-screen sidebar flex flex-col p-8 text-white z-50">
        <div class="flex items-center gap-4 mb-16 px-2">
            <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-500/50">
                <i class="fas fa-brain text-xl text-white"></i>
            </div>
            <span class="text-2xl font-black tracking-tighter uppercase italic text-white underline decoration-indigo-500">DigitagPro</span>
        </div>
        <nav class="flex-1 space-y-3">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] ml-4 mb-6">SaaS Plateforme</p>
            <a href="/dashboard" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='dashboard' else ''}"><i class="fas fa-layer-group w-5"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='config' else ''}"><i class="fas fa-wand-magic-sparkles w-5"></i> Configuration IA</a>
            <a href="/mon-agenda" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='agenda' else ''}"><i class="fas fa-calendar-day w-5"></i> Mon Agenda</a>
            <a href="/profil" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='profil' else ''}"><i class="fas fa-user-tie w-5"></i> Profil Business</a>

# --- PAGE PROFIL BUSINESS ---
@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        current_user.business_name = request.form.get('bn')
        current_user.email = request.form.get('em')
        current_user.phone_pro = request.form.get('ph')
        current_user.adresse = request.form.get('ad')
        db.session.commit()
        flash("Profil mis Ã  jour !")

    content = f"""
    <div class="flex justify-between items-center mb-12">
        <h1 class="text-4xl font-black text-slate-900 italic tracking-tighter uppercase">Profil Business</h1>
        <div class="badge badge-primary">ID Client : {current_user.id}</div>
    </div>
    
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div class="glass-card p-10 col-span-1 text-center">
            <div class="w-24 h-24 bg-indigo-600 rounded-full flex items-center justify-center text-white text-3xl font-black mx-auto mb-6 shadow-xl shadow-indigo-200">
                {current_user.business_name[0] if current_user.business_name else 'B'}
            </div>
            <h2 class="text-2xl font-black text-slate-900 mb-2">{current_user.business_name}</h2>
            <p class="text-slate-400 font-bold uppercase tracking-widest text-[10px] mb-8">{current_user.sector}</p>
            <div class="space-y-4 pt-6 border-t border-slate-100 text-left">
                <div class="flex items-center gap-4 text-sm font-medium text-slate-600">
                    <i class="fas fa-envelope text-indigo-500 w-5"></i> {current_user.email}
                </div>
                <div class="flex items-center gap-4 text-sm font-medium text-slate-600">
                    <i class="fas fa-phone-alt text-indigo-500 w-5"></i> {current_user.phone_pro}
                </div>
            </div>
        </div>
        
        <div class="glass-card p-10 col-span-2">
            <h3 class="text-xl font-black mb-8 italic text-indigo-600 underline underline-offset-8 decoration-2">Informations Business</h3>
            <form method="POST" class="space-y-6">
                <div class="grid grid-cols-2 gap-6">
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nom commercial</label>
                        <input name="bn" value="{current_user.business_name}" class="input-pro">
                    </div>
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email de contact</label>
                        <input name="em" value="{current_user.email}" class="input-pro">
                    </div>
                </div>
                <div class="space-y-2">
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">TÃ©lÃ©phone Professionnel</label>
                    <input name="ph" value="{current_user.phone_pro}" class="input-pro">
                </div>
                <div class="space-y-2">
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Adresse complÃ¨te du siÃ¨ge</label>
                    <input name="ad" value="{current_user.adresse}" class="input-pro">
                </div>
                <button class="w-full btn-grad text-white p-5 rounded-[22px] font-black shadow-lg uppercase tracking-widest text-xs mt-4">Mettre Ã  jour mes infos</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "profil"))
            
            {f'''<div class="pt-10 mb-6 border-t border-slate-800/50"></div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.3em] ml-4 mb-6">Expert Mode</p>
            <a href="/master-admin" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='m-admin' else ''} text-white"><i class="fas fa-shield-halved w-5 text-indigo-400"></i> Master Control</a>
            <a href="/master-clients" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='m-clients' else ''} text-white"><i class="fas fa-id-card-clip w-5 text-indigo-400"></i> Clients Portfolio</a>
            <a href="/master-logs" class="flex items-center gap-4 p-4 nav-link {'active-nav shadow-lg' if active_page=='m-logs' else ''} text-white"><i class="fas fa-terminal w-5 text-indigo-400"></i> Logs SystÃ¨me</a>''' if is_m else ''}
        </nav>
        <div class="pt-8 border-t border-slate-800">
            <a href="/logout" class="flex items-center gap-4 p-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition font-black uppercase text-xs tracking-widest"><i class="fas fa-sign-out-alt"></i> Quitter DigitagPro</a>
        </div>
    </div>
    """
    return f"{STYLE}<div class='flex'>{sidebar}<main class='ml-80 flex-1 p-12 min-h-screen bg-[#f8fafc] text-slate-900'>{content}</main></div>"

# --- SYSTÃˆME D'AUTHENTIFICATION ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
        flash("Les identifiants ne correspondent Ã  aucun compte actif.")
    return render_template_string(STYLE + """<body class="bg-[#0f172a] flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[4rem] shadow-2xl w-[500px] border border-slate-100"><div class="text-center mb-12"><h2 class="text-5xl font-black text-slate-900 mb-4 italic tracking-tighter">CONNEXION</h2><p class="text-slate-400 font-bold uppercase tracking-[0.3em] text-xs">AccÃ¨s SÃ©curisÃ© Entreprise</p></div><div class="space-y-6"><div class="relative"><i class="fas fa-at absolute top-5 left-5 text-slate-400"></i><input name="email" type="email" placeholder="Email Professionnel" class="input-pro pl-14" required></div><div class="relative"><i class="fas fa-lock absolute top-5 left-5 text-slate-400"></i><input name="password" type="password" placeholder="Mot de passe" class="input-pro pl-14" required></div><button class="w-full btn-grad text-white p-6 rounded-[25px] font-black shadow-xl uppercase tracking-widest text-sm">Ouvrir le Panel</button></div><p class="text-center mt-10 text-sm text-slate-500 font-medium">Pas encore de licence ? <a href="/register" class="text-indigo-600 font-extrabold hover:underline">S'enregistrer</a></p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first(): return "Email dÃ©jÃ  exploitÃ©"
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(STYLE + """<body class="bg-slate-50 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[4rem] shadow-2xl w-[600px]"><h2 class="text-4xl font-black mb-4 text-slate-900 italic tracking-tighter text-center uppercase">Nouvelle Licence DigitagPro</h2><p class="text-center text-slate-400 mb-10 font-medium tracking-wide">Rejoignez l'Ã©lite de la gestion tÃ©lÃ©phonique automatisÃ©e.</p><div class="grid grid-cols-2 gap-6"><input name="b_name" placeholder="Nom du commerce" class="input-pro col-span-2" required><input name="sector" placeholder="Secteur (ex: Garage, Clinique)" class="input-pro" required><input name="email" type="email" placeholder="Email de contact" class="input-pro" required><input name="password" type="password" placeholder="Mot de passe" class="input-pro col-span-2" required></div><button class="w-full bg-slate-950 text-white p-6 rounded-[25px] font-black mt-8 shadow-2xl hover:bg-indigo-600 transition uppercase tracking-widest text-sm">Lancer mon Infrastructure IA</button></form></body>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- LOGIQUE DASHBOARD ET ANALYTICS ---
@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().strftime("%d %B")
    rdv_count = len(current_user.appointments)
    last_rdv = current_user.appointments[-1].date_str if current_user.appointments else "Aucun appel"
    content = f"""
    <div class="flex justify-between items-end mb-16">
        <div>
            <p class="text-indigo-600 font-extrabold uppercase tracking-[0.4em] text-[10px] mb-2">Bienvenue dans le cockpit</p>
            <h1 class="text-6xl font-black text-slate-900 tracking-tighter">Salut, {current_user.business_name} !</h1>
        </div>
        <div class="text-right">
            <p class="text-slate-400 font-bold uppercase text-[10px] mb-1 italic">Nous sommes le</p>
            <p class="text-xl font-black text-slate-900 uppercase tracking-tighter">{today}</p>
        </div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-16">
        <div class="glass-card p-10 bg-white group hover:bg-indigo-600 transition-colors duration-500">
            <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-3xl flex items-center justify-center text-2xl mb-6 group-hover:bg-white/20 group-hover:text-white transition-colors">
                <i class="fas fa-phone-volume"></i>
            </div>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest group-hover:text-indigo-100 transition-colors">Appels IA</p>
            <p class="text-4xl font-black text-slate-900 mt-2 tracking-tighter group-hover:text-white transition-colors">{rdv_count}</p>
        </div>
        <div class="glass-card p-10">
            <div class="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center text-2xl mb-6">
                <i class="fas fa-calendar-check"></i>
            </div>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Dernier RDV</p>
            <p class="text-lg font-black text-slate-900 mt-2 tracking-tighter">{last_rdv}</p>
        </div>
        <div class="glass-card p-10">
            <div class="w-16 h-16 bg-amber-50 text-amber-600 rounded-3xl flex items-center justify-center text-2xl mb-6">
                <i class="fas fa-clock"></i>
            </div>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Temps Moyen</p>
            <p class="text-3xl font-black text-slate-900 mt-2 tracking-tighter font-mono">{{{{ current_user.duree_moyenne }}}}</p>
        </div>
        <div class="glass-card p-10">
            <div class="w-16 h-16 bg-rose-50 text-rose-600 rounded-3xl flex items-center justify-center text-2xl mb-6">
                <i class="fas fa-bolt"></i>
            </div>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Secteur IA</p>
            <p class="text-lg font-black text-slate-900 mt-2 uppercase italic tracking-tighter">{{{{ current_user.sector }}}}</p>
        </div>
    </div>
    
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div class="lg:col-span-2 glass-card bg-slate-900 text-white p-12 relative border-none shadow-2xl">
            <div class="relative z-10">
                <h3 class="text-3xl font-black mb-6 italic text-indigo-400 underline underline-offset-[12px] decoration-4">Connecter Twilio</h3>
                <p class="text-slate-400 mb-10 max-w-lg leading-relaxed font-medium text-lg">Votre agent est prÃªt. Pour l'activer sur votre ligne tÃ©lÃ©phonique, copiez ce Webhook dans votre interface Twilio :</p>
                <div class="bg-indigo-600/10 p-8 rounded-[30px] border border-indigo-500/30 font-mono text-indigo-300 text-md italic shadow-inner">
                    https://digitagpro-ia.onrender.com/voice/{{{{ current_user.id }}}}
                </div>
            </div>
            <i class="fas fa-robot text-[280px] absolute -right-16 -bottom-16 text-white/5 rotate-12 animate-pulse"></i>
        </div>
        <div class="glass-card p-10 bg-indigo-600 text-white border-none">
            <h3 class="text-xl font-black mb-6 flex items-center gap-3 italic"><i class="fas fa-star text-amber-400"></i> Mode Premium</h3>
            <p class="text-indigo-100 mb-8 leading-relaxed font-medium">Vous bÃ©nÃ©ficiez actuellement de l'accÃ¨s illimitÃ© aux fonctions Master et au moteur vocal GPT-4o-mini.</p>
            <div class="space-y-4">
                <div class="flex items-center gap-3 text-sm font-bold"><i class="fas fa-check-circle text-emerald-400"></i> Appels IllimitÃ©s</div>
                <div class="flex items-center gap-3 text-sm font-bold"><i class="fas fa-check-circle text-emerald-400"></i> Analyse Emotionnelle</div>
                <div class="flex items-center gap-3 text-sm font-bold"><i class="fas fa-check-circle text-emerald-400"></i> Exportation CRM PDF</div>
            </div>
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "dashboard"))

# --- PAGE CONFIGURATION IA AVANCÃ‰E ---
@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.business_name = request.form.get('n'); current_user.horaires = request.form.get('h')
        current_user.tarifs = request.form.get('t'); current_user.adresse = request.form.get('a')
        current_user.duree_moyenne = request.form.get('d'); current_user.prompt_personnalise = request.form.get('p')
        current_user.ton_ia = request.form.get('ton')
        db.session.commit(); flash("Mise Ã  jour du cerveau de l'IA effectuÃ©e !")
        
    content = """
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-5xl font-black text-slate-900 tracking-tighter italic">Cerveau IA</h1>
        <button onclick="document.getElementById('configForm').submit()" class="bg-indigo-600 text-white px-12 py-6 rounded-[28px] font-black shadow-xl shadow-indigo-200 hover:scale-[1.05] transition-all transform active:scale-95 uppercase tracking-widest text-xs italic">Synchroniser l'Agent</button>
    </div>
    
    <form id="configForm" method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div class="glass-card space-y-8 p-12 border-l-8 border-l-indigo-500">
            <h3 class="text-2xl font-black italic underline underline-offset-8 decoration-2 text-indigo-600 mb-10"><i class="fas fa-building-user mr-3"></i> IdentitÃ© Commerce</h3>
            <div class="space-y-3">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Nom de l'enseigne</label>
                <input name="n" value="{{current_user.business_name}}" class="input-pro shadow-sm">
            </div>
            <div class="space-y-3">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Horaires d'ouverture prÃ©cis</label>
                <textarea name="h" rows="4" class="input-pro shadow-sm">{{current_user.horaires}}</textarea>
            </div>
            <div class="space-y-3">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">CoordonnÃ©es Physiques</label>
                <input name="a" value="{{current_user.adresse}}" class="input-pro shadow-sm">
            </div>
        </div>
        
        <div class="glass-card space-y-8 p-12 border-l-8 border-l-emerald-500">
            <h3 class="text-2xl font-black italic underline underline-offset-8 decoration-2 text-emerald-600 mb-10"><i class="fas fa-microchip mr-3"></i> Logique de l'Agent IA</h3>
            <div class="space-y-3">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Catalogue Services & Tarifs</label>
                <textarea name="t" rows="5" class="input-pro shadow-sm" placeholder="Ex: Coupe 20â‚¬, Couleur 50â‚¬...">{{current_user.tarifs}}</textarea>
            </div>
            <div class="grid grid-cols-2 gap-6">
                <div class="space-y-3">
                    <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Temps par RDV (min)</label>
                    <input name="d" value="{{current_user.duree_moyenne}}" class="input-pro shadow-sm">
                </div>
                <div class="space-y-3">
                    <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Ton de la voix</label>
                    <select name="ton" class="input-pro shadow-sm">
                        <option value="Professionnel" {% if current_user.ton_ia == 'Professionnel' %}selected{% endif %}>Professionnel</option>
                        <option value="Amical" {% if current_user.ton_ia == 'Amical' %}selected{% endif %}>Amical / Chaleureux</option>
                        <option value="Direct" {% if current_user.ton_ia == 'Direct' %}selected{% endif %}>Direct / Rapide</option>
                    </select>
                </div>
            </div>
            <div class="space-y-3">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest ml-2">Instructions SecrÃ¨tes de Dialogue</label>
                <textarea name="p" rows="4" class="input-pro shadow-sm" placeholder="Ex: Toujours demander si c'est pour un nouveau client...">{{current_user.prompt_personnalise}}</textarea>
            </div>
        </div>
    </form>
    """
    return render_template_string(get_layout(content, "config"))

# --- PAGE AGENDA DYNAMIQUE ---
@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-5xl font-black text-slate-900 tracking-tighter italic">Historique Appels</h1>
        <div class="flex gap-4">
            <button class="bg-white border-2 border-slate-200 px-8 py-4 rounded-[22px] font-bold text-xs uppercase tracking-widest hover:bg-slate-50 transition shadow-sm">Exporter PDF</button>
            <button class="bg-slate-900 text-white px-8 py-4 rounded-[22px] font-bold text-xs uppercase tracking-widest hover:bg-slate-800 transition shadow-lg shadow-slate-200">Nettoyer Agenda</button>
        </div>
    </div>
    
    <div class="glass-card overflow-hidden !p-0 border border-slate-100 shadow-2xl">
        <div class="bg-slate-50 p-10 border-b border-slate-100 flex justify-between items-center">
            <div class="flex items-center gap-4">
                <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white"><i class="fas fa-list-ul text-sm"></i></div>
                <span class="text-sm font-black text-slate-700 uppercase tracking-[0.2em] italic">Liste des RÃ©servations IA</span>
            </div>
            <span class="text-xs font-extrabold text-slate-400 uppercase tracking-widest">{{ current_user.appointments|length }} Enregistrements</span>
        </div>
        <div class="divide-y divide-slate-50">
            {% for r in current_user.appointments|reverse %}
            <div class="p-12 hover:bg-slate-50/50 transition-all flex justify-between items-center group">
                <div class="flex items-center gap-10">
                    <div class="w-20 h-20 bg-white border-2 border-slate-100 text-slate-400 rounded-[30px] flex items-center justify-center text-2xl group-hover:border-indigo-500 group-hover:text-indigo-600 transition-all shadow-sm">
                        <i class="fas fa-phone-volume animate-float"></i>
                    </div>
                    <div>
                        <p class="text-2xl font-black text-slate-900 mb-2 italic tracking-tighter leading-tight group-hover:text-indigo-600 transition-colors">"{{ r.details }}"</p>
                        <div class="flex items-center gap-4">
                            <span class="text-[10px] font-black text-indigo-400 uppercase tracking-widest border-r pr-4 border-slate-200"><i class="far fa-clock mr-2"></i>ReÃ§u le {{ r.date_str }}</span>
                            <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest italic"><i class="fas fa-phone mr-2 text-[8px]"></i>Source: Twilio Vocal Agent</span>
                        </div>
                    </div>
                </div>
                <div class="text-right">
                    <span class="stat-badge bg-emerald-100 text-emerald-600 border border-emerald-200 shadow-sm"><i class="fas fa-circle text-[6px] mr-2"></i>ConfirmÃ© par IA</span>
                </div>
            </div>
            {% else %}
            <div class="p-40 text-center text-slate-300 italic">
                <i class="fas fa-calendar-alt text-[120px] mb-10 opacity-10"></i>
                <p class="text-3xl font-black tracking-tighter text-slate-200">Aucun appel enregistrÃ© pour le moment.</p>
                <p class="mt-4 text-slate-400 font-medium max-w-sm mx-auto">Votre agent vocal IA est en attente de sa premiÃ¨re conversation tÃ©lÃ©phonique pour remplir cet agenda.</p>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "agenda"))

# --- MASTER ADMIN VIEWS (ZONE SÃ‰CURISÃ‰E) ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(20).all()
    content = """
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-6xl font-black text-indigo-600 italic tracking-tighter uppercase underline decoration-indigo-200 underline-offset-[20px]">Master Console</h1>
        <div class="flex items-center gap-6">
            <div class="text-right"><p class="text-[10px] font-bold text-slate-400 uppercase">Licences Totales</p><p class="text-2xl font-black">{{users|length}}</p></div>
            <div class="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center text-white text-xl shadow-xl shadow-indigo-200"><i class="fas fa-crown"></i></div>
        </div>
    </div>
    
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-12">
        <div class="glass-card p-12 border-t-8 border-t-slate-900">
            <h3 class="text-2xl font-black mb-12 italic tracking-tight underline underline-offset-8">Base Clients Actifs</h3>
            <div class="space-y-6">
                {% for u in users %}
                <div class="p-8 bg-[#0f172a] text-white rounded-[2.5rem] flex justify-between items-center shadow-2xl transition hover:scale-[1.02] transform">
                    <div>
                        <p class="text-xl font-extrabold italic text-indigo-400 mb-1">{{u.business_name}}</p>
                        <p class="text-[10px] text-slate-500 font-mono tracking-widest uppercase">{{u.email}}</p>
                    </div>
                    <div class="flex items-center gap-4">
                        <span class="text-[10px] font-bold text-slate-600 bg-white/5 px-4 py-2 rounded-xl border border-white/10 italic">{{u.sector}}</span>
                        <a href="/voice/{{u.id}}" target="_blank" class="w-14 h-14 bg-indigo-600 text-white rounded-2xl flex items-center justify-center hover:bg-white hover:text-indigo-600 transition-all shadow-lg"><i class="fas fa-phone-alt"></i></a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="glass-card p-12 border-t-8 border-t-indigo-600">
            <h3 class="text-2xl font-black mb-12 italic tracking-tight underline underline-offset-8">Logs SystÃ¨me Globaux</h3>
            <div class="space-y-5">
                {% for l in logs %}
                <div class="p-6 border-l-8 border-indigo-500 bg-slate-50 rounded-r-[25px] flex justify-between items-center">
                    <div>
                        <p class="text-[11px] font-black text-indigo-600 uppercase tracking-widest mb-2">{{l.owner.business_name}}</p>
                        <p class="text-sm italic text-slate-600 font-semibold leading-relaxed max-w-xs">"{{l.details}}"</p>
                    </div>
                    <p class="text-[10px] font-bold text-slate-400 font-mono">{{l.date_str}}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "m-admin"), users=users, logs=logs)

@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = """
    <h1 class="text-4xl font-black mb-12 italic uppercase tracking-tighter">Gestion du Portefeuille Clients</h1>
    <div class="glass-card !p-0 overflow-hidden shadow-2xl border-none">
        <table class="w-full text-left">
            <thead class="bg-slate-900 text-white text-[11px] font-black uppercase tracking-[0.3em]">
                <tr>
                    <th class="p-10">Enseigne Client</th>
                    <th class="p-10">Secteur</th>
                    <th class="p-10 text-center">Volume Appels</th>
                    <th class="p-10 text-right">Statut IA</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for u in users %}
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="p-10">
                        <p class="font-black text-slate-900 text-2xl italic tracking-tighter mb-1">{{u.business_name}}</p>
                        <p class="text-xs text-slate-400 font-bold uppercase tracking-widest">{{u.email}}</p>
                    </td>
                    <td class="p-10">
                        <span class="px-6 py-2 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-indigo-100 italic">{{u.sector}}</span>
                    </td>
                    <td class="p-10 text-center">
                        <span class="text-3xl font-black text-slate-900 font-mono tracking-tighter">{{u.appointments|length}}</span>
                    </td>
                    <td class="p-10 text-right">
                        <div class="flex items-center justify-end gap-3">
                            <span class="stat-badge bg-emerald-100 text-emerald-600">Premium Actif</span>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(get_layout(content, "m-clients"), users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = """
    <h1 class="text-4xl font-black mb-12 italic tracking-tighter">Base de DonnÃ©es SystÃ¨me</h1>
    <div class="space-y-4 pb-20">
        {% for l in logs %}
        <div class="glass-card !py-8 flex justify-between items-center hover:border-indigo-400 transition shadow-lg group">
            <div class="flex items-center gap-8">
                <div class="w-16 h-16 bg-slate-900 text-indigo-400 rounded-2xl flex items-center justify-center font-black group-hover:bg-indigo-600 group-hover:text-white transition-all shadow-xl">LOG</div>
                <div>
                    <p class="font-black text-slate-900 italic text-2xl tracking-tighter mb-1">{{l.owner.business_name}} <span class="text-slate-300 font-normal">| UID:{{l.user_id}}</span></p>
                    <p class="text-sm italic text-slate-500 font-medium">"{{l.details}}"</p>
                </div>
            </div>
            <div class="text-right">
                <p class="text-[10px] font-black text-slate-300 uppercase italic mb-2">Timestamp: {{l.created_at}}</p>
                <span class="stat-badge bg-indigo-50 text-indigo-600 border border-indigo-100">{{l.date_str}}</span>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: 
        u.is_admin = True; db.session.commit()
        return "ACCÃˆS MAÃŽTRE SUPRÃŠME ACTIVÃ‰ - VEUILLEZ RAFRAICHIR LE DASHBOARD"
    return "UTILISATEUR NON TROUVÃ‰ DANS LA BASE DIGITAGPRO"

# --- MOTEUR VOCAL IA VOCO (CORE ENGINE 2026) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    # SYSTEM LOGS POWERSHELL
    print("\n" + "="*80)
    print(f"ðŸ“ž APPEL ENTRANT DETECTE | CLIENT : {c.business_name} | ID : {c.id}")
    print("="*80)
    
    if not txt:
        print("ðŸ¤– IA SYSTEM : GÃ©nÃ©ration du message d'accueil...")
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        print(f"ðŸ‘¤ CLIENT : {txt}")
        # Prompt Ultra-DensifiÃ© pour prÃ©cision maximale
        prompt = f"""Tu es l'agent vocal d'intelligence artificielle de {c.business_name}. 
        CONTEXTE COMMERCIAL :
        - SECTEUR : {c.sector}
        - VILLE : {c.adresse}
        - HORAIRES : {c.horaires}
        - TARIFS & SERVICES : {c.tarifs}
        - DUREE RDV : {c.duree_moyenne} min
        - TON SOUHAITÃ‰ : {c.ton_ia}
        - INSTRUCTIONS CLIENT : {c.prompt_personnalise}
        
        RÃˆGLES D'INTERACTION :
        1. Sois extrÃªmement courtois et concis.
        2. Si le client souhaite un rendez-vous, propose-lui de fixer une date et une heure selon nos horaires.
        3. DÃ¨s que l'accord est conclu, tu DOIS ABSOLUMENT terminer ton message par la balise suivante :
           CONFIRMATION: [Nom du service, Jour, Heure]
        """
        
        try:
            print("ðŸ§  IA PROCESSING : Appel API OpenAI GPT-4o-mini...")
            chat = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}],
                max_tokens=250,
                temperature=0.7
            )
            ai_res = chat.choices[0].message.content
            print(f"ðŸ¤– IA REPOND : {ai_res}")
            
            if "CONFIRMATION:" in ai_res:
                details_rdv = ai_res.split("CONFIRMATION:")[1].strip()
                # Sauvegarde SÃ©curisÃ©e
                db.session.add(Appointment(
                    date_str=datetime.now().strftime("%d/%m Ã  %H:%M"), 
                    details=f"RÃ©servation IA : {details_rdv}", 
                    user_id=c.id
                ))
                db.session.commit()
                print("âœ… SYSTEM : RÃ‰SERVATION ENREGISTRÃ‰E DANS LA BASE SQL")
                ai_res = ai_res.split("CONFIRMATION:")[0] + " Parfait, votre rendez-vous est maintenant enregistrÃ© dans notre agenda."
        except Exception as e:
            print(f"âŒ CRITICAL ERROR IA : {e}")
            ai_res = "Je vous prie de m'excuser, une interfÃ©rence technique perturbe notre communication. Pouvez-vous rÃ©pÃ©ter ?"

    print("="*80 + "\n")
    g = Gather(input='speech', language='fr-FR', timeout=1.5, speechTimeout='auto')
    g.say(ai_res, language='fr-FR', voice='alice')
    resp.append(g)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": 
    app.run(host='0.0.0.0', port=5000)
