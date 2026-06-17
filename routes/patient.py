from flask import Blueprint
from flask import render_template, request, flash, redirect
from datetime import datetime
import mysql.connector
import os

patient_bp = Blueprint(
    "patient",
    __name__,
    url_prefix="/patient"
)

def get_db():

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

@patient_bp.route('/appointments')
def appointments():

    db = get_db()

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
    db.close()

    return render_template(
        'patient/appointments.html',
        role="patient",
        active_page="appointments",
        appointments=appointments
    )

@patient_bp.route('/create', methods=['GET', 'POST'])
def create():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT staff_id, full_name
        FROM medical_staff
        WHERE role='doctor'
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

        try:

            appointment_datetime = datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M"
            )

            if appointment_datetime <= datetime.now():
                errors.append(
                    "Appointment must be in the future."
                )

        except ValueError:
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

        flash(
            "Appointment booked successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    cursor.close()
    db.close()

    return render_template(
        'patient/create.html',
        role="patient",
        active_page="appointments",
        doctors=doctors
    )

