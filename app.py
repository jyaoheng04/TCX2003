from flask import Blueprint, Flask, render_template, redirect
from flask import Flask, render_template, redirect, request, flash
from dotenv import load_dotenv
from datetime import datetime
import os
import mysql.connector

from routes.auth import auth
from routes.admin import admin
from routes.patient import patient_bp


load_dotenv()

app = Flask(__name__)
app.register_blueprint(auth)
app.register_blueprint(admin)

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

@app.route('/Register_Staff')
def register_staff():
    return render_template('auth/Register_MedicalStaff.html')

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

@app.route('/logout')
def logout():
    return redirect('/')

app.register_blueprint(patient_bp)

if __name__ == '__main__':
    app.run(debug=True)