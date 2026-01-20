from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_enterprise_ultra_2026'

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
    
    # Configuration Business Avancée
    sector = db.Column(db.String(100), default="Services")
    horaires = db.Column(db.Text, default="Lundi-Vendredi: 9h-18h")
    tarifs = db.Column(db.Text, default="Service standard: 50€")
    duree_moyenne = db.Column(db.String(20), default="30")
    adresse = db.Column(db.String(255), default="Non renseignée")
    
    # Configuration IA & Personnalisation
    prompt_personnalise = db.Column(db.Text, default="Sois accueillant, précis et professionnel.")
    voix_preferee = db.Column(db.String(20), default="fr-FR-Wavenet-A")
    
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

with app.app_context():

# --- DESIGN ENGINE (UI/UX PREMIUM) ---
CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
    .sidebar { background: #0f172a; box-shadow: 4px 0 15px rgba(0,0,0,0.1); }
    .nav-link { color: #94a3b8; border-radius: 16px; transition: all 0.3s ease; margin: 4px 0; }
    .nav-link:hover { background: #1e293b; color: #6366f1; transform: translateX(5px); }
    .active-nav { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white !important; shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); }
    .glass-card { background: white; border-radius: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.03); padding: 2rem; }
    .input-field { background: #f1f5f9; border: 2px solid transparent; border-radius: 18px; padding: 1rem; transition: 0.2s; width: 100%; outline: none; }
    .input-field:focus { border-color: #6366f1; background: white; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
</style>
"""

def get_layout(content, active_page="dashboard"):
    sidebar = f"""
    <div class="fixed w-80 h-screen sidebar flex flex-col p-8 text-white z-50">
        <div class="flex items-center gap-4 mb-16 px-2">
            <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/50">
                <i class="fas fa-robot text-xl"></i>
            </div>
            <span class="text-2xl font-black tracking-tighter uppercase italic">DigitagPro<span class="text-indigo-500">.</span></span>
        </div>
        <nav class="flex-1 space-y-2">
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] ml-4 mb-6">Plateforme</p>
            <a href="/dashboard" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='dashboard' else ''}"><i class="fas fa-chart-pie w-5"></i> Dashboard</a>
            <a href="/config-ia" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='config' else ''}"><i class="fas fa-sliders-h w-5"></i> Configuration IA</a>
            <a href="/mon-agenda" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='agenda' else ''}"><i class="fas fa-calendar-alt w-5"></i> Mon Agenda</a>
            
            {f'''<div class="pt-10 mb-6 border-t border-slate-800/50"></div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em] ml-4 mb-6">Administration</p>
            <a href="/master-admin" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-admin' else ''}"><i class="fas fa-shield-alt w-5"></i> Master Control</a>
            <a href="/master-clients" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-clients' else ''}"><i class="fas fa-users w-5"></i> Gérer Clients</a>
            <a href="/master-logs" class="flex items-center gap-4 p-4 nav-link {'active-nav' if active_page=='m-logs' else ''}"><i class="fas fa-terminal w-5"></i> Système Logs</a>''' if current_user.is_admin else ''}
        </nav>
        <div class="pt-8 border-t border-slate-800">
            <a href="/logout" class="flex items-center gap-4 p-4 text-red-400 hover:bg-red-500/10 rounded-2xl transition font-bold uppercase text-xs tracking-widest"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
        </div>
    </div>
    """
    return f"{CSS}<div class='flex'>{sidebar}<main class='ml-80 flex-1 p-12 min-h-screen bg-[#f8fafc]'>{content}</main></div>"

# --- AUTH ROUTES ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
        flash("Identifiants incorrects.")
    return render_template_string(CSS + """<body class="bg-[#0f172a] flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3rem] shadow-2xl w-[450px]"><div class="text-center mb-12"><h2 class="text-4xl font-black text-slate-900 mb-2 italic">DIGITAGPRO</h2><p class="text-slate-400 font-medium uppercase tracking-widest text-[10px]">Passerelle de Connexion Pro</p></div><div class="space-y-6"><input name="email" type="email" placeholder="Email Business" class="input-field" required><input name="password" type="password" placeholder="Mot de passe" class="input-field" required><button class="w-full bg-indigo-600 text-white p-5 rounded-[20px] font-black shadow-xl shadow-indigo-500/30 hover:bg-indigo-500 transition-all transform hover:-translate-y-1">ACCÉDER AU DASHBOARD</button></div><p class="text-center mt-10 text-[10px] text-slate-300 font-bold uppercase tracking-[0.3em]">Version Enterprise 2.0</p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first(): return "Compte existant."
        u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'), sector=request.form.get('sector'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(CSS + """<body class="bg-slate-50 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-16 rounded-[3rem] shadow-2xl w-[500px] border border-slate-100"><h2 class="text-3xl font-black mb-10 text-slate-900">Nouveau Partenaire</h2><div class="space-y-4"><input name="b_name" placeholder="Nom Commercial" class="input-field" required><input name="sector" placeholder="Secteur d'activité" class="input-field" required><input name="email" type="email" placeholder="Email" class="input-field" required><input name="password" type="password" placeholder="Mot de passe" class="input-field" required><button class="w-full bg-slate-900 text-white p-5 rounded-[20px] font-black mt-6 shadow-xl hover:bg-indigo-600 transition">CRÉER MON AGENT IA</button></div></form></body>""")

