from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_ultra_v2_2026'

# --- DATABASE CONFIG ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODELS PRO ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Configuration IA détaillée
    horaires = db.Column(db.Text, default="Lun-Ven: 09h-18h")
    tarifs = db.Column(db.Text, default="Prestation standard: 50€")
    temps_prestation = db.Column(db.String(50), default="30 min")
    instructions_speciales = db.Column(db.Text, default="Accueillir le client avec courtoisie.")
    
    appointments = db.relationship('Appointment', backref='owner', lazy=True, cascade="all, delete-orphan")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100))
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Confirmé")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

from sqlalchemy import text

with app.app_context():
    db.create_all()
    # Script de secours pour ajouter les colonnes manquantes sans tout casser
    try:
        with db.engine.connect() as conn:
            # Liste des nouvelles colonnes à vérifier
            cols = {
                "horaires": "TEXT",
                "tarifs": "TEXT",
                "temps_prestation": "VARCHAR(50)",
                "instructions_speciales": "TEXT"
            }
            for col, type in cols.items():
                try:
                    conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {type}'))
                    conn.commit()
                    print(f"Colonne {col} ajoutée avec succès.")
                except Exception:
                    # La colonne existe déjà, on ignore
                    pass
    except Exception as e:
        print(f"Erreur lors de la mise à jour des colonnes : {e}")
