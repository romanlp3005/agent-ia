from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_ultra_2026_vfinal'

# --- CONFIGURATION BASE DE DONNÉES ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÈLES SAAS COMPLET ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Données Métier
    sector = db.Column(db.String(100), default="Services")
    horaires = db.Column(db.Text, default="Lun-Ven: 09h-18h")
    tarifs = db.Column(db.Text, default="Prestation: 50€")
    duree_moyenne = db.Column(db.String(20), default="30")
    adresse = db.Column(db.String(255), default="Non renseignée")
    
    # Paramètres IA
    prompt_personnalise = db.Column(db.Text, default="Sois professionnel et accueillant.")
    voix_preferee = db.Column(db.String(20), default="fr-FR-Standard-A")
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), default="Client Vocal")
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Confirmé")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# --- INITIALISATION DE FORCE (FIX SCHEMA) ---
with app.app_context():
    # Décommenter db.drop_all() uniquement si l'erreur UndefinedColumn persiste
    # db.drop_all() 
    db.create_all()
    print("🚀 Moteur synchronisé à 100%")

# --- UI PREMIUM ---
STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
    .sidebar { background: #0f172a; box-shadow: 4px 0 15px rgba(0,0,0,0.1); }
    .nav-link { color: #94a3b8; border-radius: 16px; transition: all 0.3s ease; margin: 4px 0; }
    .nav-link:hover { background: #1e293b; color: #6366f1; transform: translateX(5px); }
    .active-nav { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white !important; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); }
    .glass-card { background: white; border-radius: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.03); padding: 2.5rem; }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 18px; padding: 1.2rem; transition: 0.2s; width: 100%; outline: none; }
    .input-pro:focus { border-color: #6366f1; background: white; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
</style>
"""

def get_layout(content, active_page="dashboard"):
    is_m = current_user.is_admin if current_user.is_authenticated else False
    sidebar = f"""
    <div class="fixed w-80 h-screen sidebar flex flex-col p-8 text-white z-50">
        <div class="flex items-center gap-4 mb-16 px-2">
            <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg"><i class="fas fa-robot text-xl"></i></div>
            <span class="text-2xl font-black italic tracking-tighter">DigitagPro<span class="text-indigo-500">.</span></span>
        </div>
        <nav class="flex-1 space-y-2">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-4">Navigation</p>
            <a href="/dashboard" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-chart-pie"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-sliders-h"></i> Configuration</a>
            <a href="/mon-agenda" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-alt"></i> Agenda</a>
            
            {f'''<div class="pt-10 mb-6 border-t border-slate-800/50"></div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest ml-4 mb-4">Administration</p>
            <a href="/master-admin" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-admin' else ''}"><i class="fas fa-shield-alt"></i> Master Console</a>
            <a href="/master-clients" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-clients' else ''}"><i class="fas fa-users"></i> Clients</a>
            <a href="/master-logs" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-logs' else ''}"><i class="fas fa-terminal"></i> Logs Système</a>''' if is_m else ''}
        </nav>
        <a href="/logout" class="mt-auto p-4 text-red-400 font-bold flex items-center gap-2 hover:bg-red-500/10 rounded-2xl transition uppercase text-xs tracking-widest"><i class="fas fa-power-off"></i> Déconnexion</a>
    </div>
    """
    return f"{STYLE}<div class='flex'>{sidebar}<main class='ml-80 flex-1 p-12 min-h-screen bg-[#f8fafc]'>{content}</main></div>"

# --- AUTH ROUTES ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
    return render_template_string(STYLE + """<body class="bg-[#0f172a] flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3rem] shadow-2xl w-[450px]"><h2 class="text-4xl font-black text-slate-900 mb-10 text-center italic">DIGITAGPRO</h2><input name="email" type="email" placeholder="Email Business" class="input-pro mb-6" required><input name="password" type="password" placeholder="Mot de passe" class="input-pro mb-8" required><button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black shadow-xl hover:bg-indigo-500 transition">OUVRIR LA SESSION</button><p class="text-center mt-6 text-sm">Nouveau ? <a href="/register" class="text-indigo-600 font-bold">Inscrivez-vous</a></p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
            db.session.add(u); db.session.commit(); return redirect(url_for('login'))
        except Exception as e: return f"Erreur lors de la création : {e}"
    return render_template_string(STYLE + """<body class="bg-slate-50 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3rem] shadow-2xl w-[500px] border border-slate-100"><h2 class="text-3xl font-black mb-10">Démarrer DigitagPro</h2><div class="space-y-4"><input name="b_name" placeholder="Nom du commerce" class="input-pro" required><input name="sector" placeholder="Secteur (ex: Garage)" class="input-pro" required><input name="email" type="email" placeholder="Email" class="input-pro" required><input name="password" type="password" placeholder="Mot de passe" class="input-pro" required><button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black mt-6 shadow-xl hover:bg-indigo-500 transition">CRÉER MON AGENT IA</button></div></form></body>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- CLIENT LOGIC ---
@app.route('/dashboard')
@login_required
def dashboard():
    content = f"""
    <div class="flex justify-between items-center mb-16"><div><h1 class="text-5xl font-extrabold tracking-tight mb-2">Bonjour, {current_user.business_name}</h1><p class="text-slate-400 font-medium">Votre agent IA gère vos appels 24/7.</p></div></div>
    <div class="grid grid-cols-3 gap-8 mb-12">
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-phone-alt"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Réservations</p><p class="text-3xl font-black mt-1">{{{{ current_user.appointments|length }}}}</p></div></div>
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-check-circle"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Statut Agent</p><p class="text-lg font-black text-emerald-600 mt-1">Actif</p></div></div>
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-briefcase"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Secteur</p><p class="text-lg font-black mt-1">{{{{ current_user.sector }}}}</p></div></div>
    </div>
    <div class="glass-card bg-slate-900 text-white p-12 relative overflow-hidden">
        <div class="relative z-10"><h3 class="text-2xl font-bold mb-4 italic text-indigo-400 underline">Configuration Twilio</h3><p class="text-slate-400 mb-8 max-w-lg leading-relaxed">Pointez le Webhook de votre numéro Twilio vers l'URL ci-dessous pour activer l'agent :</p><div class="bg-indigo-600/20 p-6 rounded-2xl border border-indigo-500/30 font-mono text-sm inline-block shadow-inner italic">/voice/{{{{ current_user.id }}}}</div></div><i class="fas fa-broadcast-tower text-[180px] absolute -right-10 -bottom-10 text-white/5 rotate-12"></i>
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
        db.session.commit(); flash("Configuration enregistrée.")
    content = """
    <h1 class="text-4xl font-black mb-12">Réglages de l'Agent IA</h1>
    <form method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div class="glass-card space-y-8">
            <h3 class="text-lg font-bold border-b pb-6 flex items-center gap-3 italic underline text-indigo-500">Données Commerciales</h3>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Nom d'Enseigne</label><input name="n" value="{{current_user.business_name}}" class="input-pro"></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Horaires (Précis)</label><textarea name="h" rows="3" class="input-pro">{{current_user.horaires}}</textarea></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Adresse</label><input name="a" value="{{current_user.adresse}}" class="input-pro"></div>
        </div>
        <div class="glass-card space-y-8">
            <h3 class="text-lg font-bold border-b pb-6 flex items-center gap-3 italic underline text-indigo-500">Paramètres IA</h3>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Services & Prix</label><textarea name="t" rows="4" class="input-pro">{{current_user.tarifs}}</textarea></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Durée par RDV (min)</label><input name="d" value="{{current_user.duree_moyenne}}" class="input-pro"></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Personnalisation du ton</label><textarea name="p" rows="3" class="input-pro">{{current_user.prompt_personnalise}}</textarea></div>
            <button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black shadow-xl hover:bg-slate-900 transition">ENREGISTRER LA CONFIG</button>
        </div>
    </form>
    """
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """
    <h1 class="text-4xl font-black mb-12">Agenda des Appels</h1>
    <div class="glass-card overflow-hidden !p-0">
        <div class="bg-slate-50 p-8 border-b border-slate-100 flex justify-between items-center"><span class="text-xs font-bold text-slate-500 uppercase italic tracking-widest">Historique IA</span></div>
        <div class="divide-y divide-slate-50">
            {% for r in current_user.appointments|reverse %}
            <div class="p-10 hover:bg-slate-50 transition flex justify-between items-center">
                <div class="flex items-center gap-8">
                    <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-3xl flex items-center justify-center"><i class="fas fa-phone-volume text-xl"></i></div>
                    <div><p class="text-xl font-bold text-slate-900 italic">"{{ r.details }}"</p><p class="text-xs font-bold text-indigo-400 uppercase tracking-widest mt-1">{{ r.date_str }}</p></div>
                </div>
                <span class="px-6 py-2 bg-emerald-50 text-emerald-600 rounded-full font-black text-[10px] uppercase">RDV Enregistré</span>
            </div>
            {% else %}<div class="p-24 text-center text-slate-300 italic">Aucun rendez-vous pour le moment.</div>{% endfor %}
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "agenda"))

# --- MASTER ROUTES ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(15).all()
    content = """<h1 class="text-4xl font-black mb-12 text-indigo-600 uppercase italic">Master Dashboard</h1><div class="grid grid-cols-1 lg:grid-cols-2 gap-10"><div class="glass-card"><h3 class="font-bold mb-6 italic underline">Clients Actifs</h3>{% for u in users %}<div class="p-6 bg-slate-900 text-white rounded-3xl mb-4 flex justify-between items-center"><div><p class="font-bold text-lg">{{u.business_name}}</p><p class="text-xs text-slate-500">{{u.email}}</p></div><a href="/voice/{{u.id}}" target="_blank" class="p-4 bg-indigo-600 rounded-2xl hover:bg-white hover:text-indigo-600 transition shadow-lg"><i class="fas fa-phone"></i></a></div>{% endfor %}</div><div class="glass-card"><h3 class="font-bold mb-6 italic underline">Activité Récente</h3><div class="space-y-4">{% for l in logs %}<div class="p-5 border-l-4 border-indigo-500 bg-slate-50 rounded-r-2xl"><p class="text-[10px] font-bold text-indigo-400 uppercase mb-1">{{l.owner.business_name}}</p><p class="text-xs italic text-slate-600">"{{l.details}}"</p></div>{% endfor %}</div></div></div>"""
    return render_template_string(get_layout(content, "m-admin"), users=users, logs=logs)

@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = """<h1 class="text-4xl font-black mb-12">Portefeuille Clients</h1><div class="glass-card !p-0 overflow-hidden"><table class="w-full text-left"><thead class="bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-widest"><tr><th class="p-8">Structure</th><th class="p-8">Secteur</th><th class="p-8">Réservations</th></tr></thead><tbody class="divide-y divide-slate-100">{% for u in users %}<tr class="hover:bg-slate-50 transition"><td class="p-8"><p class="font-black text-slate-900 text-xl">{{u.business_name}}</p><p class="text-xs text-slate-400">{{u.email}}</p></td><td class="p-8 text-indigo-600 font-black uppercase text-xs">{{u.sector}}</td><td class="p-8 font-black text-2xl text-slate-900">{{u.appointments|length}}</td></tr>{% endfor %}</tbody></table></div>"""
    return render_template_string(get_layout(content, "m-clients"), users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = """<h1 class="text-4xl font-black mb-12 italic">Database Logs</h1><div class="space-y-4">{% for l in logs %}<div class="glass-card !py-6 flex justify-between items-center hover:border-indigo-300 transition shadow-md"><div class="flex items-center gap-6"><div class="w-14 h-14 bg-slate-900 text-indigo-400 rounded-2xl flex items-center justify-center font-black">LOG</div><div><p class="font-black text-slate-900 italic">{{l.owner.business_name}}</p><p class="text-sm text-slate-500">"{{l.details}}"</p></div></div><p class="text-[10px] font-bold text-slate-300 uppercase tracking-widest">{{l.date_str}}</p></div>{% endfor %}</div>"""
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "MAÎTRE ACTIVÉ"
    return "Utilisateur non trouvé."

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- IA VOICE ENGINE (CORRIGÉ & LOGS) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    print("\n" + "="*50)
    print(f"📞 APPEL REÇU : {c.business_name}")
    
    if not txt:
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        print(f"👤 CLIENT : {txt}")
        prompt = f"Tu es l'agent IA de {c.business_name}. Ville: {c.adresse} | Secteur: {c.sector} | Horaires: {c.horaires} | Tarifs: {c.tarifs} | Ton: {c.prompt_personnalise}. Si RDV fixé, finis par CONFIRMATION_RDV: [Détails]."
        try:
            chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
            ai_res = chat.choices[0].message.content
            print(f"🤖 IA RÉPOND : {ai_res}")
            if "CONFIRMATION_RDV:" in ai_res:
                details_rdv = ai_res.split("CONFIRMATION_RDV:")[1].strip()
                db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=details_rdv, user_id=c.id))
                db.session.commit()
                print("✅ RDV ENREGISTRÉ")
                ai_res = ai_res.split("CONFIRMATION_RDV:")[0] + " Parfait, c'est enregistré."
        except Exception as e:
            print(f"❌ ERREUR IA : {e}")
            ai_res = "Je m'excuse, j'ai eu une petite difficulté technique. Pouvez-vous répéter ?"

    print("="*50 + "\n")
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_res, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)