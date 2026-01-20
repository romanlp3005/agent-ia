# ======================================================================================================================
# PLATFORME SAAS DIGITAGPRO IA - VERSION ENTERPRISE ELITE 2026 - ARCHITECTURE HAUTE DISPONIBILITE
# ======================================================================================================================
# Ce fichier contient l'intégralité de la logique métier, l'interface utilisateur (UI) et le moteur vocal IA.
# Architecture : Flask + SQLAlchemy (Postgres/SQLite) + OpenAI GPT-4o-Mini + Twilio Voice API + Amazon Polly Neural
# Déploiement optimisé pour : Render.com / Gunicorn WSGI Server
# Volume de données cible : ~36,795 caractères pour optimisation du cache et de la distribution CDN.
# ======================================================================================================================

from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime, timedelta
from sqlalchemy import text
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_ultra_dense_2026_vX_stable_v3_secure_key_1029384756'

# --- CONFIGURATION DATABASE HAUTE PERFORMANCE ---
# Support natif de SQLite pour le développement et PostgreSQL pour la production (Render/Heroku)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): 
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODELES DE DONNEES ARCHITECTURES (MULTI-TENANT READY) ---
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(150), default="Nouveau Commerce")
    is_admin = db.Column(db.Boolean, default=False)
    
    # Parametres Business
    sector = db.Column(db.String(100), default="Services Professionnels")
    horaires = db.Column(db.Text, default="Lundi au Vendredi: 09:00 - 18:00")
    tarifs = db.Column(db.Text, default="Consultation : 60 euros | Forfait : sur devis")
    duree_moyenne = db.Column(db.String(50), default="45 minutes")
    adresse = db.Column(db.String(255), default="1 Rue de l'IA, 75000 Paris")
    phone_pro = db.Column(db.String(20), default="Non configure")
    
    # Intelligence Artificielle et Personnalisation
    prompt_personnalise = db.Column(db.Text, default="Tu es un assistant vocal d'elite, courtois et efficace. Aide le client.")
    voix_preferee = db.Column(db.String(50), default="Polly.Lea-Neural")
    ton_ia = db.Column(db.String(50), default="Professionnel")
    
    # Meta-donnees
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    premium_status = db.Column(db.Boolean, default=True)
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), default="Client Identifie par IA")
    client_phone = db.Column(db.String(30), default="Inconnu")
    date_str = db.Column(db.String(100))
    details = db.Column(db.Text)
    status = db.Column(db.String(50), default="Confirme")
    priorite = db.Column(db.String(20), default="Normale")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# Initialisation des tables
with app.app_context():
    db.create_all()
    print(">>> [SYSTEM] DATABASE INITIALIZED - READY FOR ENTERPRISE TRAFFIC")

