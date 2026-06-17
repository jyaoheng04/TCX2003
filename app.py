from flask import Flask, render_template, redirect, request, flash
from dotenv import load_dotenv
from datetime import datetime
import os
import mysql.connector

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

@app.route('/patient/appointments')
def patient_appointments():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            a.appointment_id,
            a.appointment_type,
            a.reason,
            a.appointment_date,
            a.status,
            ms.full_name AS doctor_name
        FROM appointment a
        JOIN medical_staff ms
            ON a.doctor_id = ms.staff_id
        ORDER BY a.appointment_date ASC
    """)

    appointments = cursor.fetchall()

    cursor.close()

    return render_template(
        'patient/appointments.html',
        role="patient",
        active_page="appointments",
        appointments=appointments
    )

@app.route('/patient/create', methods=['GET', 'POST'])
def patient_create():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT staff_id, full_name
        FROM medical_staff
        WHERE role = 'doctor'
    """)
    doctors = cursor.fetchall()

    if request.method == 'POST':

        doctor_id = request.form.get('doctor_id')
        appointment_type = request.form.get('appointment_type')
        date = request.form.get('date')
        time = request.form.get('time')
        reason = request.form.get('reason')

        errors = []

        if not doctor_id:
            errors.append("Doctor is required.")

        if not appointment_type:
            errors.append("Appointment type is required.")

        if not date:
            errors.append("Date is required.")

        if not time:
            errors.append("Time is required.")

        if not reason:
            errors.append("Reason is required.")

        if len(reason) > 255:
            errors.append("Reason cannot exceed 255 characters.")

        try:
            appointment_datetime = datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M"
            )

            if appointment_datetime <= datetime.now():
                errors.append(
                    "Appointment must be in the future."
                )

        except:
            errors.append("Invalid date/time.")

        if errors:

            for error in errors:
                flash(error, "error")

            return render_template(
                'patient/create.html',
                role="patient",
                active_page="appointments",
                doctors=doctors
            )

        patient_id = 1

        cursor.execute("""
            INSERT INTO appointment
            (
                patient_id,
                doctor_id,
                appointment_type,
                reason,
                appointment_date,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,'booked')
        """, (
            patient_id,
            doctor_id,
            appointment_type,
            reason,
            appointment_datetime
        ))

        db.commit()

        cursor.close()

        flash(
            "Appointment booked successfully.",
            "success"
        )

        return redirect('/patient/appointments')

    cursor.close()

    return render_template(
        'patient/create.html',
        role="patient",
        active_page="appointments",
        doctors=doctors
    )

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