# --- CLIENT DASHBOARD & LOGIC ---
@app.route('/dashboard')
@login_required
def dashboard():
    last_rdv = current_user.appointments[-1].date_str if current_user.appointments else "Aucun appel"
    content = f"""
    <div class="flex justify-between items-center mb-16">
        <div><h1 class="text-5xl font-extrabold tracking-tight text-slate-900 mb-2">Bonjour, {current_user.business_name}</h1><p class="text-slate-400 font-medium">Voici l'état actuel de votre accueil téléphonique IA.</p></div>
        <div class="flex items-center gap-4 bg-white p-4 rounded-3xl border border-slate-100 shadow-sm"><div class="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div><span class="text-sm font-bold text-slate-700 uppercase tracking-widest">Agent IA : Opérationnel</span></div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-phone-alt"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Appels Gérés</p><p class="text-3xl font-black text-slate-900 mt-1">{{{{ current_user.appointments|length }}}}</p></div></div>
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-calendar-check"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Dernière Réservation</p><p class="text-lg font-black text-slate-900 mt-1">{last_rdv}</p></div></div>
        <div class="glass-card flex items-center gap-6"><div class="w-16 h-16 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center text-2xl"><i class="fas fa-tags"></i></div><div><p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Secteur IA</p><p class="text-lg font-black text-slate-900 mt-1">{{{{ current_user.sector }}}}</p></div></div>
    </div>
    
    <div class="glass-card bg-indigo-600 text-white p-12 border-none relative overflow-hidden">
        <div class="relative z-10">
            <h3 class="text-2xl font-bold mb-4">Besoin de tester votre agent ?</h3>
            <p class="text-indigo-100 mb-8 max-w-lg leading-relaxed font-medium">Configurez votre numéro Twilio et pointez le Webhook vers l'adresse ci-dessous. Votre agent répondra instantanément avec votre voix préférée.</p>
            <div class="bg-indigo-700/50 p-6 rounded-2xl border border-white/10 font-mono text-sm inline-block shadow-inner italic">/voice/{{{{ current_user.id }}}}</div>
        </div>
        <i class="fas fa-robot text-[200px] absolute -right-10 -bottom-10 text-white/5 rotate-12"></i>
    </div>
    """
    return render_template_string(get_layout(content, "dashboard"))