# --- DESIGN SYSTEM ---
STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; }
    .sidebar-active { background: #6366f1; color: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
    .card-pro { background: white; border-radius: 24px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .input-pro { background: #f1f5f9; border: 2px solid transparent; border-radius: 16px; padding: 12px 16px; transition: all 0.2s; }
    .input-pro:focus { border-color: #6366f1; background: white; outline: none; }
</style>
"""

def layout(content, active="dashboard"):
    is_master = current_user.is_admin if current_user.is_authenticated else False
    bg_color = "bg-slate-950 text-white" if is_master else "bg-white text-slate-900"
    
    sidebar = f"""
    <div class="fixed w-72 h-screen {bg_color} border-r border-slate-200 p-8 flex flex-col z-50">
        <div class="text-2xl font-extrabold mb-12 flex items-center gap-2">
            <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm">D</div>
            <span>DIGITAG<span class="text-indigo-600">PRO</span></span>
        </div>
        <nav class="flex-1 space-y-3">
            <a href="/dashboard" class="flex items-center gap-3 p-4 transition {'sidebar-active' if active=='dashboard' else 'text-slate-500 hover:bg-slate-50'}"><i class="fas fa-calendar-alt"></i> Agenda</a>
            <a href="/config-ia" class="flex items-center gap-3 p-4 transition {'sidebar-active' if active=='config' else 'text-slate-500 hover:bg-slate-50'}"><i class="fas fa-robot"></i> Configuration IA</a>
            { '<a href="/master-admin" class="flex items-center gap-3 p-4 text-indigo-400 font-bold italic"><i class="fas fa-crown"></i> Master Mode</a>' if is_master else '' }
        </nav>
        <a href="/logout" class="mt-auto p-4 text-red-500 font-bold flex items-center gap-2 hover:bg-red-50 rounded-xl transition"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
    </div>
    """
    return f"{STYLE}<div class='flex'>{sidebar}<main class='ml-72 flex-1 min-h-screen p-12 bg-slate-50'>{content}</main></div>"

# --- ROUTES ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('dashboard'))
    return render_template_string(STYLE + """<body class="bg-slate-100 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-xl w-[400px] border border-slate-200"><h2 class="text-3xl font-black mb-8 text-center">Accès Pro</h2><input name="email" placeholder="Email" class="w-full input-pro mb-4"><input name="password" type="password" placeholder="Mot de passe" class="w-full input-pro mb-8"><button class="w-full bg-slate-900 text-white p-4 rounded-2xl font-bold hover:bg-indigo-600 transition">Se connecter</button><p class="text-center mt-6 text-sm text-slate-400">Pas encore client ? <a href="/register" class="text-indigo-600 font-bold">Créer un compte</a></p></form></body>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_u = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('b_name'))
        db.session.add(new_u); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(STYLE + """<body class="bg-slate-100 flex items-center justify-center h-screen"><form method="POST" class="bg-white p-12 rounded-[2.5rem] shadow-xl w-[450px] border border-slate-200"><h2 class="text-3xl font-black mb-8">Démarrer DigitagPro</h2><input name="b_name" placeholder="Nom de votre commerce" class="w-full input-pro mb-4" required><input name="email" type="email" placeholder="Email" class="w-full input-pro mb-4" required><input name="password" type="password" placeholder="Mot de passe" class="w-full input-pro mb-8" required><button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black">LANCER MON IA</button></form></body>""")

# --- DASHBOARD CLIENT : AGENDA ---
@app.route('/dashboard')
@login_required
def dashboard():
    content = """
    <div class="flex justify-between items-end mb-12">
        <div>
            <p class="text-slate-400 font-bold uppercase text-xs tracking-widest mb-1">Tableau de bord</p>
            <h1 class="text-4xl font-black text-slate-900">Mon Agenda IA</h1>
        </div>
        <div class="bg-white px-6 py-3 rounded-2xl border border-slate-200 font-bold text-slate-600">
            <i class="fas fa-circle text-emerald-500 text-[10px] mr-2"></i> Agent IA : Actif
        </div>
    </div>
    
    <div class="grid grid-cols-1 gap-8">
        <div class="card-pro p-8">
            <div class="flex items-center justify-between mb-8">
                <h2 class="text-xl font-bold">Prochaines Réservations</h2>
                <span class="text-sm text-slate-400">{{ current_user.appointments|length }} rendez-vous</span>
            </div>
            
            <div class="space-y-4">
                {% for r in current_user.appointments|reverse %}
                <div class="flex items-center justify-between p-6 bg-slate-50 rounded-2xl border border-slate-100 hover:border-indigo-200 transition">
                    <div class="flex items-center gap-6">
                        <div class="w-12 h-12 bg-white rounded-xl flex flex-col items-center justify-center shadow-sm border border-slate-200">
                            <span class="text-[10px] font-bold text-indigo-600 uppercase">{{ r.date_str.split(' ')[0] }}</span>
                        </div>
                        <div>
                            <p class="font-bold text-slate-900">{{ r.details }}</p>
                            <p class="text-xs text-slate-500"><i class="far fa-clock mr-1"></i> Reçu le {{ r.date_str }}</p>
                        </div>
                    </div>
                    <span class="px-4 py-1 bg-emerald-100 text-emerald-600 rounded-full text-[10px] font-bold uppercase">Confirmé</span>
                </div>
                {% else %}
                <div class="text-center py-20 text-slate-400">
                    <i class="fas fa-calendar-day text-4xl mb-4 opacity-20"></i>
                    <p>Aucun rendez-vous pour le moment.</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    """
    return render_template_string(layout(content, "dashboard"))

# --- PAGE CONFIGURATION IA ---
@app.route('/config-ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    if request.method == 'POST':
        current_user.horaires = request.form.get('horaires')
        current_user.tarifs = request.form.get('tarifs')
        current_user.temps_prestation = request.form.get('temps')
        current_user.instructions_speciales = request.form.get('instructions')
        db.session.commit()
        flash("Configuration mise à jour !")
        return redirect(url_for('config_ia'))
        
    content = """
    <h1 class="text-4xl font-black text-slate-900 mb-12">Configuration de l'IA</h1>
    
    <form method="POST" class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div class="card-pro p-10 space-y-8">
            <h3 class="text-lg font-bold border-b border-slate-100 pb-4"><i class="fas fa-cog mr-2 text-indigo-500"></i> Paramètres du commerce</h3>
            
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase mb-2">Horaires d'ouverture</label>
                <textarea name="horaires" rows="3" class="w-full input-pro" placeholder="Ex: Lundi au Vendredi, 8h-12h / 14h-18h">{{ current_user.horaires }}</textarea>
            </div>
            
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase mb-2">Carte des prix / Services</label>
                <textarea name="tarifs" rows="5" class="w-full input-pro" placeholder="Ex: Coupe Homme 20€, Forfait Barbe 15€...">{{ current_user.tarifs }}</textarea>
            </div>
        </div>
        
        <div class="card-pro p-10 space-y-8">
            <h3 class="text-lg font-bold border-b border-slate-100 pb-4"><i class="fas fa-magic mr-2 text-indigo-500"></i> Comportement de l'IA</h3>
            
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase mb-2">Durée moyenne par rendez-vous</label>
                <input name="temps" value="{{ current_user.temps_prestation }}" class="w-full input-pro" placeholder="Ex: 30 minutes">
            </div>
            
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase mb-2">Instructions de vente / Accueil</label>
                <textarea name="instructions" rows="5" class="w-full input-pro" placeholder="Ex: Toujours proposer le soin VIP, être très poli...">{{ current_user.instructions_speciales }}</textarea>
            </div>
            
            <button class="w-full bg-indigo-600 text-white p-5 rounded-2xl font-black shadow-lg shadow-indigo-200 hover:scale-[1.02] transition transform">
                ENREGISTRER LA CONFIGURATION
            </button>
        </div>
    </form>
    """
    return render_template_string(layout(content, "config"))

# --- MASTER ADMIN ---
@app.route('/master-admin')
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès Master uniquement", 403
    users = User.query.all()
    content = """
    <h1 class="text-4xl font-black mb-12">Master Control</h1>
    <div class="card-pro overflow-hidden">
        <table class="w-full text-left">
            <thead class="bg-slate-50 border-b border-slate-100">
                <tr class="text-xs font-bold text-slate-400 uppercase tracking-widest">
                    <th class="p-6">Client</th><th class="p-6">Email</th><th class="p-6">Stats</th><th class="p-6">Action</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for u in users %}
                <tr class="hover:bg-slate-50 transition">
                    <td class="p-6 font-bold">{{ u.business_name }}</td>
                    <td class="p-6 text-slate-500">{{ u.email }}</td>
                    <td class="p-6"><span class="bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full text-xs">{{ u.appointments|length }} RDV</span></td>
                    <td class="p-6"><a href="/voice/{{ u.id }}" class="text-indigo-600 hover:underline">Tester Voice</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(layout(content, "master"), users=users)

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "Status: MASTER"
    return "Not Found"

# --- IA ENGINE VOCO ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    
    if not txt:
        ai_msg = f"Bonjour, bienvenue chez {c.business_name}, que puis-je faire pour vous ?"
    else:
        # Prompt Ultra-Structuré basé sur les nouveaux champs
        prompt = f"""Tu es l'assistant de {c.business_name}. 
        HORAIRES: {c.horaires}
        TARIFS/SERVICES: {c.tarifs}
        DURÉE RDV: {c.temps_prestation}
        TON ET INSTRUCTIONS: {c.instructions_speciales}
        
        Si le client veut prendre rendez-vous, demande la date et l'heure.
        Dès que le rendez-vous est convenu, tu DOIS commencer ta réponse par 'CONFIRMATION_RDV: [Détail du service et heure]'."""
        
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": txt}])
        ai_msg = chat.choices[0].message.content
        
        if "CONFIRMATION_RDV:" in ai_msg:
            details = ai_msg.split("CONFIRMATION_RDV:")[1].strip()
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=details, user_id=c.id)
            db.session.add(new_rdv); db.session.commit()
            ai_msg = ai_msg.split("CONFIRMATION_RDV:")[0]
            
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai_msg, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)