from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_ultra_2026_v3'

# --- CONFIGURATION BASE DE DONNÉES ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÈLES (ARCHITECTURÉS POUR LE SAAS) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Configuration Métier
    sector = db.Column(db.String(100), default="Services")
    horaires = db.Column(db.Text, default="Lundi-Vendredi: 9h-18h")
    tarifs = db.Column(db.Text, default="Service standard: 50€")
    duree_moyenne = db.Column(db.String(20), default="30")
    adresse = db.Column(db.String(255), default="Non renseignée")
    
    # Personnalisation IA
    prompt_personnalise = db.Column(db.Text, default="Sois accueillant, précis et professionnel.")
    voix_preferee = db.Column(db.String(20), default="fr-FR-Standard-A")
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), default="Client Vocal")
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Confirmé")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# --- INITIALISATION DE FORCE ---
with app.app_context():
    # Décommenter les deux lignes suivantes pour TOUT remettre à zéro si l'erreur persiste
    db.drop_all() # Supprime les vieilles tables qui buggent
    db.create_all() # Recrée les tables avec toutes les colonnes (SaaS V3)
    print("Base de données réinitialisée avec succès.")            
            # 2. MISE À JOUR DE LA TABLE APPOINTMENT (Celle qui bloque maintenant)
            cols_app = {"client_name": "VARCHAR(100)", "status": "VARCHAR(20)"}
            for col, dtype in cols_app.items():
                try:
                    conn.execute(text(f'ALTER TABLE "appointment" ADD COLUMN {col} {dtype}'))
                    conn.commit()
                except: pass
    except: pass
