from flask import Blueprint, render_template, request, redirect, session
from datetime import datetime, timedelta, date
import mysql.connector
import os
import json

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
        SET queue_status = 'completed'
        WHERE appointment_date <= NOW()
        AND queue_status = 'waiting'
    """)

    db.commit()

    # fetch appointments
    cursor.execute("""
        SELECT
            a.appointment_id,
            a.appointment_type,
            a.reason,
            a.appointment_date,
            a.queue_status,
            ms.full_name AS doctor_name
        FROM appointment a
        LEFT JOIN medical_staff ms
            ON a.doctor_id = ms.staff_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date ASC
    """, (patient_id,))

    appointments = cursor.fetchall()

    # determine if appointment can be modified
    # (cancel + reschedule allowed only >24 hrs)
    for appointment in appointments:

        appointment["can_modify"] = False

        if appointment["queue_status"] == "waiting":

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

        # only consultation needs doctor
        if appointment_type != "consultation":
            doctor_id = None

        date = request.form.get('date')
        time = request.form.get('time')
        reason = request.form.get('reason')

        errors = {}

        # ======================
        # FIELD VALIDATION
        # ======================
        if appointment_type == "consultation" and not doctor_id:
            errors["doctor_id"] = "Doctor is required."

        if not appointment_type:
            errors["appointment_type"] = "Appointment type is required."

        if not date:
            errors["date"] = "Date is required."

        if not time:
            errors["time"] = "Time is required."

        if not reason:
            errors["reason"] = "Reason is required."

        appointment_datetime = None

        if date and time:
            try:
                appointment_datetime = datetime.strptime(
                    f"{date} {time}",
                    "%Y-%m-%d %H:%M"
                )

                if appointment_datetime <= datetime.now():
                    errors["date"] = "Appointment must be in the future."

            except ValueError:
                errors["date"] = "Invalid date/time."

        # ======================
        # RETURN ERRORS IF ANY
        # ======================
        if errors:
            return render_template(
                'patient/create.html',
                role="patient",
                active_page="appointments",
                doctors=doctors,
                errors=errors,
                form_data=request.form
            )

        # ======================
        # INSERT APPOINTMENT
        # ======================
        patient_id = 1

        cursor.execute("""
            INSERT INTO appointment
            (
                patient_id,
                doctor_id,
                appointment_type,
                reason,
                appointment_date,
                queue_status,
                consultation_room
            )
            VALUES (%s, %s, %s, %s, %s, 'waiting', %s)
        """, (
            patient_id,
            doctor_id,
            appointment_type,
            reason,
            appointment_datetime,
            "Room 3A"
        ))

        appointment_id = cursor.lastrowid

        # ======================
        # INSERT CONSULTATION
        # ======================
        cursor.execute("""
            INSERT INTO consultation
            (
                appointment_id,
                patient_id,
                staff_id,
                visit_type,
                service_type,
                consultation_time
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            appointment_id,
            patient_id,
            doctor_id if appointment_type == "consultation" else None,
            'appointment',
            appointment_type,
            appointment_datetime
        ))

        consultation_id = cursor.lastrowid

        # ======================
        # LAB RESULT (if needed)
        # ======================
        if appointment_type in ['blood_test', 'urine_test']:

            cursor.execute("""
                INSERT INTO lab_result
                (
                    consultation_id,
                    test_type,
                    result_details,
                    result_date,
                    result_status
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                consultation_id,
                appointment_type,
                None,
                None,
                'pending'
            ))

        db.commit()

        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    cursor.close()
    db.close()

    return render_template(
        'patient/create.html',
        role="patient",
        active_page="appointments",
        doctors=doctors,
        errors={},
        form_data={}
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
            queue_status
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
    if appointment["queue_status"] != "waiting":

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
        SET queue_status = 'cancelled'
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

# ======================
# MEDICAL RECORDS
# ======================
@patient_bp.route('/records')
def records():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    patient_id = 1   # replace with session later

    cursor.execute("""
        SELECT
            c.consultation_id,
            c.service_type,
            c.symptoms,
            c.doctor_notes,
            c.prescription_notes,
            c.medical_bill,
            c.consultation_time,
            ms.full_name AS doctor_name
        FROM consultation c
        JOIN medical_staff ms
            ON c.staff_id = ms.staff_id
        JOIN appointment a
            ON c.appointment_id = a.appointment_id
        WHERE c.patient_id = %s
        AND a.queue_status = 'completed'
        ORDER BY c.consultation_time DESC
    """, (patient_id,))

    records = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "patient/records.html",
        role="patient",
        active_page="records",
        records=records
    )

# ======================
# VIEW LAB REPORT
# ======================
@patient_bp.route('/report/<int:consultation_id>')
def view_report(consultation_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    patient_id = 1

    cursor.execute("""
        SELECT
            lr.lab_result_id,
            lr.test_type,
            lr.result_details,
            lr.result_date,
            lr.result_status,

            c.consultation_id,
            c.doctor_notes,
            c.symptoms,
            c.prescription_notes,
            c.consultation_time,

            ms.full_name AS doctor_name
        FROM lab_result lr
        JOIN consultation c
            ON lr.consultation_id = c.consultation_id
        JOIN medical_staff ms
            ON c.staff_id = ms.staff_id
        WHERE c.consultation_id = %s
        AND c.patient_id = %s
    """, (consultation_id, patient_id))

    report = cursor.fetchone()

    if report and report.get("result_details"):
        try:
            report["parsed_results"] = json.loads(report["result_details"])
        except json.JSONDecodeError:
            report["parsed_results"] = {}
    else:
        report = report or {}
        report["parsed_results"] = {}

    cursor.close()
    db.close()

    return render_template(
        "patient/report.html",
        report=report,
        role="patient"
    )

# ======================
# GET BOOKED TIMES FOR A DATE
# ======================
@patient_bp.route('/available-times')
def available_times():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    date = request.args.get("date")
    doctor_id = request.args.get("doctor_id")
    appointment_type = request.args.get("appointment_type")

    if not date:
        return {"booked": []}

    # ============================
    # CONSULTATION → check by doctor
    # ============================
    if appointment_type == "consultation":

        if not doctor_id:
            return {"booked": []}

        cursor.execute("""
            SELECT appointment_date
            FROM appointment
            WHERE DATE(appointment_date) = %s
            AND doctor_id = %s
            AND queue_status = 'waiting'
        """, (date, doctor_id))

    # ============================
    # BLOOD / URINE TEST → global check
    # ============================
    else:

        cursor.execute("""
            SELECT appointment_date
            FROM appointment
            WHERE DATE(appointment_date) = %s
            AND queue_status = 'waiting'
            AND appointment_type = %s
        """, (date, appointment_type))

    results = cursor.fetchall()

    booked_times = [
        row["appointment_date"].strftime("%H:%M")
        for row in results
    ]

    cursor.close()
    db.close()

    return {"booked": booked_times}

# =========
# DASHBOARD
# =========

@patient_bp.route("/dashboard")
def dashboard():

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="polyclinic"
    )

    cursor = conn.cursor(dictionary=True)

    patient_id = 1
    today = date.today()

    # TODAY APPOINTMENTS
    cursor.execute("""
        SELECT
            a.*,
            m.full_name AS doctor_name,
            m.department
        FROM appointment a
        LEFT JOIN medical_staff m
            ON a.doctor_id = m.staff_id
        WHERE a.patient_id = %s
        AND DATE(a.appointment_date) = %s
        AND a.queue_status != 'cancelled'
        ORDER BY a.appointment_date ASC
    """, (patient_id, today))

    today_appointments = cursor.fetchall()

    # UPCOMING
    cursor.execute("""
        SELECT
            a.*,
            m.full_name AS doctor_name,
            m.department
        FROM appointment a
        LEFT JOIN medical_staff m
            ON a.doctor_id = m.staff_id
        WHERE a.patient_id = %s
        AND DATE(a.appointment_date) > %s
        AND a.queue_status != 'cancelled'
        ORDER BY a.appointment_date ASC
    """, (patient_id, today))

    upcoming_appointments = cursor.fetchall()

    cursor.close()
    conn.close()

    APPOINTMENT_LABELS = {
        "consultation": "Consultation",
        "blood_test": "Blood Test",
        "urine_test": "Urine Test"
        }

    return render_template(
        "patient/dashboard.html",
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        appointment_labels=APPOINTMENT_LABELS,
        active_page="dashboard",
        role="patient"
    )