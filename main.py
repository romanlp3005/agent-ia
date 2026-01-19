from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_ultra_secret_2026'

# Configuration SQL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro_database.db')
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
    activity_sector = db.Column(db.String(100), default="Services") # Ajout du secteur
    slots = db.Column(db.Integer, default=1)
    avg_duration = db.Column(db.Integer, default=30)
    prices_info = db.Column(db.Text, default="Ex: Service A: 20€\nService B: 50€")
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

# --- DESIGN SYSTEM ---
BASE_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
"""

# --- ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_user = User(
            email=request.form.get('email'), 
            password=request.form.get('password'), 
            business_name=request.form.get('business_name'),
            activity_sector=request.form.get('activity_sector')
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    html = """
    BASE_HEAD_HERE
    <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div class="max-w-md w-full bg-white rounded-3xl shadow-2xl shadow-indigo-100/50 p-10 border border-slate-100">
            <div class="text-center mb-8">
                <div class="bg-indigo-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-xl shadow-indigo-200">
                    <i class="fas fa-bolt text-white text-2xl"></i>
                </div>
                <h2 class="text-3xl font-bold text-slate-900">DigitagPro IA</h2>
                <p class="text-slate-500 mt-2 italic">L'intelligence artificielle au service des entreprises</p>
            </div>
            <form method="POST" class="space-y-4">
                <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 ml-1">Nom de l'entreprise</label><input name="business_name" type="text" placeholder="Ex: Digitag Corp" required class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 ml-1">Secteur d'activité</label><input name="activity_sector" type="text" placeholder="Ex: Garage, Clinique, Restaurant" required class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 ml-1">Email Pro</label><input name="email" type="email" required class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 ml-1">Mot de passe</label><input name="password" type="password" required class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl shadow-lg transition-all transform hover:-translate-y-1">Créer mon espace Pro</button>
            </form>
            <p class="text-center mt-8 text-sm text-slate-400">Déjà partenaire ? <a href="/login" class="text-indigo-600 font-bold">Se connecter</a></p>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('dashboard'))
    
    html = """
    BASE_HEAD_HERE
    <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div class="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10 border border-slate-100">
            <div class="text-center mb-8">
                <h2 class="text-3xl font-bold text-slate-900">Connexion Pro</h2>
                <p class="text-slate-500 mt-2">Bienvenue sur votre espace DigitagPro</p>
            </div>
            <form method="POST" class="space-y-4">
                <input name="email" type="email" placeholder="Email" class="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none">
                <input name="password" type="password" placeholder="Mot de passe" class="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none">
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl shadow-lg transition-all">Accéder au Dashboard</button>
            </form>
            <p class="text-center mt-8 text-sm text-slate-400">Nouvelle entreprise ? <a href="/register" class="text-indigo-600 font-bold">Inscrire votre société</a></p>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        current_user.business_name = request.form.get('business_name')
        current_user.slots = int(request.form.get('slots'))
        current_user.avg_duration = int(request.form.get('avg_duration'))
        current_user.prices_info = request.form.get('prices_info')
        db.session.commit()
        return redirect(url_for('dashboard'))

    html = """
    BASE_HEAD_HERE
    <div class="flex min-h-screen bg-slate-50 text-slate-900">
        <div class="w-72 bg-slate-900 text-white flex flex-col p-8 hidden lg:flex">
            <div class="flex items-center gap-3 mb-12 text-2xl font-bold tracking-tighter">
                <div class="bg-indigo-600 w-10 h-10 rounded-lg flex items-center justify-center"><i class="fas fa-bolt text-sm"></i></div>
                Digitag<span class="text-indigo-400">Pro</span>
            </div>
            <nav class="space-y-6 flex-1">
                <a href="#" class="flex items-center gap-4 text-indigo-400 bg-slate-800/50 p-4 rounded-2xl"><i class="fas fa-th-large"></i> Dashboard</a>
                <a href="#" class="flex items-center gap-4 text-slate-400 p-4 hover:bg-slate-800 rounded-2xl transition-all"><i class="fas fa-calendar-check"></i> Rendez-vous</a>
                <a href="#" class="flex items-center gap-4 text-slate-400 p-4 hover:bg-slate-800 rounded-2xl transition-all"><i class="fas fa-cog"></i> Paramètres IA</a>
            </nav>
            <a href="/logout" class="text-slate-500 p-4 hover:text-red-400 flex items-center gap-4 mt-auto border-t border-slate-800 pt-8"><i class="fas fa-power-off"></i> Déconnexion</a>
        </div>

        <div class="flex-1 p-8 lg:p-12 overflow-y-auto">
            <div class="flex justify-between items-start mb-12">
                <div>
                    <h1 class="text-3xl font-extrabold mb-2 tracking-tight">{{ current_user.business_name }}</h1>
                    <p class="text-slate-500 font-medium">Secteur : <span class="text-indigo-600">{{ current_user.activity_sector }}</span></p>
                </div>
                <div class="bg-indigo-50 border border-indigo-100 text-indigo-700 px-6 py-3 rounded-2xl text-sm font-bold flex items-center gap-3">
                    <div class="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-pulse"></div> Agent IA Actif
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                <div class="bg-white p-8 rounded-3xl border border-slate-100 shadow-sm shadow-slate-200/50">
                    <div class="text-slate-400 text-xs font-bold uppercase tracking-widest mb-2">Total Réservations</div>
                    <div class="text-4xl font-black">{{ current_user.appointments|length }}</div>
                </div>
                <div class="bg-white p-8 rounded-3xl border border-slate-100 shadow-sm shadow-slate-200/50">
                    <div class="text-slate-400 text-xs font-bold uppercase tracking-widest mb-2">Capacité Simultanée</div>
                    <div class="text-4xl font-black">{{ current_user.slots }}</div>
                </div>
                <div class="bg-slate-900 p-8 rounded-3xl shadow-2xl text-white">
                    <div class="text-slate-500 text-xs font-bold uppercase tracking-widest mb-2 text-indigo-300">Point d'entrée Voix</div>
                    <div class="text-xl font-mono text-indigo-400">/voice/{{ current_user.id }}</div>
                </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-2 gap-12">
                <div class="bg-white p-10 rounded-3xl border border-slate-100 shadow-sm shadow-slate-200/50">
                    <h3 class="text-xl font-black mb-8 flex items-center gap-4"><i class="fas fa-sliders text-indigo-600"></i> Configuration de l'agent</h3>
                    <form method="POST" class="space-y-6">
                        <div class="grid grid-cols-2 gap-6">
                            <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Capacité (Slots)</label><input name="slots" type="number" value="{{ current_user.slots }}" class="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-lg"></div>
                            <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Durée Moy. (min)</label><input name="avg_duration" type="number" value="{{ current_user.avg_duration }}" class="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-lg"></div>
                        </div>
                        <div><label class="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Base de connaissances & Tarifs</label><textarea name="prices_info" rows="5" class="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none font-medium">{{ current_user.prices_info }}</textarea></div>
                        <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-5 rounded-2xl transition-all shadow-xl shadow-indigo-100">Actualiser l'Agent IA</button>
                    </form>
                </div>

                <div class="bg-white p-10 rounded-3xl border border-slate-100 shadow-sm shadow-slate-200/50">
                    <h3 class="text-xl font-black mb-8 flex items-center gap-4"><i class="fas fa-history text-indigo-600"></i> Historique des appels</h3>
                    <div class="space-y-6 max-h-[500px] overflow-y-auto pr-4">
                        {% for rdv in current_user.appointments|reverse %}
                        <div class="flex items-center gap-6 p-6 hover:bg-slate-50 rounded-2xl border border-transparent hover:border-slate-100 transition-all group">
                            <div class="bg-indigo-50 w-14 h-14 rounded-2xl flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-all"><i class="fas fa-phone-volume text-xl"></i></div>
                            <div class="flex-1">
                                <div class="font-extrabold text-slate-900 text-lg mb-1">{{ rdv.details }}</div>
                                <div class="text-sm text-slate-400 font-bold flex items-center gap-2"><i class="fas fa-clock text-xs"></i> {{ rdv.date_str }}</div>
                            </div>
                        </div>
                        {% else %}
                        <div class="text-center py-20 text-slate-300"><i class="fas fa-ghost text-5xl mb-6 opacity-20"></i><p class="font-bold text-lg">En attente du premier appel...</p></div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- IA DIGITAGPRO (VOICE) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    
    # Prompt plus générique pour s'adapter à tous les secteurs
    system_prompt = f"""
    Tu es l'assistant IA de l'entreprise '{commercant.business_name}' (Secteur: {commercant.activity_sector}). 
    Capacité: {commercant.slots} places. Durée moyenne de prestation: {commercant.avg_duration}min.
    Infos/Tarifs: {commercant.prices_info}.
    Sois bref et professionnel. Si une réservation est validée, commence par CONFIRMATION_RDV: [Détails].
    """

    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {commercant.business_name}, comment puis-je vous aider ?"
    else:
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}])
        raw = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in raw:
            parts = raw.split("CONFIRMATION_RDV:")
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=parts[1].strip(), user_id=commercant.id)
            db.session.add(new_rdv)
            db.session.commit()
            ai_response = parts[0] if parts[0] else "C'est enregistré, merci."
        else: ai_response = raw

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)