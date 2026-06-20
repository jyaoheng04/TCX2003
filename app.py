from flask import Flask, render_template, redirect, request, flash
from dotenv import load_dotenv
from datetime import datetime
import os
import mysql.connector

from routes.patient import patient_bp


load_dotenv()

app = Flask(__name__)

# SECRET KEY
app.secret_key = os.getenv("SECRET_KEY")

# DB CONNECTION
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

@app.route('/')
def login():
    return render_template('auth/login.html')

# DOCTOR
@app.route('/doctor/dashboard')
def doctor():
    return render_template('doctor/dashboard.html', role="doctor", active_page="dashboard")

@app.route('/doctor/consultations')
def doctor_consultations():
    return render_template('doctor/consultation.html', role="doctor", active_page="consultations")


@app.route('/doctor/create')
def doctor_create():
    return render_template('doctor/create.html', role="doctor", active_page="create")


@app.route('/doctor/edit/<int:id>')
def doctor_edit(id):
    return render_template('doctor/edit.html', role="doctor", id=id, active_page="edit")

# NURSE
@app.route('/nurse/dashboard')
def nurse():
    return render_template('nurse/dashboard.html', role="nurse",active_page="dashboard")

@app.route('/nurse/patients')
def nurse_patients():
    return render_template('nurse/patients.html', role="nurse",active_page="patients")


@app.route('/nurse/clinic_op')
def nurse_wards():
    return render_template('nurse/clinic_op.html', role="nurse",active_page="Clinic Operation")


@app.route('/nurse/medication')
def nurse_medication():
    return render_template('nurse/medication.html', role="nurse",active_page="medication")

# PATIENT
@app.route('/patient/dashboard')
def patient():
    return render_template('patient/dashboard.html', role="patient",active_page="dashboard")

# ADMIN
@app.route('/admin/dashboard')
def admin():
    return render_template('admin/dashboard.html', role="admin",active_page="dashboard")

@app.route('/admin/users')
def admin_users():
    return render_template('admin/users.html', role="admin",active_page="users")

@app.route("/admin/users/create")
def admin_user():
    return render_template("admin/user_create.html", role="admin", active_page="users")

@app.route("/admin/users/edit/<int:id>")
def admin_user_edit(id):
    return render_template("admin/user_edit.html", role="admin", active_page="users", id=id)

@app.route('/admin/security')
def admin_security():
    return render_template('admin/security.html', role="admin",active_page="security")


@app.route('/admin/system')
def admin_system():
    return render_template('admin/system.html', role="admin",active_page="system")


@app.route('/admin/logs')
def admin_logs():
    return render_template('admin/logs.html', role="admin",active_page="logs")

@app.route('/logout')
def logout():
    return redirect('/')

app.register_blueprint(patient_bp)

if __name__ == '__main__':
    app.run(debug=True)