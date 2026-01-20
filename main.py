from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_final_2026_ultra_dense'

# --- CONFIGURATION DATABASE (POSTGRES / SQLITE) ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): 
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÈLES DE DONNÉES ÉTENDUS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Configuration Commerce (SaaS Multi-niche)
    sector = db.Column(db.String(100), default="Services")
    horaires = db.Column(db.Text, default="Lundi-Vendredi: 9h-18h")
    tarifs = db.Column(db.Text, default="Service standard: 50€")
    duree_moyenne = db.Column(db.String(20), default="30")
    adresse = db.Column(db.String(255), default="Non renseignée")
    
    # Personnalisation de l'Agent IA
    prompt_personnalise = db.Column(db.Text, default="Sois accueillant, précis et professionnel.")
    voix_preferee = db.Column(db.String(20), default="fr-FR-Standard-A")
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), default="Client Anonyme")
    client_phone = db.Column(db.String(20))
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Confirmé")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# --- MOTEUR DE SYNCHRONISATION CRITIQUE ---
with app.app_context():
    # Suppression et recréation pour forcer la colonne 'client_name'
    db.drop_all() 
    db.create_all()
    print(">>> [DATABASE] RESET ET SYNCHRO TERMINEE. TOUTES LES COLONNES SONT OK.")