@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.business_name = request.form.get('n')
        current_user.horaires = request.form.get('h')
        current_user.tarifs = request.form.get('t')
        current_user.adresse = request.form.get('a')
        current_user.duree_moyenne = request.form.get('d')
        current_user.prompt_personnalise = request.form.get('p')
        db.session.commit()
        flash("Mise à jour effectuée !")
        
    content = """
    <div class="flex justify-between items-center mb-12">
        <h1 class="text-4xl font-black">Expertise de l'Agent</h1>
        <button onclick="document.getElementById('configForm').submit()" class="bg-indigo-600 text-white px-8 py-4 rounded-2xl font-black shadow-lg shadow-indigo-200">SAUVEGARDER LES MODIFS</button>
    </div>
    
    <form id="configForm" method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="glass-card space-y-8">
            <h3 class="text-lg font-bold border-b pb-6 flex items-center gap-3"><i class="fas fa-store text-indigo-500"></i> Identité Business</h3>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Nom du commerce</label><input name="n" value="{{current_user.business_name}}" class="input-field"></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Horaires de fonctionnement</label><textarea name="h" rows="4" class="input-field">{{current_user.horaires}}</textarea></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Adresse de l'établissement</label><input name="a" value="{{current_user.adresse}}" class="input-field"></div>
        </div>
        
        <div class="glass-card space-y-8">
            <h3 class="text-lg font-bold border-b pb-6 flex items-center gap-3"><i class="fas fa-brain text-indigo-500"></i> Intelligence Artificielle</h3>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Tarification & Services (Soyez très précis)</label><textarea name="t" rows="4" class="input-field">{{current_user.tarifs}}</textarea></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Temps moyen de prestation (minutes)</label><input name="d" value="{{current_user.duree_moyenne}}" class="input-field"></div>
            <div><label class="text-[10px] font-bold text-slate-400 uppercase mb-3 block">Instructions de dialogue & Ton</label><textarea name="p" rows="4" class="input-field">{{current_user.prompt_personnalise}}</textarea></div>
        </div>
    </form>
    """
    return render_template_string(get_layout(content, "config"))

