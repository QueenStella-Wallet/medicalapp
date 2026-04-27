from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import csv
import io

app = Flask(__name__)
app.secret_key = "medical_secret_key_2026_pro"

# --- CONFIGURATION DE LA BASE DE DONNÉES ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'clinique_privee.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODÈLE DE DONNÉES ---
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    poids = db.Column(db.Float)   # kg
    taille = db.Column(db.Float)  # m
    imc = db.Column(db.Float)
    statut_poids = db.Column(db.String(50))
    glycemie = db.Column(db.Float)
    contexte = db.Column(db.String(20))
    temp = db.Column(db.Float)
    tension = db.Column(db.String(15))
    groupe = db.Column(db.String(5))
    electro = db.Column(db.String(5))
    diagnostic = db.Column(db.String(50))
    date = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))

# Création automatique de la table au lancement
with app.app_context():
    db.create_all()

# --- LOGIQUE MÉDICALE ---
def analyser_patient(p):
    """Calcule l'IMC et détermine si le cas est une urgence."""
    # 1. Calcul IMC
    imc_val = round(p.poids / (p.taille * p.taille), 2)
    if imc_val < 18.5: statut = "Maigre"
    elif imc_val < 25: statut = "Normal"
    elif imc_val < 30: statut = "Surpoids"
    else: statut = "Obèse"
    
    # 2. Détermination de l'Urgence (Paramètres personnalisables)
    etat = "Normal"
    if p.temp > 38.5 or p.temp < 35.5: etat = "Urgence"
    if p.electro == "SS": etat = "Urgence"
    if p.contexte == "ajeun" and (p.glycemie > 1.26 or p.glycemie < 0.7): etat = "Urgence"
    
    return imc_val, statut, etat

# --- ROUTES FLASK ---

@app.route('/')
def index():
    patients = Patient.query.order_by(Patient.id.desc()).all()
    # Statistiques pour le graphique Chart.js
    stats = {'Maigre': 0, 'Normal': 0, 'Surpoids': 0, 'Obese': 0}
    for p in patients:
        key = 'Obese' if p.statut_poids == 'Obèse' else p.statut_poids
        if key in stats: stats[key] += 1
    
    return render_template('index.html', mode="liste", patients=patients, stats=stats)

@app.route('/ajouter', methods=['GET', 'POST'])
def ajouter():
    if request.method == 'POST':
        try:
            nuevo = Patient(
                nom=request.form['nom'].upper(),
                prenom=request.form['prenom'].capitalize(),
                age=int(request.form['age']),
                poids=float(request.form['poids']),
                taille=float(request.form['taille']),
                glycemie=float(request.form['glycemie']),
                contexte=request.form['contexte'],
                temp=float(request.form['temp']),
                tension=request.form['tension'],
                groupe=request.form['groupe'],
                electro=request.form['electro']
            )
            # Calculs automatiques avant insertion
            nuevo.imc, nuevo.statut_poids, nuevo.diagnostic = analyser_patient(nuevo)
            
            db.session.add(nuevo)
            db.session.commit()
            flash("Patient enregistré avec succès !", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout : {str(e)}", "danger")
            
    return render_template('index.html', mode="formulaire")

@app.route('/supprimer/<int:id>')
def supprimer(id):
    p = Patient.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash("Dossier supprimé.", "info")
    return redirect(url_for('index'))

@app.route('/exporter')
def exporter():
    patients = Patient.query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    # En-têtes du fichier Excel/CSV
    cw.writerow(['ID', 'Nom', 'Prénom', 'Âge', 'IMC', 'Statut Poids', 'Urgence', 'Date Enregistrement'])
    
    for p in patients:
        cw.writerow([p.id, p.nom, p.prenom, p.age, p.imc, p.statut_poids, p.diagnostic, p.date])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=base_patients.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    app.run(debug=True)