# --- ENGINE DE DESIGN (CSS FRAMEWORK) ---
CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
    .sidebar { background: #0f172a; border-right: 1px solid #1e293b; }
    .nav-link { color: #94a3b8; border-radius: 14px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); margin: 5px 0; }
    .nav-link:hover { background: #1e293b; color: #6366f1; transform: translateX(8px); }
    .active-nav { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white !important; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); }
    .glass-card { background: white; border-radius: 28px; border: 1px solid #e2e8f0; box-shadow: 0 4px 25px rgba(0,0,0,0.03); transition: 0.3s; }
    .glass-card:hover { transform: translateY(-5px); box-shadow: 0 12px 30px rgba(0,0,0,0.06); }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 15px; padding: 14px; transition: 0.2s; width: 100%; outline: none; }
    .input-pro:focus { border-color: #6366f1; background: white; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
    .badge { padding: 4px 12px; border-radius: 100px; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
    .badge-success { background: #dcfce7; color: #166534; }
    .badge-primary { background: #e0e7ff; color: #3730a3; }
</style>
"""

def get_layout(content, active_page="dashboard"):
    is_m = current_user.is_admin if current_user.is_authenticated else False
    sidebar = f"""
    <div class="fixed w-80 h-screen sidebar flex flex-col p-8 text-white z-50">
        <div class="flex items-center gap-4 mb-16 px-2">
            <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/50">
                <i class="fas fa-microchip text-xl"></i>
            </div>
            <span class="text-2xl font-black tracking-tighter uppercase italic">DigitagPro<span class="text-indigo-500">.</span></span>
        </div>
        <nav class="flex-1 space-y-1">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-6">Plateforme Client</p>
            <a href="/dashboard" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-th-large w-5"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-robot w-5"></i> Config IA</a>
            <a href="/mon-agenda" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-alt w-5"></i> Agenda</a>
            
            {f'''<div class="pt-10 mb-6 border-t border-slate-800/50"></div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest ml-4 mb-6">Master Control</p>
            <a href="/master-admin" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-admin' else ''} text-white hover:text-white"><i class="fas fa-crown w-5 text-indigo-400"></i> Console</a>
            <a href="/master-clients" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-clients' else ''} text-white hover:text-white"><i class="fas fa-users-cog w-5 text-indigo-400"></i> Clients</a>
            <a href="/master-logs" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-logs' else ''} text-white hover:text-white"><i class="fas fa-stream w-5 text-indigo-400"></i> Logs</a>''' if is_m else ''}
        </nav>
        <div class="pt-8 border-t border-slate-800">
            <a href="/logout" class="flex items-center gap-4 p-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition font-bold uppercase text-[11px] tracking-widest"><i class="fas fa-power-off"></i> Déconnexion</a>
        </div>
    </div>
    """
    return f"{CSS}<div class='flex'>{sidebar}<main class='ml-80 flex-1 p-12 min-h-screen bg-[#f8fafc]'>{content}</main></div>"

# --- AUTH SYSTEM ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
        flash("Identifiants incorrects")
    return render_template_string(CSS + """<body class="bg-[#0f172a] flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3.5rem] shadow-2xl w-[480px]"><div class="text-center mb-12"><h2 class="text-4xl font-extrabold text-slate-900 mb-2 italic tracking-tighter uppercase">DigitagPro</h2><p class="text-slate-400 font-medium uppercase tracking-[0.2em] text-[10px]">Session Enterprise IA</p></div><div class="space-y-6"><input name="email" type="email" placeholder="Email Professionnel" class="input-pro" required><input name="password" type="password" placeholder="Mot de passe" class="input-pro" required><button class="w-full bg-indigo-600 text-white p-5 rounded-[22px] font-black shadow-xl shadow-indigo-500/30 hover:bg-indigo-500 transition-all transform hover:-translate-y-1 uppercase tracking-widest">Se Connecter</button></div><p class="text-center mt-8 text-sm text-slate-400">Nouveau client ? <a href="/register" class="text-indigo-600 font-bold">Créer un compte</a></p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first(): return "Email déjà utilisé"
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(CSS + """<body class="bg-slate-100 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3.5rem] shadow-2xl w-[550px]"><h2 class="text-3xl font-black mb-10 text-slate-900 italic">Démarrer DigitagPro</h2><div class="space-y-4"><input name="b_name" placeholder="Nom du commerce" class="input-pro" required><input name="sector" placeholder="Secteur (ex: Garage, Coiffure)" class="input-pro" required><input name="email" type="email" placeholder="Email" class="input-pro" required><input name="password" type="password" placeholder="Mot de passe" class="input-pro" required><button class="w-full bg-slate-950 text-white p-5 rounded-[22px] font-black mt-6 shadow-2xl hover:bg-indigo-600 transition uppercase tracking-widest">Activer mon Agent IA</button></div></form></body>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- CORE DASHBOARD CLIENT ---
@app.route('/dashboard')
@login_required
def dashboard():
    last_rdv = current_user.appointments[-1].date_str if current_user.appointments else "En attente..."
    content = f"""
    <div class="flex justify-between items-center mb-16">
        <div><h1 class="text-5xl font-black text-slate-900 mb-2">Bonjour, {current_user.business_name}</h1><p class="text-slate-400 font-semibold uppercase tracking-widest text-xs">Tableau de bord de votre Agent Vocal</p></div>
        <div class="bg-white p-5 rounded-[24px] border border-slate-100 shadow-sm flex items-center gap-4"><div class="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div><span class="text-sm font-bold text-slate-700 uppercase tracking-widest">IA : En Ligne</span></div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        <div class="glass-card p-10"><div class="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-xl mb-6"><i class="fas fa-phone-alt"></i></div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Appels Gérés</p><p class="text-4xl font-black text-slate-900 mt-2">{{{{ current_user.appointments|length }}}}</p></div>
        <div class="glass-card p-10"><div class="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center text-xl mb-6"><i class="fas fa-calendar-check"></i></div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Dernière Réservation</p><p class="text-lg font-black text-slate-900 mt-2 truncate">{last_rdv}</p></div>
        <div class="glass-card p-10"><div class="w-14 h-14 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center text-xl mb-6"><i class="fas fa-briefcase"></i></div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Secteur</p><p class="text-lg font-black text-slate-900 mt-2 uppercase italic tracking-tighter">{{{{ current_user.sector }}}}</p></div>
    </div>
    <div class="glass-card bg-slate-950 text-white p-12 relative overflow-hidden border-none shadow-indigo-500/20 shadow-2xl">
        <div class="relative z-10">
            <h3 class="text-3xl font-bold mb-6 italic underline underline-offset-8 text-indigo-400">Intégration Twilio</h3>
            <p class="text-slate-400 mb-10 max-w-lg leading-relaxed font-medium">Pour activer votre IA sur votre numéro de téléphone, copiez l'URL ci-dessous dans la configuration "A Call Comes In" de Twilio :</p>
            <div class="bg-indigo-600/10 p-8 rounded-3xl border border-indigo-500/30 font-mono text-indigo-300 text-sm italic shadow-inner">
                https://digitagpro-ia.onrender.com/voice/{{{{ current_user.id }}}}
            </div>
        </div>
        <i class="fas fa-broadcast-tower text-[220px] absolute -right-12 -bottom-12 text-white/5 rotate-12"></i>
    </div>
    """
    return render_template_string(get_layout(content, "dashboard"))

@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.business_name = request.form.get('n'); current_user.horaires = request.form.get('h')
        current_user.tarifs = request.form.get('t'); current_user.adresse = request.form.get('a')
        current_user.duree_moyenne = request.form.get('d'); current_user.prompt_personnalise = request.form.get('p')
        db.session.commit(); flash("Configuration mise à jour avec succès !")
    content = """
    <div class="flex justify-between items-center mb-12">
        <h1 class="text-4xl font-black text-slate-900 italic">Configuration de l'IA</h1>
        <button onclick="document.getElementById('configForm').submit()" class="bg-indigo-600 text-white px-10 py-5 rounded-[22px] font-black shadow-lg shadow-indigo-200 hover:scale-[1.02] transition transform">SAUVEGARDER L'AGENT</button>
    </div>
    <form id="configForm" method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-10 pb-20">
        <div class="glass-card p-12 space-y-8">
            <h3 class="text-xl font-bold border-b pb-6 flex items-center gap-4 italic text-indigo-500"><i class="fas fa-store-alt"></i> Données Commerce</h3>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Nom d'Enseigne</label><input name="n" value="{{current_user.business_name}}" class="input-pro"></div>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Horaires d'ouverture</label><textarea name="h" rows="3" class="input-pro">{{current_user.horaires}}</textarea></div>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Adresse Physique</label><input name="a" value="{{current_user.adresse}}" class="input-pro"></div>
        </div>
        <div class="glass-card p-12 space-y-8">
            <h3 class="text-xl font-bold border-b pb-6 flex items-center gap-4 italic text-indigo-500"><i class="fas fa-brain"></i> Intelligence Artificielle</h3>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Services & Prix détaillés</label><textarea name="t" rows="4" class="input-pro">{{current_user.tarifs}}</textarea></div>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Durée RDV (minutes)</label><input name="d" value="{{current_user.duree_moyenne}}" class="input-pro"></div>
            <div class="space-y-2"><label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Prompt Comportemental</label><textarea name="p" rows="3" class="input-pro">{{current_user.prompt_personnalise}}</textarea></div>
        </div>
    </form>
    """
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """
    <h1 class="text-4xl font-black mb-12 italic tracking-tight">Agenda des Réservations</h1>
    <div class="glass-card overflow-hidden !p-0">
        <div class="bg-slate-50 p-8 border-b border-slate-100 flex justify-between items-center">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest italic">Aujourd'hui : {{ current_date }}</span>
            <div class="flex gap-4"><button class="px-6 py-2 bg-white rounded-xl text-[11px] font-bold border border-slate-200 hover:bg-slate-50 transition shadow-sm uppercase tracking-widest">Exporter CSV</button></div>
        </div>
        <div class="divide-y divide-slate-100">
            {% for r in current_user.appointments|reverse %}
            <div class="p-10 flex justify-between items-center hover:bg-slate-50 transition group">
                <div class="flex items-center gap-8">
                    <div class="w-16 h-16 bg-slate-100 text-slate-400 rounded-[22px] flex items-center justify-center text-xl group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors shadow-sm"><i class="fas fa-phone-volume"></i></div>
                    <div><p class="text-2xl font-black text-slate-900 italic tracking-tighter mb-1">"{{ r.details }}"</p><p class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Enregistré le {{ r.date_str }}</p></div>
                </div>
                <div class="badge badge-success">Confirmé par IA</div>
            </div>
            {% else %}<div class="p-32 text-center text-slate-300 italic text-2xl font-medium">L'IA attend son premier appel...</div>{% endfor %}
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "agenda"), current_date=datetime.now().strftime("%d %B %Y"))

# --- MASTER ADMIN ZONE ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(20).all()
    content = """
    <h1 class="text-5xl font-black mb-12 text-indigo-600 italic uppercase">Master Console</h1>
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-12">
        <div class="glass-card p-10">
            <h3 class="text-xl font-extrabold mb-10 italic border-b pb-4">Clients Actifs ({{users|length}})</h3>
            <div class="space-y-5">
                {% for u in users %}
                <div class="p-6 bg-slate-950 text-white rounded-[2rem] flex justify-between items-center shadow-2xl">
                    <div><p class="font-bold text-lg italic">{{u.business_name}}</p><p class="text-[10px] text-slate-500 font-mono">{{u.email}}</p></div>
                    <a href="/voice/{{u.id}}" target="_blank" class="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center hover:bg-white hover:text-indigo-600 transition-all shadow-lg"><i class="fas fa-phone"></i></a>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="glass-card p-10">
            <h3 class="text-xl font-extrabold mb-10 italic border-b pb-4">Flux Global (Temps Réel)</h3>
            <div class="space-y-4">
                {% for l in logs %}
                <div class="p-5 border-l-4 border-indigo-500 bg-slate-50 rounded-r-2xl"><p class="text-[10px] font-bold text-indigo-400 uppercase mb-2">{{l.owner.business_name}}</p><p class="text-xs italic text-slate-600 font-medium leading-relaxed">"{{l.details}}"</p></div>
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
    <h1 class="text-4xl font-black mb-12 italic uppercase">Gestion Clients</h1>
    <div class="glass-card overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead class="bg-indigo-600 text-white text-[11px] font-bold uppercase tracking-[0.2em]">
                <tr><th class="p-8">Enseigne</th><th class="p-8 text-center">Appels Gérés</th><th class="p-8 text-right">Actions</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for u in users %}
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="p-8"><p class="font-black text-slate-900 text-2xl italic tracking-tighter">{{u.business_name}}</p><p class="text-xs text-slate-400 font-medium">{{u.email}}</p></td>
                    <td class="p-8 text-center"><span class="badge badge-primary text-xl px-5 py-2 font-black italic">{{u.appointments|length}}</span></td>
                    <td class="p-8 text-right"><a href="/voice/{{u.id}}" class="text-indigo-600 font-bold hover:underline italic">Accès Voice</a></td>
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
    content = """<h1 class="text-4xl font-black mb-12 italic tracking-tighter">Database Full Logs</h1><div class="space-y-4">{% for l in logs %}<div class="glass-card p-6 flex justify-between items-center"><div class="flex items-center gap-6"><div class="w-14 h-14 bg-slate-900 text-indigo-400 rounded-2xl flex items-center justify-center font-black">LOG</div><div><p class="font-bold text-slate-900 italic text-xl">{{l.owner.business_name}}</p><p class="text-sm italic text-slate-500">"{{l.details}}"</p></div></div><p class="text-[10px] font-bold text-slate-400 italic">{{l.date_str}}</p></div>{% endfor %}</div>"""
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "ACCES MAITRE VALIDE"
    return "NOT FOUND"

# --- CORE VOICE ENGINE IA ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    # LOGS POUR POWERSHELL
    print("\n" + "="*60)
    print(f"📞 APPEL ENTRANT : {c.business_name}")
    
    if not txt:
        print("🤖 IA : Accueil Vocal")
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        print(f"👤 CLIENT : {txt}")
        prompt = f"""Tu es l'agent vocal de {c.business_name}. 
        Secteur: {c.sector} | Ville: {c.adresse} | Horaires: {c.horaires}
        Tarifs/Services: {c.tarifs} | Durée: {c.duree_moyenne}min
        Instructions: {c.prompt_personnalise}
        
        Si le client veut un rendez-vous, demande la date et l'heure précises. 
        Dès que c'est fixé, termine par : 'CONFIRMATION: [Détail, Date, Heure]'."""
        
        try:
            chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
            ai_res = chat.choices[0].message.content
            print(f"🤖 IA REPOND : {ai_res}")
            
            if "CONFIRMATION:" in ai_res:
                details_clean = ai_res.split("CONFIRMATION:")[1].strip()
                new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m à %H:%M"), details=details_clean, user_id=c.id)
                db.session.add(new_rdv); db.session.commit()
                print("✅ RÉSERVATION ENREGISTRÉE DANS L'AGENDA")
                ai_res = ai_res.split("CONFIRMATION:")[0] + " C'est parfait, c'est noté pour vous."
        except Exception as e:
            print(f"❌ ERREUR OPENAI : {e}")
            ai_res = "Désolé, j'ai une petite difficulté technique, pouvez-vous répéter ?"

    print("="*60 + "\n")
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_res, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)