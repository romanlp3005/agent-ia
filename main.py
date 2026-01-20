from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digitagpro_2026'
db_url = os.environ.get('DATABASE_URL', 'sqlite:///digitagpro.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    prices_info = db.Column(db.Text, default="Services standards")
    appointments = db.relationship('Appointment', backref='owner', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(50))
    details = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

with app.app_context(): db.create_all()

# --- DESIGN UNIQUE ---
LAYOUT_START = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<body class="bg-[#020617] text-white font-sans flex">
    <div class="w-72 h-screen bg-[#020617] border-r border-slate-800 p-6 flex flex-col fixed">
        <div class="text-xl font-black text-indigo-500 mb-10">DIGITAGPRO</div>
        <nav class="flex-1 space-y-2">
            <a href="/master-admin" class="flex items-center gap-3 p-4 rounded-xl hover:bg-slate-800 transition"><i class="fas fa-th-large"></i> Dashboard</a>
            <a href="/master-clients" class="flex items-center gap-3 p-4 rounded-xl hover:bg-slate-800 transition"><i class="fas fa-users"></i> Clients</a>
            <a href="/master-logs" class="flex items-center gap-3 p-4 rounded-xl hover:bg-slate-800 transition"><i class="fas fa-phone"></i> Logs</a>
        </nav>
        <a href="/logout" class="text-red-400 text-xs font-bold uppercase p-4">Déconnexion</a>
    </div>
    <main class="ml-72 flex-1 p-12">
"""
LAYOUT_END = "</main></body>"

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and u.password == request.form.get('password'):
            login_user(u); return redirect(url_for('master_admin' if u.is_admin else 'dashboard'))
    return render_template_string("<body class='bg-slate-950 flex items-center justify-center h-screen font-sans'><form method='POST' class='bg-slate-900 p-10 rounded-3xl border border-slate-800 w-96'><h2 class='text-2xl font-bold text-white mb-6 text-center italic text-indigo-500'>DIGITAGPRO</h2><input name='email' placeholder='Email' class='w-full p-4 bg-slate-950 border border-slate-800 rounded-xl mb-4 text-white'><input name='password' type='password' placeholder='Pass' class='w-full p-4 bg-slate-950 border border-slate-800 rounded-xl mb-6 text-white'><button class='w-full bg-indigo-600 p-4 rounded-xl font-bold text-white'>Connexion</button></form></body>")

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/master-admin', methods=['GET', 'POST'])
@login_required
def master_admin():
    if not current_user.is_admin: return "Refusé", 403
    if request.method == 'POST':
        u = User.query.get(request.form.get('id'))
        if u: u.business_name = request.form.get('n'); u.prices_info = request.form.get('p'); db.session.commit()
    users = User.query.all()
    content = "{% for u in users %}<div class='bg-slate-900 p-6 rounded-2xl mb-4 border border-slate-800'><form method='POST' class='flex justify-between items-center'><input type='hidden' name='id' value='{{u.id}}'><div class='flex-1 mr-4'><input name='n' value='{{u.business_name}}' class='bg-transparent text-xl font-bold mb-2 w-full focus:text-indigo-400 focus:outline-none'><textarea name='p' class='w-full bg-slate-950 p-4 rounded-xl text-sm border border-slate-800'>{{u.prices_info}}</textarea></div><button class='bg-indigo-600 px-4 py-2 rounded-lg font-bold text-xs'>SAUVER</button></form></div>{% endfor %}"
    return render_template_string(LAYOUT_START + content + LAYOUT_END, users=users)

@app.route('/master-clients')
@login_required
def master_clients():
    users = User.query.all()
    content = "<div class='bg-slate-900 rounded-2xl p-6 border border-slate-800'><h2 class='text-xl font-bold mb-6'>Liste des Clients</h2>{% for u in users %}<div class='flex justify-between p-4 border-b border-slate-800 last:border-0'><span>{{u.business_name}}</span><span class='text-slate-500'>{{u.email}}</span></div>{% endfor %}</div>"
    return render_template_string(LAYOUT_START + content + LAYOUT_END, users=users)

@app.route('/master-logs')
@login_required
def master_logs():
    logs = Appointment.query.order_by(Appointment.id.desc()).all()
    content = "<h2 class='text-xl font-bold mb-6'>Historique des Appels</h2>{% for r in logs %}<div class='bg-slate-900 p-4 rounded-xl border border-slate-800 mb-3'><p class='text-[10px] text-indigo-400 font-bold'>{{r.owner.business_name}}</p><p class='text-sm'>{{r.details}}</p><p class='text-[10px] text-slate-600 mt-2'>{{r.date_str}}</p></div>{% endfor %}"
    return render_template_string(LAYOUT_START + content + LAYOUT_END, logs=logs)

@app.route('/devenir-master-vite')
def dev_master():
    u = User.query.filter_by(email='romanlayani@gmail.com').first()
    if u: u.is_admin = True; db.session.commit(); return "OK MASTER"
    return "USER NOT FOUND"

@app.route("/voice/<int:user_id>", methods=['POST'])
def voice(user_id):
    c = User.query.get_or_404(user_id)
    resp = VoiceResponse()
    txt = request.values.get('SpeechResult')
    if not txt: ai = f"Bonjour, bienvenue chez {c.business_name}, comment puis-je vous aider ?"
    else:
        chat = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": f"Tu es l'assistant de {c.business_name}. Tarifs: {c.prices_info}. Si RDV validé, CONFIRMATION_RDV: [Détail]"}, {"role": "user", "content": txt}])
        ai = chat.choices[0].message.content
        if "CONFIRMATION_RDV:" in ai:
            db.session.add(Appointment(date_str=datetime.now().strftime("%d/%m %H:%M"), details=ai.split("CONFIRMATION_RDV:")[1].strip(), user_id=c.id)); db.session.commit()
            ai = ai.split("CONFIRMATION_RDV:")[0]
    g = Gather(input='speech', language='fr-FR', timeout=1); g.say(ai, language='fr-FR'); resp.append(g); resp.redirect(f'/voice/{user_id}')
    return str(resp)

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)