@app.route('/mon-agenda')
@login_required
def mon_agenda():
    content = """
    <h1 class="text-4xl font-black mb-12 italic tracking-tight">Agenda des Réservations</h1>
    <div class="glass-card overflow-hidden !p-0 border border-slate-100">
        <div class="bg-slate-50 p-8 border-b border-slate-100 flex justify-between items-center">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest italic">Aujourd'hui : {{ current_date }}</span>
            <div class="flex gap-4"><button class="px-6 py-2 bg-white rounded-xl text-xs font-bold border border-slate-200">Exporter en PDF</button></div>
        </div>
        <div class="divide-y divide-slate-50">
            {% for r in current_user.appointments|reverse %}
            <div class="p-8 hover:bg-slate-50/50 transition-all flex justify-between items-center group">
                <div class="flex items-center gap-8">
                    <div class="w-16 h-16 bg-slate-100 text-slate-400 rounded-3xl flex items-center justify-center group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                        <i class="fas fa-phone-volume text-xl"></i>
                    </div>
                    <div>
                        <p class="text-xl font-bold text-slate-900 mb-1 italic">"{{ r.details }}"</p>
                        <p class="text-xs font-bold text-indigo-400 uppercase tracking-widest">Enregistré le {{ r.date_str }}</p>
                    </div>
                </div>
                <div class="text-right">
                    <span class="px-6 py-2 bg-emerald-50 text-emerald-600 rounded-full font-black text-[10px] uppercase">Rendez-vous Confirmé</span>
                </div>
            </div>
            {% else %}
            <div class="p-32 text-center text-slate-300">
                <i class="fas fa-calendar-alt text-8xl mb-6 opacity-10"></i>
                <p class="text-lg font-medium italic">Aucune donnée de réservation pour le moment.</p>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(get_layout(content, "agenda"), current_date=datetime.now().strftime("%d %B %Y"))

# --- MASTER ADMIN VIEWS ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return redirect(url_for('dashboard'))
    users = User.query.all(); logs = Appointment.query.order_by(Appointment.id.desc()).limit(20).all()
    content = """
    <h1 class="text-4xl font-black mb-12 text-indigo-600 uppercase italic underline underline-offset-8">Master Command Center</h1>
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-10">
        <div class="glass-card">
            <h3 class="text-xl font-extrabold mb-8 italic">État de la Flotte Agents</h3>
            <div class="space-y-4">
                {% for u in users %}
                <div class="p-6 bg-slate-950 text-white rounded-[2rem] flex justify-between items-center">
                    <div><p class="font-bold text-lg">{{u.business_name}}</p><p class="text-[10px] text-slate-400 font-mono">{{u.email}}</p></div>
                    <a href="/voice/{{u.id}}" target="_blank" class="p-4 bg-indigo-600 rounded-2xl hover:bg-white hover:text-indigo-600 transition-all shadow-lg"><i class="fas fa-phone"></i></a>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="glass-card">
            <h3 class="text-xl font-extrabold mb-8 italic">Flux de Données Entrants</h3>
            <div class="space-y-4">
                {% for l in logs %}
                <div class="p-4 border-l-4 border-indigo-500 bg-slate-50 rounded-r-2xl">
                    <p class="text-[10px] font-bold text-indigo-400 uppercase mb-1">{{l.owner.business_name}}</p>
                    <p class="text-xs italic text-slate-600 leading-relaxed">"{{l.details}}"</p>
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
    <h1 class="text-4xl font-black mb-12">Gestion Portefeuille SaaS</h1>
    <div class="glass-card !p-0 overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead class="bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-[0.2em]">
                <tr><th class="p-8">Structure</th><th class="p-8">Secteur</th><th class="p-8">Appels/RDV</th><th class="p-8">Admin Access</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for u in users %}
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="p-8"><p class="font-black text-slate-900 text-xl">{{u.business_name}}</p><p class="text-xs text-slate-400">{{u.email}}</p></td>
                    <td class="p-8"><span class="px-4 py-2 bg-indigo-50 text-indigo-600 rounded-xl text-[10px] font-black uppercase">{{u.sector}}</span></td>
                    <td class="p-8 font-black text-2xl text-slate-900">{{u.appointments|length}}</td>
                    <td class="p-8"><a href="#" class="text-slate-300 hover:text-indigo-600 transition"><i class="fas fa-user-shield text-2xl"></i></a></td>
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
    <h1 class="text-4xl font-black mb-12">Database System Logs</h1>
    <div class="space-y-4">
        {% for l in logs %}
        <div class="glass-card !py-6 flex justify-between items-center hover:border-indigo-200 transition-colors">
            <div class="flex items-center gap-6">
                <div class="w-14 h-14 bg-slate-900 text-indigo-400 rounded-2xl flex items-center justify-center font-black">LOG</div>
                <div><p class="font-black text-slate-900">{{l.owner.business_name}} <span class="text-slate-400 font-normal">| UID:{{l.user_id}}</span></p><p class="text-sm italic text-slate-500 mt-1">"{{l.details}}"</p></div>
            </div>
            <p class="text-[10px] font-bold text-slate-300 uppercase italic">{{l.date_str}}</p>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(get_layout(content, "m-logs"), logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "ACCÈS MAÎTRE VALIDÉ - VEUILLEZ RAFRAICHIR"
    return "Utilisateur introuvable."

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

# --- CORE IA VOICE ENGINE (CORRIGÉ & SÉCURISÉ) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    if not txt:
        ai_res = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        prompt = f"""Tu es l'agent IA de {c.business_name}. 
        SECTEUR: {c.sector} | VILLE: {c.adresse} | HORAIRES: {c.horaires}
        TARIFS/SERVICES: {c.tarifs} | TEMPS PRÉVU: {c.duree_moyenne} min
        TON: {c.prompt_personnalise}
        
        RÈGLES: Si le client veut un RDV, demande la date et l'heure précises. 
        Dès que c'est fixé, conclus par : 'CONFIRMATION: [Date, Heure, Service]'."""
        
        try:
            chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
            ai_res = chat.choices[0].message.content
            
            if "CONFIRMATION:" in ai_res:
                details_clean = ai_res.split("CONFIRMATION:")[1].strip()
                # Écriture sécurisée en base de données
                db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m à %H:%M"), details=details_clean, user_id=c.id))
                db.session.commit()
                # On ne lit pas le tag de confirmation au client
                ai_res = ai_res.split("CONFIRMATION:")[0] + " Parfait, c'est enregistré."
        except Exception as e:
            print(f"DEBUG IA ERROR: {e}")
            ai_res = "Je vous prie de m'excuser, j'ai eu une petite interférence. Pouvez-vous répéter ?"

    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_res, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)