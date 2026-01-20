from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_final_2026'

# --- DATABASE ENGINE ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODELS STRUCTURED FOR ANY BUSINESS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Configuration Business
    sector = db.Column(db.String(100), default="Services")
    horaires = db.Column(db.Text, default="Lundi-Vendredi: 9h-18h")
    tarifs = db.Column(db.Text, default="Coupe: 25€, Barbe: 15€")
    duree_moyenne = db.Column(db.String(20), default="30") # En minutes
    adresse = db.Column(db.String(255), default="123 Rue de la Paix, Paris")
    
    # Configuration IA
    prompt_personnalise = db.Column(db.Text, default="Sois accueillant et professionnel.")
    voix_preferee = db.Column(db.String(20), default="Alice")
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_phone = db.Column(db.String(20))
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Confirmé")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# --- DATABASE MIGRATION SYSTEM ---
with app.app_context():
    # ATTENTION : Cette ligne va vider ta base pour la reconstruire au propre
    # Utilise-la une seule fois pour débloquer la situation
    db.drop_all() 
    db.create_all()
    print("Base de données réinitialisée avec succès !")
# --- DESIGN ENGINE ---
CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f1f5f9; }
    .sidebar { background: #0f172a; transition: all 0.3s ease; }
    .nav-link { color: #94a3b8; border-radius: 12px; transition: 0.2s; }
    .nav-link:hover { background: #1e293b; color: white; }
    .active-nav { background: #4f46e5; color: white !important; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); }
    .glass-card { background: white; border-radius: 24px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .stat-card { border-left: 4px solid #4f46e5; }
</style>
"""

def get_layout(content, active_page="dashboard"):
    user_type = "MASTER ADMIN" if current_user.is_admin else current_user.business_name
    sidebar = f"""
    <div class="fixed w-72 h-screen sidebar flex flex-col p-6 text-white z-50">
        <div class="flex items-center gap-3 mb-12 px-2">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-black">D</div>
            <span class="text-xl font-extrabold tracking-tighter">DIGITAGPRO<span class="text-indigo-500">.</span></span>
        </div>
        <nav class="flex-1 space-y-2">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-4">Menu Principal</p>
            <a href="/dashboard" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-th-large"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-robot"></i> Configuration IA</a>
            <a href="/mon-agenda" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-check"></i> Agenda</a>
            
            <div class="my-8 border-t border-slate-800 opacity-50"></div>
            
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-4">Expert Mode</p>
            {f'''<a href="/master-admin" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-admin' else ''} text-indigo-400"><i class="fas fa-crown"></i> Master Console</a>
            <a href="/master-clients" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-clients' else ''} text-indigo-400"><i class="fas fa-users-gear"></i> Gérer Clients</a>
            <a href="/master-logs" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-logs' else ''} text-indigo-400"><i class="fas fa-database"></i> Tous les Logs</a>''' if current_user.is_admin else ''}
        </nav>
        <div class="pt-6 border-t border-slate-800 mt-auto">
            <div class="p-4 bg-slate-800 rounded-2xl mb-4">
                <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Connecté en tant que</p>
                <p class="text-sm font-bold truncate">{user_type}</p>
            </div>
            <a href="/logout" class="flex items-center gap-3 p-4 text-red-400 hover:bg-red-500/10 rounded-xl transition font-bold"><i class="fas fa-power-off"></i> Déconnexion</a>
        </div>
    </div>
    """
    return f"{CSS}<div class='flex'>{sidebar}<main class='ml-72 flex-1 p-10 min-h-screen'>{content}</main></div>"

# --- AUTH ROUTES ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
        flash("Email ou mot de passe incorrect.")
    return render_template_string(CSS + """<body class="bg-slate-900 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-2xl w-[420px]"><h2 class="text-3xl font-black mb-2 text-slate-900 italic uppercase">DigitagPro</h2><p class="text-slate-400 text-sm mb-10 font-medium tracking-tight">Accédez à votre plateforme IA</p><div class="space-y-4"><input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:border-indigo-500 transition"><input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl outline-none focus:border-indigo-500 transition"><button class="w-full bg-slate-900 text-white p-5 rounded-2xl font-black shadow-lg hover:bg-indigo-600 transition">OUVRIR LA SESSION</button></div><p class="text-center mt-6 text-xs text-slate-400">© 2026 DigitagPro Enterprise Edition</p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first(): return "Email déjà utilisé"
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(CSS + """<body class="bg-slate-50 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-xl w-[480px] border border-slate-200"><h2 class="text-3xl font-black mb-8">Inscription</h2><div class="space-y-4"><input name="b_name" placeholder="Nom du commerce" class="w-full p-4 bg-slate-100 rounded-2xl outline-none"><input name="sector" placeholder="Secteur (ex: Garage, Coiffure)" class="w-full p-4 bg-slate-100 rounded-2xl outline-none"><input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-100 rounded-2xl outline-none"><input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-100 rounded-2xl outline-none"><button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black mt-4">DEMARRER MON IA</button></div></form></body>""")

# --- CLIENT LOGIC ---
@app.route('/dashboard')
@login_required
def dashboard():
    stats = {"rdv_count": len(current_user.appointments), "last_call": "Aucun"}
    if current_user.appointments: stats["last_call"] = current_user.appointments[-1].date_str
    content = f"""<div class="flex justify-between items-center mb-10"><div><h1 class="text-4xl font-black">Dashboard</h1><p class="text-slate-400">Statistiques de votre agent vocal</p></div><div class="bg-indigo-600 text-white px-6 py-2 rounded-full font-bold text-sm">IA Statut : En Ligne</div></div><div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10"><div class="glass-card p-8 stat-card"><div><p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Appels transformés</p><p class="text-3xl font-black mt-2">{{{{ current_user.appointments|length }}}}</p></div></div><div class="glass-card p-8 border-l-4 border-emerald-500"><div><p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Dernière activité</p><p class="text-lg font-bold mt-2 text-emerald-600">{stats['last_call']}</p></div></div><div class="glass-card p-8 border-l-4 border-amber-500"><div><p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Secteur</p><p class="text-lg font-bold mt-2 text-amber-600">{{{{ current_user.sector }}}}</p></div></div></div><div class="glass-card p-10"><h3 class="text-xl font-bold mb-8 italic text-slate-400">Guide de démarrage rapide</h3><div class="grid grid-cols-1 md:grid-cols-2 gap-10"><div class="p-6 bg-slate-50 rounded-3xl"><p class="font-bold text-indigo-600 mb-2 underline">Étape 1 : Configurez l'IA</p><p class="text-sm text-slate-500 leading-relaxed">Allez dans "Configuration IA" pour entrer vos tarifs, vos horaires et l'adresse de votre établissement.</p></div><div class="p-6 bg-slate-50 rounded-3xl"><p class="font-bold text-indigo-600 mb-2 underline">Étape 2 : Connectez Twilio</p><p class="text-sm text-slate-500 leading-relaxed">Donnez ce lien à votre administrateur pour lier votre numéro Twilio :<br><span class="text-[10px] font-mono bg-slate-200 p-1 rounded">/voice/{{{{ current_user.id }}}}</span></p></div></div></div>"""
    return render_template_string(get_layout(content, "dashboard"))

@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.business_name = request.form.get('n'); current_user.horaires = request.form.get('h')
        current_user.tarifs = request.form.get('t'); current_user.adresse = request.form.get('a')
        current_user.duree_moyenne = request.form.get('d'); current_user.prompt_personnalise = request.form.get('p')
        db.session.commit(); flash("Configuration enregistrée avec succès.")
    content = """<h1 class="text-3xl font-black mb-8">Paramètres Experts de l'Agent IA</h1><form method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-8"><div class="glass-card p-8 space-y-6"><h3 class="font-bold text-indigo-600 uppercase text-xs tracking-widest italic border-b pb-4">Données Métier</h3><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Nom de l'enseigne</label><input name="n" value="{{current_user.business_name}}" class="w-full p-4 bg-slate-50 rounded-2xl outline-none focus:bg-white border focus:border-indigo-500"></div><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Horaires détaillés</label><textarea name="h" rows="3" class="w-full p-4 bg-slate-50 rounded-2xl outline-none focus:bg-white border focus:border-indigo-500">{{current_user.horaires}}</textarea></div><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Services & Prix (Précisez tout)</label><textarea name="t" rows="6" class="w-full p-4 bg-slate-50 rounded-2xl outline-none focus:bg-white border focus:border-indigo-500">{{current_user.tarifs}}</textarea></div></div><div class="glass-card p-8 space-y-6"><h3 class="font-bold text-indigo-600 uppercase text-xs tracking-widest italic border-b pb-4">Logique d'Appel</h3><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Adresse Physique</label><input name="a" value="{{current_user.adresse}}" class="w-full p-4 bg-slate-50 rounded-2xl border outline-none"></div><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Durée de Prestation (minutes)</label><input name="d" value="{{current_user.duree_moyenne}}" class="w-full p-4 bg-slate-50 rounded-2xl border outline-none"></div><div><label class="text-xs font-bold text-slate-500 mb-2 block uppercase">Instructions Comportement IA</label><textarea name="p" rows="4" class="w-full p-4 bg-slate-50 rounded-2xl border outline-none focus:border-indigo-500">{{current_user.prompt_personnalise}}</textarea></div><button class="w-full bg-slate-900 text-white p-5 rounded-2xl font-black hover:bg-indigo-600 transition shadow-xl">METTRE À JOUR MON AGENT</button></div></form>"""
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """<h1 class="text-3xl font-black mb-8 italic uppercase">Agenda des Réservations</h1><div class="glass-card p-8"><div class="flex items-center justify-between mb-10"><p class="text-slate-400 font-bold uppercase tracking-widest text-xs">Aujourd'hui : {{ current_date }}</p><div class="flex gap-2"><button class="px-4 py-2 bg-slate-100 rounded-lg text-xs font-bold hover:bg-slate-200 transition">Exporter CSV</button></div></div><div class="space-y-4">{% for r in current_user.appointments|reverse %}<div class="p-6 bg-white border border-slate-100 rounded-3xl flex justify-between items-center shadow-sm hover:shadow-md transition"><div class="flex items-center gap-6"><div class="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center font-black text-xl"><i class="fas fa-phone-volume"></i></div><div><p class="font-black text-slate-900">{{ r.details }}</p><p class="text-xs font-bold text-indigo-400 uppercase tracking-widest">Le {{ r.date_str }}</p></div></div><div class="text-right"><span class="px-4 py-2 bg-emerald-100 text-emerald-600 rounded-full font-bold text-[10px] uppercase">RDV Confirmé par IA</span></div></div>{% else %}<div class="text-center py-24 text-slate-300"><i class="far fa-calendar-times text-6xl mb-4 opacity-20"></i><p class="italic">Votre agenda est vide, l'IA attend son premier appel.</p></div>{% endfor %}</div></div>"""
    return render_template_string(get_layout(content, "agenda"), current_date=datetime.now().strftime("%A %d %B %Y"))

# --- MASTER ROUTES ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(15).all()
    content = """<h1 class="text-4xl font-black mb-10 text-indigo-500 uppercase italic">Command Center</h1><div class="grid grid-cols-1 lg:grid-cols-2 gap-8"><div class="glass-card p-8"><h3 class="text-xl font-bold mb-6 italic underline">Clients Actifs</h3>{% for u in users %}<div class="p-4 bg-slate-950/5 text-slate-900 border border-slate-100 rounded-2xl mb-3 flex justify-between items-center"><div class="font-bold">{{u.business_name}}</div><a href="/voice/{{u.id}}" target="_blank" class="text-[10px] bg-indigo-600 text-white px-3 py-1 rounded-full font-bold">TEST IA</a></div>{% endfor %}</div><div class="glass-card p-8"><h3 class="text-xl font-bold mb-6 italic underline">Activité Temps Réel</h3><div class="space-y-4">{% for l in logs %}<div class="p-4 border-l-4 border-indigo-500 bg-slate-50 text-xs rounded-r-xl"><p class="font-bold uppercase mb-1">{{l.owner.business_name}}</p><p class="italic text-slate-500">"{{l.details}}"</p></div>{% endfor %}</div></div></div>"""
    return render_template_string(get_layout(content, "m-admin"), users=users, logs=logs)

@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = """<h1 class="text-3xl font-black mb-10">Gestion du Portefeuille</h1><div class="glass-card overflow-hidden"><table class="w-full text-left"><thead class="bg-slate-900 text-white text-xs font-bold uppercase tracking-widest"><tr class="border-b"><th class="p-8">Enseigne</th><th class="p-8">Secteur</th><th class="p-8">Contact</th><th class="p-8">Réservations</th><th class="p-8">Action</th></tr></thead><tbody class="divide-y divide-slate-100">{% for u in users %}<tr><td class="p-8 font-black text-lg text-indigo-600">{{u.business_name}}</td><td class="p-8 text-slate-500 font-bold uppercase text-xs">{{u.sector}}</td><td class="p-8 text-slate-400 font-mono">{{u.email}}</td><td class="p-8"><span class="bg-emerald-50 text-emerald-600 px-4 py-2 rounded-full font-bold text-xs">{{u.appointments|length}} appels</span></td><td class="p-8"><a href="/master-admin" class="text-slate-400 hover:text-indigo-600"><i class="fas fa-edit text-xl"></i></a></td></tr>{% endfor %}</tbody></table></div>"""
    return render_template_string(get_layout(content, "m-clients"), users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = """<h1 class="text-3xl font-black mb-10">Database Global Logs</h1><div class="space-y-4">{% for l in logs %}<div class="glass-card p-6 flex justify-between items-center"><div class="flex gap-4 items-center"><div class="p-4 bg-indigo-500 text-white rounded-2xl font-black italic">IA</div><div><p class="font-bold text-slate-900">{{l.owner.business_name}} <span class="text-slate-400 font-normal">| ID: {{l.user_id}}</span></p><p class="text-sm italic text-slate-600 mt-1">"{{l.details}}"</p></div></div><p class="text-xs font-bold text-slate-400">{{l.date_str}}</p></div>{% endfor %}</div>"""
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "MAÎTRE SUPRÊME ACTIVÉ"
    return "Email non trouvé"

# --- CORE IA VOICE ENGINE ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    if not txt:
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, que puis-je faire pour vous ?"
    else:
        prompt = f"""Tu es l'agent IA de {c.business_name}. 
        SECTEUR: {c.sector}
        ADRESSE: {c.adresse}
        HORAIRES: {c.horaires}
        TARIFS/SERVICES: {c.tarifs}
        DURÉE MOYENNE: {c.duree_moyenne} min
        INSTRUCTIONS: {c.prompt_personnalise}
        
        Si le client veut prendre rendez-vous, réponds positivement et demande la date et l'heure. 
        Dès que la réservation est fixée, commence ta réponse par 'CONFIRMATION_RDV: [Prestation, Date, Heure]'."""
        
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
        ai_res = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in ai_res:
            db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=ai_res.split("CONFIRMATION_RDV:")[1].strip(), user_id=c.id))
            db.session.commit(); ai_res = ai_res.split("CONFIRMATION_RDV:")[0]
            
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_res, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)