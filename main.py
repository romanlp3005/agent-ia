from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ton_secret_saas_ultra_sur'

# Configuration de la base de données (SQL)
# Si on est sur Render, il prendra DATABASE_URL, sinon une base locale sqlite
database_url = os.environ.get('DATABASE_URL', 'sqlite:///saas_database.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- MODÈLES DE DONNÉES ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    # Paramètres Scalables
    slots = db.Column(db.Integer, default=1)  # Nb de coiffeurs/places
    avg_duration = db.Column(db.Integer, default=30)  # Durée en min
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

# Création des tables au démarrage
with app.app_context():
    db.create_all()

# --- ROUTES AUTHENTIFICATION ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email déjà utilisé !"
        
        new_user = User(
            email=email,
            password=request.form.get('password'), # En prod, utilise werkzeug.security
            business_name=request.form.get('business_name')
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return '''
    <h2>Inscription Partenaire HairForMe</h2>
    <form method="POST">
        <input name="email" placeholder="Email" required><br>
        <input name="business_name" placeholder="Nom du Salon" required><br>
        <input name="password" type="password" placeholder="Mot de passe" required><br>
        <button type="submit">Créer mon espace SaaS</button>
    </form>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('dashboard'))
    return '<h2>Connexion</h2><form method="POST"><input name="email"><input name="password" type="password"><button type="submit">Entrer</button></form>'

# --- DASHBOARD SCALABLE ---

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

    return render_template_string("""
    <h1>Tableau de bord de {{ current_user.business_name }}</h1>
    <p>Votre lien Twilio : <b>https://{{ request.host }}/voice/{{ current_user.id }}</b></p>
    
    <div style="display:flex; gap:20px;">
        <form method="POST" style="flex:1; border:1px solid #ccc; padding:20px;">
            <h3>Réglages Business</h3>
            Nombre de places (fauteuils) : <input type="number" name="slots" value="{{ current_user.slots }}"><br><br>
            Durée moyenne RDV (min) : <input type="number" name="avg_duration" value="{{ current_user.avg_duration }}"><br><br>
            Tarifs et Infos : <textarea name="prices_info" rows="5" style="width:100%">{{ current_user.prices_info }}</textarea><br><br>
            <button type="submit">Sauvegarder</button>
        </form>

        <div style="flex:1; border:1px solid #ccc; padding:20px;">
            <h3>Derniers RDV</h3>
            {% for rdv in current_user.appointments|reverse %}
                <p><b>{{ rdv.date_str }}</b> : {{ rdv.details }}</p>
            {% endfor %}
        </div>
    </div>
    <br><a href="/logout">Se déconnecter</a>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- IA VOCALE (MULTI-CLIENT) ---

@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    
    system_prompt = f"""
    Tu es l'IA de {commercant.business_name}. 
    Capacité: {commercant.slots} places. Durée moyenne: {commercant.avg_duration}min.
    Tarifs: {commercant.prices_info}.
    Sois bref (15 mots max). Si RDV validé, commence par CONFIRMATION_RDV: [Détails].
    """

    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {commercant.business_name}, je vous écoute ?"
    else:
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
        )
        raw = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in raw:
            parts = raw.split("CONFIRMATION_RDV:")
            new_rdv = Appointment(
                date_str=datetime.now().strftime("%d/%m %H:%M"),
                details=parts[1].strip(),
                user_id=commercant.id
            )
            db.session.add(new_rdv)
            db.session.commit()
            ai_response = parts[0] if parts[0] else "C'est noté !"
        else:
            ai_response = raw

    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)