# --- DESIGN SYSTEM ---
CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; }
    .sidebar { background: #0f172a; }
    .nav-link { color: #94a3b8; border-radius: 12px; transition: all 0.2s; }
    .nav-link:hover { background: #1e293b; color: white; }
    .active-nav { background: #6366f1; color: white !important; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3); }
    .glass-card { background: white; border-radius: 24px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 12px; padding: 12px; transition: 0.2s; width: 100%; outline: none; }
    .input-pro:focus { border-color: #6366f1; background: white; }
</style>
"""

def get_layout(content, active_page="dashboard"):
    sidebar = f"""
    <div class="fixed w-72 h-screen sidebar flex flex-col p-6 text-white z-50">
        <div class="flex items-center gap-3 mb-12 px-2">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-black">D</div>
            <span class="text-xl font-extrabold tracking-tighter">DIGITAGPRO<span class="text-indigo-500">.</span></span>
        </div>
        <nav class="flex-1 space-y-2">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-4">Espace Client</p>
            <a href="/dashboard" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-th-large"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-robot"></i> Config IA</a>
            <a href="/mon-agenda" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-alt"></i> Agenda</a>
            
            {f'''<div class="my-8 border-t border-slate-800 opacity-50"></div>
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-4 mb-4">Master</p>
            <a href="/master-admin" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-admin' else ''} text-indigo-400"><i class="fas fa-crown"></i> Console</a>
            <a href="/master-clients" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-clients' else ''} text-indigo-400"><i class="fas fa-users"></i> Clients</a>
            <a href="/master-logs" class="flex items-center gap-3 p-4 nav-link {'active-nav' if active_page=='m-logs' else ''} text-indigo-400"><i class="fas fa-database"></i> Logs</a>''' if current_user.is_admin else ''}
        </nav>
        <div class="pt-6 border-t border-slate-800 mt-auto">
            <a href="/logout" class="flex items-center gap-3 p-4 text-red-400 hover:bg-red-500/10 rounded-xl transition font-bold text-xs uppercase"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
        </div>
    </div>
    """
    return f"{CSS}<div class='flex'>{sidebar}<main class='ml-72 flex-1 p-10 min-h-screen bg-slate-50'>{content}</main></div>"

# --- ROUTES AUTH ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
    return render_template_string(CSS + """<body class="bg-slate-950 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-2xl w-[400px]"><h2 class="text-3xl font-black mb-8 text-center italic text-indigo-600">DIGITAGPRO</h2><div class="space-y-4"><input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-100 rounded-xl outline-none border focus:border-indigo-500"><input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-100 rounded-xl outline-none border focus:border-indigo-500"><button class="w-full bg-slate-900 text-white p-4 rounded-xl font-black hover:bg-indigo-600 transition">ENTRER</button></div></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(CSS + """<body class="bg-slate-100 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-xl w-[450px]"><h2 class="text-2xl font-black mb-8">Nouveau Compte IA</h2><div class="space-y-4"><input name="b_name" placeholder="Entreprise" class="w-full p-4 bg-slate-50 rounded-xl outline-none"><input name="sector" placeholder="Secteur" class="w-full p-4 bg-slate-50 rounded-xl outline-none"><input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-50 rounded-xl outline-none"><input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-50 rounded-xl outline-none"><button class="w-full bg-indigo-600 text-white p-4 rounded-xl font-black">LANCER MON IA</button></div></form></body>""")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- CLIENT VIEW ---
@app.route('/dashboard')
@login_required
def dashboard():
    content = """<h1 class="text-4xl font-black mb-10 text-slate-900">Dashboard</h1><div class="grid grid-cols-3 gap-8 mb-10"><div class="glass-card p-8 bg-white border-l-4 border-indigo-500"><div><p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Réservations IA</p><p class="text-3xl font-black mt-2">{{ current_user.appointments|length }}</p></div></div><div class="glass-card p-8 bg-white border-l-4 border-emerald-500"><div><p class="text-xs font-bold text-slate-400 uppercase tracking-widest">Statut Agent</p><p class="text-lg font-bold mt-2 text-emerald-600">Connecté</p></div></div></div>"""
    return render_template_string(get_layout(content, "dashboard"))

@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.horaires = request.form.get('h'); current_user.tarifs = request.form.get('t')
        current_user.adresse = request.form.get('a'); current_user.duree_moyenne = request.form.get('d')
        current_user.prompt_personnalise = request.form.get('p'); db.session.commit(); flash("Config sauvée")
    content = """<h1 class="text-3xl font-black mb-10">Config Agent IA</h1><form method="POST" class="grid grid-cols-2 gap-8"><div class="glass-card p-8 space-y-6"><div><label class="text-xs font-bold uppercase text-slate-400 mb-2 block">Horaires</label><textarea name="h" rows="3" class="input-pro">{{ current_user.horaires }}</textarea></div><div><label class="text-xs font-bold uppercase text-slate-400 mb-2 block">Tarifs & Services</label><textarea name="t" rows="5" class="input-pro">{{ current_user.tarifs }}</textarea></div></div><div class="glass-card p-8 space-y-6"><div><label class="text-xs font-bold uppercase text-slate-400 mb-2 block">Adresse</label><input name="a" value="{{ current_user.adresse }}" class="input-pro"></div><div><label class="text-xs font-bold uppercase text-slate-400 mb-2 block">Durée par RDV (min)</label><input name="d" value="{{ current_user.duree_moyenne }}" class="input-pro"></div><div><label class="text-xs font-bold uppercase text-slate-400 mb-2 block">Instructions IA</label><textarea name="p" rows="3" class="input-pro">{{ current_user.prompt_personnalise }}</textarea></div><button class="w-full bg-indigo-600 text-white p-4 rounded-xl font-black">SAUVEGARDER</button></div></form>"""
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """<h1 class="text-3xl font-black mb-10 italic">Agenda des RDV</h1><div class="glass-card p-4 space-y-4">{% for r in current_user.appointments|reverse %}<div class="p-6 bg-slate-50 rounded-2xl border flex justify-between items-center"><p class="font-bold">{{ r.details }}</p><span class="text-xs font-bold text-indigo-400 uppercase tracking-widest">{{ r.date_str }}</span></div>{% else %}<p class="text-center py-20 text-slate-400">Aucun rendez-vous enregistré.</p>{% endfor %}</div>"""
    return render_template_string(get_layout(content, "agenda"))

# --- MASTER VIEWS ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(10).all()
    content = """<h1 class="text-3xl font-black mb-10 text-indigo-500 uppercase italic">Command Center</h1><div class="grid grid-cols-2 gap-8"><div class="glass-card p-8"><h3>Flotte Clients</h3>{% for u in users %}<div class="p-4 bg-slate-900 text-white rounded-xl mb-3 flex justify-between items-center"><p>{{u.business_name}}</p><a href="/voice/{{u.id}}" target="_blank" class="text-[10px] bg-indigo-600 px-3 py-1 rounded-full font-bold">TEST</a></div>{% endfor %}</div><div class="glass-card p-8"><h3>Activité Réelle</h3>{% for l in logs %}<div class="p-4 border-l-4 border-indigo-500 bg-slate-50 text-xs mb-2"><p class="font-bold">{{l.owner.business_name}}</p><p class="italic">"{{l.details}}"</p></div>{% endfor %}</div></div>"""
    return render_template_string(get_layout(content, "m-admin"), users=users, logs=logs)

@app.route('/master-clients')
@login_required
def master_clients():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all()
    content = """<h1 class="text-3xl font-black mb-10">Gestion Clients</h1><div class="glass-card overflow-hidden"><table class="w-full text-left"><thead class="bg-slate-900 text-white text-xs font-bold uppercase tracking-widest"><tr><th class="p-8">Entreprise</th><th class="p-8">Contact</th><th class="p-8">Réservations</th></tr></thead><tbody class="divide-y divide-slate-100">{% for u in users %}<tr><td class="p-8 font-bold text-lg text-indigo-600">{{u.business_name}}</td><td class="p-8 text-slate-500 text-xs">{{u.email}}</td><td class="p-8"><span class="bg-emerald-50 text-emerald-600 px-4 py-2 rounded-full font-bold text-xs">{{u.appointments|length}} appels</span></td></tr>{% endfor %}</tbody></table></div>"""
    return render_template_string(get_layout(content, "m-clients"), users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = """<h1 class="text-3xl font-black mb-10">Database Logs</h1><div class="space-y-4">{% for l in logs %}<div class="glass-card p-6 flex justify-between items-center"><p class="font-bold">{{l.owner.business_name}} <span class="text-slate-400 font-normal">| {{l.details}}</span></p><p class="text-[10px] font-bold text-slate-400">{{l.date_str}}</p></div>{% endfor %}</div>"""
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "MAÎTRE ACTIVÉ"
    return "Non trouvé"

# --- MOTEUR IA VOICE AVEC LOGS ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    print("\n" + "="*40)
    print(f"📞 APPEL : {c.business_name}")
    
    if not txt:
        print("🤖 IA : Accueil")
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        print(f"👤 CLIENT : {txt}")
        prompt = f"Tu es l'IA de {c.business_name}. Horaires: {c.horaires}. Tarifs: {c.tarifs}. Si RDV fixé, finis par CONFIRMATION: [Détails]."
        try:
            chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
            ai_res = chat.choices[0].message.content
            print(f"🤖 IA RÉPOND : {ai_res}")
            if "CONFIRMATION:" in ai_res:
                details = ai_res.split("CONFIRMATION:")[1].strip()
                db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=details, user_id=c.id))
                db.session.commit()
                print("✅ RDV ENREGISTRÉ")
                ai_res = ai_res.split("CONFIRMATION:")[0] + " C'est noté."
        except Exception as e:
            print(f"❌ ERREUR IA : {e}")
            ai_res = "Désolé, j'ai une erreur technique momentanée."

    print("="*40 + "\n")
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_res, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)