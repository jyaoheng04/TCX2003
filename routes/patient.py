from flask import Blueprint, render_template, request, flash, redirect, get_flashed_messages
from datetime import datetime, timedelta
import mysql.connector
import os

patient_bp = Blueprint(
    "patient",
    __name__,
    url_prefix="/patient"
)


# ======================
# DATABASE CONNECTION
# ======================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )


# ======================
# VIEW APPOINTMENTS
# ======================
@patient_bp.route('/appointments')
def appointments():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # temporary hardcoded patient
    patient_id = 1

    # auto-complete appointments whose datetime has passed
    cursor.execute("""
        UPDATE appointment
        SET status = 'completed'
        WHERE appointment_date <= NOW()
        AND status = 'booked'
    """)

    db.commit()

    # fetch appointments
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
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date ASC
    """, (patient_id,))

    appointments = cursor.fetchall()

    # determine if appointment can be modified
    # (cancel + reschedule allowed only >24 hrs)
    for appointment in appointments:

        appointment["can_modify"] = False

        if appointment["status"] == "booked":

            time_difference = (
                appointment["appointment_date"] - datetime.now()
            )

            if time_difference >= timedelta(hours=24):
                appointment["can_modify"] = True

    cursor.close()
    db.close()

    return render_template(
        'patient/appointments.html',
        role="patient",
        active_page="appointments",
        appointments=appointments
    )


# ======================
# CREATE APPOINTMENT
# ======================
@patient_bp.route('/create', methods=['GET', 'POST'])
def create():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # fetch doctors
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

        # validation errors
        if errors:

            for error in errors:
                flash(error, "error")

            cursor.close()
            db.close()

            return render_template(
                'patient/create.html',
                role="patient",
                active_page="appointments",
                doctors=doctors
            )

        # temporary hardcoded patient
        patient_id = 1

        # insert appointment
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
            (%s, %s, %s, %s, %s, 'booked')
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

    # clear old flash messages
    get_flashed_messages()

    return render_template(
        'patient/create.html',
        role="patient",
        active_page="appointments",
        doctors=doctors
    )


# ======================
# RESCHEDULE APPOINTMENT
# ======================
@patient_bp.route('/edit/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    patient_id = 1

    # verify ownership
    cursor.execute("""
        SELECT *
        FROM appointment
        WHERE appointment_id = %s
        AND patient_id = %s
    """, (appointment_id, patient_id))

    appointment = cursor.fetchone()

    if not appointment:

        flash("Appointment not found.", "error")

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    # check 24 hour rule
    time_difference = (
        appointment["appointment_date"] - datetime.now()
    )

    if time_difference < timedelta(hours=24):

        flash(
            "Appointments cannot be rescheduled less than 24 hours before appointment time.",
            "error"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    # fetch doctors
    cursor.execute("""
        SELECT staff_id, full_name
        FROM medical_staff
        WHERE role = 'doctor'
    """)

    doctors = cursor.fetchall()

    # submit new appointment
    if request.method == "POST":

        doctor_id = request.form.get("doctor_id")
        date = request.form.get("date")
        time = request.form.get("time")

        try:
            new_datetime = datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M"
            )

            if new_datetime <= datetime.now():

                flash(
                    "New appointment must be in the future.",
                    "error"
                )

                cursor.close()
                db.close()

                return redirect('/patient/appointments')

        except ValueError:

            flash("Invalid date/time.", "error")

            cursor.close()
            db.close()

            return redirect('/patient/appointments')

        # update appointment
        cursor.execute("""
            UPDATE appointment
            SET doctor_id = %s,
                appointment_date = %s
            WHERE appointment_id = %s
            AND patient_id = %s
        """, (
            doctor_id,
            new_datetime,
            appointment_id,
            patient_id
        ))

        db.commit()

        flash(
            "Appointment rescheduled successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    return render_template(
        "patient/edit.html",
        appointment=appointment,
        doctors=doctors,
        role="patient",
        active_page="appointments"
    )


# ======================
# CANCEL APPOINTMENT
# ======================
@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    patient_id = 1

    # verify ownership
    cursor.execute("""
        SELECT
            appointment_id,
            patient_id,
            appointment_date,
            status
        FROM appointment
        WHERE appointment_id = %s
        AND patient_id = %s
    """, (appointment_id, patient_id))

    appointment = cursor.fetchone()

    # not found / wrong owner
    if not appointment:

        flash(
            "Appointment not found or access denied.",
            "error"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    # cannot cancel completed/cancelled
    if appointment["status"] != "booked":

        flash(
            "This appointment cannot be cancelled.",
            "error"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    # check 24 hour rule
    time_difference = (
        appointment["appointment_date"] - datetime.now()
    )

    if time_difference < timedelta(hours=24):

        flash(
            "Appointments cannot be cancelled less than 24 hours before appointment time.",
            "error"
        )

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    # cancel appointment
    cursor.execute("""
        UPDATE appointment
        SET status = 'cancelled'
        WHERE appointment_id = %s
        AND patient_id = %s
    """, (
        appointment_id,
        patient_id
    ))

    db.commit()

    flash(
        "Appointment cancelled successfully.",
        "success"
    )

    cursor.close()
    db.close()

    return redirect('/patient/appointments')

# ===============
# PATIENT PROFILE
# ===============
@patient_bp.route('/profile')
def profile():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    patient_id = 1  

    cursor.execute("""
        SELECT
            p.full_name,
            p.email,
            p.nric,
            p.phone,
            p.date_of_birth,
            u.username
        FROM patient p
        JOIN user_account u ON p.user_id = u.user_id
        WHERE p.patient_id = %s
    """, (patient_id,))

    patient = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "patient/profile.html",
        role="patient",
        active_page="profile",
        patient=patient
    )