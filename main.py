from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_ia_master_key_2026'

# Configuration SQL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db')
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
    activity_sector = db.Column(db.String(100), default="Services")
    is_admin = db.Column(db.Boolean, default=False)  # NOUVEAU : Pour ton accès Maître
    slots = db.Column(db.Integer, default=1)
    avg_duration = db.Column(db.Integer, default=30)
    prices_info = db.Column(db.Text, default="Services standards")
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

# --- DESIGN ---
BASE_HEAD = """
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
"""

# --- ROUTE MASTER ADMIN AVEC CONTRÔLE TOTAL ---
@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Accès refusé", 403
    
    # Action pour supprimer un utilisateur
    if request.args.get('delete_user'):
        u_to_del = User.query.get(request.args.get('delete_user'))
        if u_to_del and not u_to_del.is_admin:
            db.session.delete(u_to_del)
            db.session.commit()
            return redirect(url_for('master_admin'))

    # Action pour mettre à jour les infos d'un client en direct
    if request.method == 'POST' and 'update_client_id' in request.form:
        client_id = request.form.get('update_client_id')
        target_user = User.query.get(client_id)
        if target_user:
            target_user.business_name = request.form.get('b_name')
            target_user.prices_info = request.form.get('p_info')
            db.session.commit()
            return redirect(url_for('master_admin'))

    users = User.query.all()
    all_rdv = Appointment.query.order_by(Appointment.id.desc()).all()
    
    html = """
    BASE_HEAD_HERE
    <div class="min-h-screen bg-[#0a0c14] text-white p-8">
        <div class="flex justify-between items-center mb-12">
            <h1 class="text-4xl font-black bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent italic">DIGITAGPRO COMMAND CENTER</h1>
            <a href="/logout" class="bg-slate-800 px-6 py-2 rounded-full text-sm hover:bg-red-600 transition">Quitter la passerelle</a>
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
            <div class="lg:col-span-2 space-y-8">
                <h2 class="text-xl font-bold text-slate-400 flex items-center gap-3"><i class="fas fa-robot"></i> Agents IA en Service ({{ users|length }})</h2>
                
                {% for u in users %}
                <div class="bg-[#111420] border border-slate-800 p-8 rounded-[2rem] shadow-2xl">
                    <form method="POST" class="space-y-4">
                        <input type="hidden" name="update_client_id" value="{{ u.id }}">
                        
                        <div class="flex justify-between items-start">
                            <div class="w-full">
                                <label class="text-[10px] text-indigo-400 font-bold uppercase tracking-widest">Nom de l'Entreprise (ID: {{ u.id }})</label>
                                <input name="b_name" value="{{ u.business_name }}" class="bg-transparent text-2xl font-black w-full focus:outline-none focus:border-b border-indigo-500 mb-4">
                            </div>
                            <div class="flex gap-2">
                                <a href="/voice/{{ u.id }}" class="p-3 bg-green-500/10 text-green-500 rounded-xl hover:bg-green-500 hover:text-white transition"><i class="fas fa-phone"></i></a>
                                {% if not u.is_admin %}
                                <a href="/master-admin?delete_user={{ u.id }}" onclick="return confirm('Supprimer ce client ?')" class="p-3 bg-red-500/10 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition"><i class="fas fa-trash"></i></a>
                                {% endif %}
                            </div>
                        </div>

                        <div>
                            <label class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Configuration de l'IA (Prompt & Tarifs)</label>
                            <textarea name="p_info" rows="3" class="w-full bg-[#0a0c14] border border-slate-800 rounded-2xl p-4 mt-2 text-sm text-slate-300 focus:border-indigo-500 outline-none">{{ u.prices_info }}</textarea>
                        </div>

                        <button class="w-full bg-indigo-600/10 border border-indigo-600/50 text-indigo-400 py-3 rounded-2xl font-bold hover:bg-indigo-600 hover:text-white transition">Appliquer les modifications</button>
                    </form>
                </div>
                {% endfor %}
            </div>

            <div>
                <h2 class="text-xl font-bold text-slate-400 mb-8 flex items-center gap-3"><i class="fas fa-broadcast-tower"></i> Flux d'appels live</h2>
                <div class="space-y-4 max-h-[1000px] overflow-y-auto pr-2">
                    {% for rdv in all_rdv %}
                    <div class="p-5 bg-[#111420] border-l-4 border-indigo-500 rounded-2xl">
                        <div class="flex justify-between text-[10px] mb-2 font-bold uppercase">
                            <span class="text-indigo-400">{{ rdv.owner.business_name }}</span>
                            <span class="text-slate-600">{{ rdv.date_str }}</span>
                        </div>
                        <p class="text-sm text-slate-300 leading-relaxed">{{ rdv.details }}</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """.replace("BASE_HEAD_HERE", BASE_HEAD)
    return render_template_string(html, users=users, all_rdv=all_rdv)

# --- IA VOICE ---
@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    commercant = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    user_input = request.values.get('SpeechResult')
    system_prompt = f"Tu es l'assistant IA de '{commercant.business_name}'. Secteur: {commercant.activity_sector}. Tarifs/Infos: {commercant.prices_info}. Si RDV validé, commence par CONFIRMATION_RDV: [Détail]."
    
    if not user_input:
        ai_response = f"Bonjour, bienvenue chez {commercant.business_name}, comment puis-je vous aider ?"
    else:
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}])
        raw = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in raw:
            new_rdv = Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=raw.split("CONFIRMATION_RDV:")[1].strip(), user_id=commercant.id)
            db.session.add(new_rdv); db.session.commit()
            ai_response = raw.split("CONFIRMATION_RDV:")[0]
        else: ai_response = raw
        
    gather = Gather(input='speech', language='fr-FR', timeout=1, speechTimeout='auto')
    gather.say(ai_response, language='fr-FR')
    resp.append(gather)
    resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
@app.route('/devenir-master-vite')
def dev_master():
    user = User.query.filter_by(email='romanlayani@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "Tu es maintenant le Maitre du systeme !"
    return "Utilisateur non trouve"