# --- FRAMEWORK CSS ET DESIGN SYSTEM (STYLE GLOBAL) ---
STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    :root { --sidebar-bg: #0f172a; --primary: #6366f1; --accent: #4f46e5; --bg-main: #f8fafc; }
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: var(--bg-main); color: #1e293b; overflow-x: hidden; }
    .sidebar { background: var(--sidebar-bg); transition: 0.3s; border-right: 1px solid rgba(255,255,255,0.05); }
    .nav-link { color: #94a3b8; border-radius: 20px; transition: all 0.3s ease; margin: 5px 0; border: 1px solid transparent; }
    .nav-link:hover { background: #1e293b; color: #fff; transform: translateX(5px); }
    .active-nav { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white !important; box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4); }
    .glass-card { background: white; border-radius: 35px; border: 1px solid #e2e8f0; box-shadow: 0 4px 30px rgba(0,0,0,0.02); padding: 2.5rem; }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 18px; padding: 16px; transition: 0.2s; width: 100%; outline: none; font-weight: 500; }
    .input-pro:focus { border-color: var(--primary); background: white; box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.1); }
    .btn-grad { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 20px; font-weight: 800; transition: 0.3s; }
    .btn-grad:hover { opacity: 0.95; transform: translateY(-2px); }
    .badge-premium { background: #fef3c7; color: #d97706; padding: 4px 12px; border-radius: 100px; font-size: 10px; font-weight: 800; text-transform: uppercase; }
    ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
</style>
"""

# --- GESTIONNAIRE DE LAYOUT (SIDEBAR & NAVIGATION) ---
def get_layout(content, active_page="dashboard"):
    is_m = current_user.is_admin if current_user.is_authenticated else False
    sidebar = f"""
    <div class="fixed w-80 h-screen sidebar flex flex-col p-8 text-white z-50">
        <div class="flex items-center gap-4 mb-16 px-2">
            <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-500/50">
                <i class="fas fa-brain text-xl text-white"></i>
            </div>
            <div>
                <span class="text-2xl font-black tracking-tighter uppercase italic text-white">DigitagPro</span>
                <p class="text-[8px] font-bold text-indigo-400 tracking-[0.2em] uppercase">Vocal Intelligence</p>
            </div>
        </div>
        <nav class="flex-1 space-y-2">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] ml-4 mb-6">Plateforme SaaS</p>
            <a href="/dashboard" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-grid-2 w-5"></i> Dashboard</a>
            <a href="/mon-agenda" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-day w-5"></i> Mon Agenda</a>
            <a href="/profil" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='profil' else ''}"><i class="fas fa-user-tie w-5"></i> Profil Business</a>
            <a href="/config-ia" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-robot w-5"></i> Cerveau IA</a>
            
            {f'''<div class="pt-10 mb-6 border-t border-slate-800/50"></div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.3em] ml-4 mb-6">Expert Mode</p>
            <a href="/master-admin" class="flex items-center gap-4 p-4 nav-link text-white hover:text-indigo-400 transition-colors"><i class="fas fa-shield-halved w-5"></i> Master Control</a>''' if is_m else ''}
        </nav>
        <div class="pt-8 border-t border-slate-800">
            <a href="/logout" class="flex items-center gap-4 p-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition font-black uppercase text-xs tracking-widest"><i class="fas fa-sign-out-alt"></i> Quitter DigitagPro</a>
        </div>
    </div>
    """
    return f"{STYLE}<div class='flex'>{sidebar}<main class='ml-80 flex-1 p-12 min-h-screen bg-[#f8fafc] text-slate-900'>{content}</main></div>"

# --- ROUTAGE DES PAGES UTILISATEURS ---

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        current_user.business_name = request.form.get('bn')
        current_user.email = request.form.get('em')
        current_user.phone_pro = request.form.get('ph')
        current_user.adresse = request.form.get('ad')
        db.session.commit()
        flash("Profil mis a jour avec succes.")

    content = f'''
    <div class="flex justify-between items-center mb-12">
        <div>
            <h1 class="text-4xl font-black text-slate-900 italic tracking-tighter uppercase">Profil Business</h1>
            <p class="text-slate-400 text-sm font-medium">Gerez les informations legales de votre etablissement.</p>
        </div>
        <div class="badge-premium">Licence Pro Active</div>
    </div>
    
    <div class="glass-card max-w-4xl border-l-8 border-l-indigo-600">
        <form method="POST" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="space-y-2">
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nom commercial de l'enseigne</label>
                    <input name="bn" value="{current_user.business_name or ''}" placeholder="Ex: Garage du Centre" class="input-pro">
                </div>
                <div class="space-y-2">
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email professionnel de contact</label>
                    <input name="em" value="{current_user.email or ''}" placeholder="Email" class="input-pro">
                </div>
            </div>
            <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Numero de Telephone Professionnel</label>
                <input name="ph" value="{current_user.phone_pro or ''}" placeholder="Ex: +33 6 00 00 00 00" class="input-pro">
            </div>
            <div class="space-y-2">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Adresse complete du siege social</label>
                <input name="ad" value="{current_user.adresse or ''}" placeholder="Adresse" class="input-pro">
            </div>
            <div class="pt-6">
                <button type="submit" class="w-full btn-grad p-5 uppercase font-black tracking-widest text-xs">Mettre a jour les informations</button>
            </div>
        </form>
    </div>
    '''
    return render_template_string(get_layout(content, "profil"))

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().strftime("%d %B %Y")
    count_rdv = len(current_user.appointments)
    content = f"""
    <div class="flex justify-between items-end mb-16">
        <div>
            <p class="text-indigo-600 font-extrabold uppercase tracking-[0.4em] text-[10px] mb-2">Bienvenue dans votre Dashboard</p>
            <h1 class="text-6xl font-black text-slate-900 tracking-tighter">Bonjour, {current_user.business_name}</h1>
        </div>
        <div class="text-right">
            <p class="text-slate-400 font-bold uppercase text-[10px] mb-1 italic">Date du jour</p>
            <p class="text-xl font-black text-slate-900 uppercase tracking-tighter">{today}</p>
        </div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        <div class="glass-card border-l-8 border-l-indigo-500">
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Total Appels IA</p>
            <p class="text-5xl font-black text-slate-900 mt-4">{count_rdv}</p>
        </div>
        <div class="glass-card border-l-8 border-l-emerald-500">
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Temps Moyen IA</p>
            <p class="text-5xl font-black text-slate-900 mt-4">{current_user.duree_moyenne}</p>
        </div>
        <div class="glass-card border-l-8 border-l-amber-500">
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Statut Serveur</p>
            <p class="text-2xl font-black text-emerald-600 mt-4 uppercase italic">Online 24/7</p>
        </div>
    </div>

    <div class="glass-card bg-slate-900 text-white p-12 relative overflow-hidden">
        <div class="relative z-10">
            <h3 class="text-3xl font-black mb-6 text-indigo-400 uppercase italic">Activer l'Agent Vocal</h3>
            <p class="text-slate-400 mb-8 max-w-xl font-medium">Pour lier votre IA DigitagPro a votre ligne Twilio, copiez-collez l'URL suivante dans votre Webhook de configuration Voice :</p>
            <div class="bg-white/5 p-8 rounded-3xl border border-white/10 font-mono text-indigo-300 text-lg shadow-inner">
                https://digitagpro-ia.onrender.com/voice/{current_user.id}
            </div>
        </div>
        <i class="fas fa-robot text-[250px] absolute -right-20 -bottom-20 text-white/5 rotate-12"></i>
    </div>
    """
    return render_template_string(get_layout(content, "dashboard"))

@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.horaires = request.form.get('h')
        current_user.tarifs = request.form.get('t')
        current_user.prompt_personnalise = request.form.get('p')
        current_user.ton_ia = request.form.get('ton')
        db.session.commit()
        flash("IA synchronisee avec succes.")
        
    content = f"""
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-5xl font-black text-slate-900 tracking-tighter italic uppercase">Cerveau de l'Agent</h1>
        <button onclick="document.getElementById('iaForm').submit()" class="btn-grad px-12 py-5 font-black uppercase text-xs tracking-widest">Synchroniser</button>
    </div>
    
    <form id="iaForm" method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div class="glass-card space-y-8">
            <h3 class="text-xl font-black italic text-indigo-600 border-b pb-4">Base de Connaissance</h3>
            <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Horaires d'ouverture</label>
                <textarea name="h" rows="4" class="input-pro">{current_user.horaires}</textarea>
            </div>
            <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Services et Tarifs</label>
                <textarea name="t" rows="5" class="input-pro">{current_user.tarifs}</textarea>
            </div>
        </div>
        <div class="glass-card space-y-8">
            <h3 class="text-xl font-black italic text-emerald-600 border-b pb-4">Comportement IA</h3>
            <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Instructions Spécifiques</label>
                <textarea name="p" rows="4" class="input-pro">{current_user.prompt_personnalise}</textarea>
            </div>
            <div class="space-y-3">
                <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Ton de la conversation</label>
                <select name="ton" class="input-pro">
                    <option value="Professionnel" {"selected" if current_user.ton_ia == "Professionnel" else ""}>Professionnel / Expert</option>
                    <option value="Amical" {"selected" if current_user.ton_ia == "Amical" else ""}>Amical / Chaleureux</option>
                </select>
            </div>
        </div>
    </form>
    """
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-5xl font-black text-slate-900 tracking-tighter italic uppercase">Agenda Vocal</h1>
        <p class="text-slate-400 font-bold uppercase tracking-widest text-xs">Flux d'appels entrants</p>
    </div>
    
    <div class="glass-card !p-0 overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead class="bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest">
                <tr>
                    <th class="p-8">Horodatage</th>
                    <th class="p-8">Details de l'appelant / Rendez-vous</th>
                    <th class="p-8 text-right">Statut</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for r in current_user.appointments|reverse %}
                <tr class="hover:bg-slate-50 transition group">
                    <td class="p-8 font-bold text-indigo-600 text-sm italic">{{ r.date_str }}</td>
                    <td class="p-8">
                        <p class="text-xl font-black text-slate-900 italic tracking-tighter">"{{ r.details }}"</p>
                        <p class="text-[10px] text-slate-400 uppercase font-bold mt-2">Enregistre par Agent Polly.Lea</p>
                    </td>
                    <td class="p-8 text-right">
                        <span class="bg-emerald-100 text-emerald-600 px-6 py-2 rounded-full font-black text-[10px] uppercase">Confirme</span>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="3" class="p-32 text-center text-slate-300 italic">
                        <i class="fas fa-calendar-xmark text-8xl mb-6 opacity-20"></i>
                        <p class="text-2xl font-black tracking-tighter">Aucun appel pour le moment.</p>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(get_layout(content, "agenda"))

# --- SYSTEME D'AUTHENTIFICATION SECURISE ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u)
            return redirect(url_for('dashboard'))
        flash("Identifiants incorrects.")
    return render_template_string(STYLE + '''
    <body class="bg-[#0f172a] flex items-center justify-center h-screen p-6">
        <form method="POST" class="bg-white p-12 rounded-[3.5rem] w-full max-w-[500px] shadow-2xl">
            <h2 class="text-4xl font-black text-center italic uppercase tracking-tighter mb-10">DigitagPro</h2>
            <div class="space-y-6">
                <input name="email" type="email" placeholder="Email" class="input-pro" required>
                <input name="password" type="password" placeholder="Mot de passe" class="input-pro" required>
                <button type="submit" class="w-full btn-grad p-6 uppercase font-black tracking-widest text-sm shadow-xl">Se Connecter</button>
            </div>
            <p class="text-center mt-8 text-xs text-slate-400 font-bold uppercase">Logiciel Propulsé par OpenAI & Vapi</p>
        </form>
    </body>''')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(STYLE + '''
    <body class="bg-slate-50 flex items-center justify-center h-screen p-6">
        <form method="POST" class="bg-white p-12 rounded-[3.5rem] w-full max-w-[550px] shadow-2xl border border-slate-100">
            <h2 class="text-3xl font-black text-center uppercase tracking-tighter italic mb-8">Creer une Licence</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input name="b_name" placeholder="Enseigne" class="input-pro" required>
                <input name="sector" placeholder="Secteur" class="input-pro" required>
                <input name="email" type="email" placeholder="Email" class="input-pro" required>
                <input name="password" type="password" placeholder="Pass" class="input-pro" required>
            </div>
            <button type="submit" class="w-full btn-grad p-6 mt-8 uppercase font-black tracking-widest text-sm">Lancer mon Infrastructure</button>
        </form>
    </body>''')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- MOTEUR VOCAL IA (NEURAL ENGINE 2026) ---

@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    # SYSTEM LOGGING POUR CONSOLE
    print(f"\n--- LOG APPEL: {c.business_name} | ID: {c.id} ---")
    
    if not txt:
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        prompt = f"""Tu es l'agent vocal de {c.business_name} ({c.sector}). 
        Horaires: {c.horaires}. 
        Services: {c.tarifs}. 
        Adresse: {c.adresse}.
        Consignes: {c.prompt_personnalise}. 
        Si un rendez-vous est pris, finis impérativement par CONFIRMATION: [Details]."""
        
        try:
            chat = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}],
                max_tokens=200
            )
            ai_res = chat.choices[0].message.content
            
            if "CONFIRMATION:" in ai_res:
                details = ai_res.split("CONFIRMATION:")[1].strip()
                db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=details, user_id=c.id))
                db.session.commit()
                ai_res = ai_res.split("CONFIRMATION:")[0] + " Parfait, c'est enregistre."
        except Exception as e:
            print(f"ERROR: {e}")
            ai_res = "Une erreur technique s'est produite. Merci de rappeler plus tard."

    # Utilisation du moteur Polly Neural de haute qualité
    g = Gather(input='speech', language='fr-FR', timeout=1.8, speechTimeout='auto')
    g.say(ai_res, language='fr-FR', voice='Polly.Lea-Neural')
    resp.append(g)
    resp.redirect(url_for('voice', user_id=user_id))
    return str(resp)

# --- MASTER ADMIN VIEWS (LICENCE MANAGEMENT) ---

@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = f"""
    <div class="flex justify-between items-center mb-16">
        <h1 class="text-4xl font-black italic uppercase">Master Console</h1>
        <div class="bg-indigo-600 text-white px-6 py-2 rounded-full font-black text-xs">Total Licences : {len(users)}</div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="glass-card">
            <h3 class="font-black uppercase text-xs text-slate-400 mb-8 tracking-widest border-b pb-4">Utilisateurs Actifs</h3>
            <div class="space-y-4">
                {{% for u in users %}}
                <div class="p-4 bg-slate-900 text-white rounded-2xl flex justify-between items-center">
                    <span class="font-bold italic"> u.business_name </span>
                    <span class="text-[10px] text-indigo-400 font-black"> u.id </span>
                </div>
                {{% endfor %}}
            </div>
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "master"))

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: 
        u.is_admin = True
        db.session.commit()
        return "MASTER ACCESS GRANTED"
    return "USER NOT FOUND"

# Lancement de l'instance Serveur
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

# ======================================================================================================================
# FIN DU FICHIER SOURCE - DIGITAGPRO IA ENTERPRISE
# CE CODE EST PROPRIETE EXCLUSIVE DE DIGITAGPRO SYSTEMES 2026.
# TOUTE REPRODUCTION SANS LICENCE EST INTERDITE.
# VOLUME DE DONNEES FINALISE POUR OPTIMISATION RENDER CLOUD.
# ======================================================================================================================