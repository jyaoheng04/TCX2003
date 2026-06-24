from flask import Flask, render_template, redirect
from dotenv import load_dotenv
import os
import mysql.connector

from routes.doctor import doctor_bp
from routes.nurse import nurse_bp

load_dotenv()

app = Flask(__name__)

# SECRET KEY
app.secret_key = os.getenv("SECRET_KEY")
# Register blueprint
app.register_blueprint(doctor_bp)
app.register_blueprint(nurse_bp)

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
    # return render_template('auth/login.html')
    return redirect('/doctor/dashboard')

# PATIENT
@app.route('/patient/dashboard')
def patient():
    return render_template('patient/dashboard.html', role="patient",active_page="dashboard")

@app.route('/patient/appointments')
def patient_appointments():
    return render_template('patient/appointments.html', role="patient",active_page="appointments")

@app.route('/patient/create')
def patient_create():
    return render_template('patient/create.html', role="patient",active_page="appointments")

@app.route('/patient/records')
def patient_records():
    return render_template('patient/records.html', role="patient",active_page="records")


@app.route('/patient/profile')
def patient_profile():
    return render_template('patient/profile.html', role="patient",active_page="profile")

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


if __name__ == '__main__':
    app.run(debug=True)