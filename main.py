from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hairforme_secret_key_2024'

# Configuration SQL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///saas_database.db')
if database_url.startswith("postgres://"):
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
    slots = db.Column(db.Integer, default=1)
    avg_duration = db.Column(db.Integer, default=30)
    prices_info = db.Column(db.Text, default="Coupe Homme: 25€\nCoupe Femme: 45€")
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

# --- TEMPLATES CSS COMMUNS ---
BASE_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>body { font-family: 'Inter', sans-serif; }</style>
"""

# --- ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_user = User(email=request.form.get('email'), password=request.form.get('password'), business_name=request.form.get('business_name'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(f"""
    {BASE_HEAD}
    <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div class="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
            <div class="text-center mb-8">
                <div class="bg-indigo-600 w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-200">
                    <i class="fas fa-robot text-white text-2xl"></i>
                </div>
                <h2 class="text-3xl font-bold text-slate-800">HairForMe AI</h2>
                <p class="text-slate-500 mt-2">Rejoignez le futur de la gestion de salon</p>
            </div>
            <form method="POST" class="space-y-4">
                <div><label class="block text-sm font-semibold text-slate-700">Nom du Salon</label><input name="business_name" type="text" required class="w-full mt-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"></div>
                <div><label class="block text-sm font-semibold text-slate-700">Email Professionnel</label><input name="email" type="email" required class="w-full mt-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"></div>
                <div><label class="block text-sm font-semibold text-slate-700">Mot de passe</label><input name="password" type="password" required class="w-full mt-1 p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"></div>
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-lg shadow-lg shadow-indigo-100 transition-all">Créer mon compte</button>
            </form>
            <p class="text-center mt-6 text-sm text-slate-500">Déjà inscrit ? <a href="/login" class="text-indigo-600 font-semibold">Connectez-vous</a></p>
        </div>
    </div>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template_string(f"""
    {BASE_HEAD}
    <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div class="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
            <div class="text-center mb-8">
                <h2 class="text-3xl font-bold text-slate-800 font-bold">Connexion</h2>
                <p class="text-slate-500 mt-2">Accédez à votre assistant IA</p>
            </div>
            <form method="POST" class="space-y-4">
                <input name="email" type="email" placeholder="Email" class="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                <input name="password" type="password" placeholder="Mot de passe" class="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-lg shadow-lg transition-all">Entrer</button>
            </form>
            <p class="text-center mt-6 text-sm text-slate-500">Pas encore client ? <a href="/register" class="text-indigo-600 font-semibold">Inscrivez votre salon</a></p>
        </div>
    </div>
    """)

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

    return render_template_string(f"""
    {BASE_HEAD}
    <div class="flex min-h-screen bg-slate-50">
        <div class="w-64 bg-slate-900 text-white flex flex-col p-6 hidden md:flex">
            <div class="flex items-center gap-3 mb-10 text-xl font-bold tracking-tight">
                <i class="fas fa-robot text-indigo-400"></i> HairForMe <span class="text-indigo-400">AI</span>
            </div>
            <nav class="space-y-4 flex-1">
                <a href="#" class="flex items-center gap-3 text-indigo-400 bg-slate-800 p-3 rounded-lg"><i class="fas fa-home"></i> Dashboard</a>
                <a href="#" class="flex items-center gap-3 text-slate-400 p-3 hover:bg-slate-800 rounded-lg transition-all"><i class="fas fa-calendar"></i> Agenda</a>
                <a href="#" class="flex items-center gap-3 text-slate-400 p-3 hover:bg-slate-800 rounded-lg transition-all"><i class="fas fa-chart-line"></i> Analytics</a>
            </nav>
            <a href="/logout" class="text-slate-400 p-3 hover:text-red-400 flex items-center gap-3 mt-auto"><i class="fas fa-sign-out-alt"></i> Déconnexion</a>
        </div>

        <div class="flex-1 p-6 md:p-10 overflow-y-auto">
            <div class="flex justify-between items-center mb-10">
                <div>
                    <h1 class="text-2xl font-bold text-slate-800">Bonjour, {{ current_user.business_name }} 👋</h1>
                    <p class="text-slate-500">Gérez votre assistant IA et vos rendez-vous.</p>
                </div>
                <div class="bg-emerald-100 text-emerald-700 px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2">
                    <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span> Assistant En Ligne
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
                    <div class="text-slate-500 text-sm mb-1 font-semibold">Rendez-vous</div>
                    <div class="text-3xl font-bold text-slate-800">{{ current_user.appointments|length }}</div>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
                    <div class="text-slate-500 text-sm mb-1 font-semibold">Places (Fauteuils)</div>
                    <div class="text-3xl font-bold text-slate-800">{{ current_user.slots }}</div>
                </div>
                <div class="bg-indigo-600 p-6 rounded-2xl shadow-lg shadow-indigo-100 text-white">
                    <div class="text-indigo-100 text-sm mb-1 font-semibold">ID Twilio</div>
                    <div class="text-xl font-mono">/voice/{{ current_user.id }}</div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <div class="bg-white p-8 rounded-2xl border border-slate-100 shadow-sm">
                    <h3 class="text-xl font-bold text-slate-800 mb-6 flex items-center gap-3"><i class="fas fa-sliders-h text-indigo-600"></i> Configuration IA</h3>
                    <form method="POST" class="space-y-6">
                        <div><label class="block text-sm font-bold text-slate-700 mb-2">Nom du Salon</label><input name="business_name" type="text" value="{{ current_user.business_name }}" class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                        <div class="grid grid-cols-2 gap-4">
                            <div><label class="block text-sm font-bold text-slate-700 mb-2">Places</label><input name="slots" type="number" value="{{ current_user.slots }}" class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                            <div><label class="block text-sm font-bold text-slate-700 mb-2">Durée (min)</label><input name="avg_duration" type="number" value="{{ current_user.avg_duration }}" class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"></div>
                        </div>
                        <div><label class="block text-sm font-bold text-slate-700 mb-2">Base de connaissances (Tarifs/Infos)</label><textarea name="prices_info" rows="4" class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none">{{ current_user.prices_info }}</textarea></div>
                        <button type="submit" class="w-full bg-slate-900 hover:bg-black text-white font-bold py-4 rounded-xl transition-all shadow-lg">Enregistrer les réglages</button>
                    </form>
                </div>

                <div class="bg-white p-8 rounded-2xl border border-slate-100 shadow-sm">
                    <h3 class="text-xl font-bold text-slate-800 mb-6 flex items-center gap-3"><i class="fas fa-list-ul text-indigo-600"></i> Journal des appels</h3>
                    <div class="space-y-4">
                        {% for rdv in current_user.appointments|reverse %}
                        <div class="flex items-center gap-4 p-4 hover:bg-slate-50 rounded-xl border border-transparent hover:border-slate-100 transition-all">
                            <div class="bg-indigo-50 w-12 h-12 rounded-full flex items-center justify-center text-indigo-600"><i class="fas fa-phone-alt"></i></div>
                            <div class="flex-1">
                                <div class="font-bold text-slate-800">{{ rdv.details }}</div>
                                <div class="text-sm text-slate-500">{{ rdv.date_str }}</div>
                            </div>
                        </div>
                        {% else %}
                        <div class="text-center py-20 text-slate-400"><i class="fas fa-calendar-times text-4xl mb-4"></i><p>Aucun rendez-vous noté pour le moment.</p></div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- IA TWILIO (ID_DU_CLIENT) ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    system_prompt = f"Tu es l'assistant de {commercant.business_name}. Places: {commercant.slots}. Durée: {commercant.avg_duration}min. Tarifs: {commercant.prices_info}. Sois bref (15 mots max). Si RDV validé, commence par CONFIRMATION_RDV: [Détail]."
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
            ai_response = parts[0] if parts[0] else "C'est noté pour votre rendez-vous."
        else: ai_response = raw
    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)