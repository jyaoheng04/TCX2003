from flask import Blueprint, render_template, request, redirect, session, flash
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
# GET LOGGED IN PATIENT ID
# ======================
def get_logged_in_patient_id():

    user_id = session.get("user_id")

    if not user_id:
        return None

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT patient_id
        FROM patient
        WHERE user_id = %s
    """, (user_id,))

    patient = cursor.fetchone()

    cursor.close()
    db.close()

    if patient:
        return patient["patient_id"]

    return None

# ======================
# VIEW APPOINTMENTS
# ======================
@patient_bp.route('/appointments')
def appointments():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # temporary hardcoded patient
    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

    # auto-complete appointments whose datetime has passed
    # cursor.execute("""
    #     UPDATE appointment
    #     SET queue_status = 'completed'
    #     WHERE appointment_date <= NOW()
    #     AND queue_status = 'waiting'
    # """)

    db.commit()

    # fetch appointments
    cursor.execute("""
        SELECT
            a.appointment_id,
            a.appointment_type,
            a.reason,
            a.appointment_date,
            a.queue_status,
            q.queue_number,
            ms.full_name AS doctor_name
        FROM appointment a
        LEFT JOIN medical_staff ms
            ON a.doctor_id = ms.staff_id
        LEFT JOIN queue q
            ON a.appointment_id = q.appointment_id
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
                form_data=request.form,
                datetime=datetime
            )

        # ======================
        # ASSIGN ROOM BASED ON APPOINTMENT TYPE
        # ======================

        # consultation -> consultation room
        if appointment_type == "consultation":
            # Get the consultation room assigned to the selected doctor
            cursor.execute("""
                SELECT
                    mr.room_id,
                    mr.room_name
                FROM medical_staff ms
                JOIN medical_room mr
                    ON ms.room_id = mr.room_id
                WHERE ms.staff_id = %s
            """, (doctor_id,))


        # blood/urine -> laboratory room
        else:

            cursor.execute("""
                SELECT room_id, room_name
                FROM medical_room
                WHERE room_type = 'laboratory'
                AND status = 'available'
                ORDER BY RAND()
                LIMIT 1
            """)

        room = cursor.fetchone()

        if not room:
            flash("No available room found.", "error")
            return redirect("/patient/create")

        room_id = room["room_id"]
        room_name = room["room_name"]

        # ======================
        # INSERT APPOINTMENT
        # ======================
        # patient_id = 1

        patient_id = get_logged_in_patient_id()

        if not patient_id:
            return redirect("/")

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
            room_name
        ))

        appointment_id = cursor.lastrowid

        # ======================
        # GENERATE QUEUE NUMBER
        # ======================

        prefix = "C" if appointment_type == "consultation" else "L"

        cursor.execute("""
            SELECT queue_number
            FROM queue
            WHERE queue_number LIKE %s
            ORDER BY queue_id DESC
            LIMIT 1
        """, (prefix + "%",))

        last = cursor.fetchone()

        if last is None:
            next_number = 1
        else:
            last_num = int(last["queue_number"][1:])
            next_number = last_num + 1

        queue_number = f"{prefix}{next_number:03d}"

        # ======================
        # INSERT INTO QUEUE
        # ======================
        cursor.execute("""
            INSERT INTO queue
            (
                appointment_id,
                patient_id,
                assigned_staff_id,
                room_id,
                queue_number,
                queue_status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            appointment_id,
            patient_id,
            doctor_id if appointment_type == "consultation" else None,
            room_id,
            queue_number,
            "waiting"
        ))

        queue_id = cursor.lastrowid
        
        # ======================
        # INSERT CONSULTATION
        # ======================
        cursor.execute("""
        INSERT INTO consultation
        (
            appointment_id,
            patient_id,
            staff_id,
            queue_id,
            visit_type,
            service_type,
            consultation_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            appointment_id,
            patient_id,
            doctor_id if appointment_type == "consultation" else None,
            queue_id,
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
                None
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
        form_data={},
        datetime=datetime
    )

# ======================
# RESCHEDULE APPOINTMENT
# ======================
@patient_bp.route('/edit/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

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
        if doctor_id == "":
            doctor_id = None

        if doctor_id == "" or doctor_id is None:
            doctor_id = None

        date = request.form.get("date")
        time = request.form.get("time")

        try:
            new_datetime = datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M"
            )

            # =========================
            # cannot book TODAY or PAST
            # earliest = TOMORROW 00:00+
            # =========================
            today = datetime.now().date()

            if new_datetime.date() <= today:
                flash(
                    "Rescheduled appointment must be from tomorrow onwards.",
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
        
        # ============================
        # enforce type-based conflict rule
        # ============================
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM appointment
            WHERE appointment_date = %s
            AND appointment_type = %s
            AND appointment_id != %s
            AND queue_status = 'waiting'
        """, (new_datetime, appointment["appointment_type"], appointment_id))

        conflict = cursor.fetchone()

        if conflict["cnt"] > 0:
            flash("This time slot is already booked for this test type.", "error")
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
        appointment_type=appointment["appointment_type"],
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

    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

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

    # patient_id = 1  

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

    cursor.execute("""
        SELECT
            p.full_name,
            p.email,
            p.nric,
            p.phone,
            p.date_of_birth,
            u.email
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

    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

    cursor.execute("""
        SELECT
            c.consultation_id,
            c.service_type,
            c.symptoms,
            c.doctor_notes,
            c.prescription_notes,
            c.medical_bill,
            c.consultation_time,
            ms.full_name AS doctor_name,
            lr.test_type AS lab_test_type,
            lr.result_status AS lab_result_status,
            a.queue_status
        FROM consultation c
        LEFT JOIN medical_staff ms
            ON c.staff_id = ms.staff_id
        LEFT JOIN lab_result lr
            ON lr.consultation_id = c.consultation_id
        LEFT JOIN appointment a
            ON c.appointment_id = a.appointment_id
        WHERE c.patient_id = %s
        ORDER BY c.consultation_time DESC
    """, (patient_id,))

    records = cursor.fetchall()

    cursor.close()
    db.close()

    for record in records:

        # parse bill
        bill_data = {
            "consultation_fee": 18.5,
            "medications": [],
            "total_price": 0.0
        }
        try:
            raw = record.get("medical_bill")
            if raw and isinstance(raw, str) and raw.strip().startswith("{"):
                bill_data.update(json.loads(raw))
            elif raw:
                bill_data["total_price"] = float(raw)
        except Exception:
            pass
        bill_data["total_price"] = float(bill_data.get("total_price", 0) or 0)
        record["bill_data"] = bill_data

        # parse prescription
        rx = []
        try:
            raw_rx = record.get("prescription_notes")
            if raw_rx:
                parsed = json.loads(raw_rx)
                if isinstance(parsed, list):
                    rx = parsed
        except Exception:
            pass
        record["parsed_prescription"] = rx

        # if a lab test was ordered alongside the consultation, show both
        if record.get("lab_test_type"):
            lab_label = record["lab_test_type"].replace("_", " ").title()
            record["service_label"] = f"Consultation + {lab_label}"
        else:
            record["service_label"] = record["service_type"].replace("_", " ").title() if record["service_type"] else "—"

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

    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

    # main consultation
    cursor.execute("""
        SELECT
            c.consultation_id,
            c.service_type,
            c.symptoms,
            c.doctor_notes,
            c.prescription_notes,
            c.medical_bill,
            c.temperature,
            c.blood_pressure,
            c.consultation_time,
            ms.full_name AS doctor_name
        FROM consultation c
        LEFT JOIN medical_staff ms
            ON c.staff_id = ms.staff_id
        WHERE c.consultation_id = %s
        AND c.patient_id = %s
    """, (consultation_id, patient_id))

    record = cursor.fetchone()

    if not record:
        cursor.close()
        db.close()
        return redirect('/patient/records')

    # lab result for this consultation (if any)
    cursor.execute("""
        SELECT
            lab_result_id,
            test_type,
            result_details,
            result_date,
            result_status
        FROM lab_result
        WHERE consultation_id = %s
    """, (consultation_id,))

    lab = cursor.fetchone()

    # vitals history for charts
    cursor.execute("""
        SELECT
            consultation_time,
            temperature,
            blood_pressure
        FROM consultation
        WHERE patient_id = %s
        ORDER BY consultation_time ASC
    """, (patient_id,))

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    # parse bill
    bill_data = {
        "consultation_fee": 18.5,
        "medications": [],
        "total_price": 0.0
    }
    try:
        raw = record.get("medical_bill")
        if raw and isinstance(raw, str) and raw.strip().startswith("{"):
            bill_data.update(json.loads(raw))
        elif raw:
            bill_data["total_price"] = float(raw)
    except Exception:
        pass
    bill_data["total_price"] = float(bill_data.get("total_price", 0) or 0)

    # parse prescription
    rx = []
    try:
        raw_rx = record.get("prescription_notes")
        if raw_rx:
            parsed = json.loads(raw_rx)
            if isinstance(parsed, list):
                rx = parsed
    except Exception:
        pass

    # parse lab result
    if lab and lab.get("result_details"):
        try:
            lab["parsed_results"] = json.loads(lab["result_details"])
        except Exception:
            lab["parsed_results"] = {}
    elif lab:
        lab["parsed_results"] = {}

    # build chart data
    systolic = []
    diastolic = []
    temperatures = []

    for r in rows:
        x = r["consultation_time"].strftime("%Y-%m-%d %H:%M:%S")

        if r["blood_pressure"]:
            try:
                sys, dia = r["blood_pressure"].split("/")
                systolic.append({"x": x, "y": int(sys)})
                diastolic.append({"x": x, "y": int(dia)})
            except Exception:
                pass

        try:
            if r["temperature"]:
                temperatures.append({"x": x, "y": float(r["temperature"])})
        except Exception:
            pass

    return render_template(
        "patient/report.html",
        record=record,
        bill_data=bill_data,
        prescription=rx,
        lab=lab,
        systolic=systolic,
        diastolic=diastolic,
        temperatures=temperatures,
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
    # CONSULTATION → per doctor
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
    # BLOOD + URINE SEPARATION
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

    # patient_id = 1

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return redirect("/")

    today = date.today()

    # TODAY APPOINTMENTS
    cursor.execute("""
        SELECT
            a.*,
            q.queue_number,
            m.full_name AS doctor_name,
            m.department
        FROM appointment a
        LEFT JOIN medical_staff m
            ON a.doctor_id = m.staff_id
        LEFT JOIN queue q
            ON a.appointment_id = q.appointment_id
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
            q.queue_number,
            m.full_name AS doctor_name,
            m.department
        FROM appointment a
        LEFT JOIN medical_staff m
            ON a.doctor_id = m.staff_id
        LEFT JOIN queue q
            ON a.appointment_id = q.appointment_id
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

# ======================
# GET AVAILABLE TIMES (EDIT PAGE)
# ======================
@patient_bp.route('/available-times-edit')
def available_times_edit():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    date = request.args.get("date")
    doctor_id = request.args.get("doctor_id")
    appointment_type = request.args.get("appointment_type")

    if not date:
        return {"booked": []}

    today = datetime.now().date()
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()

    if selected_date <= today:
        return {"booked": []}

    # ============================
    # CONSULTATION
    # ============================
    if appointment_type == "consultation" and doctor_id:

        cursor.execute("""
            SELECT appointment_date
            FROM appointment
            WHERE DATE(appointment_date) = %s
            AND doctor_id = %s
            AND queue_status = 'waiting'
        """, (date, doctor_id))

    # ============================
    # BLOOD / URINE SEPARATION
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

# ======================
# CREATE MULTI APPOINTMENT
# ======================
@patient_bp.route('/create-multi', methods=['GET', 'POST'])
def create_multi():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT staff_id, full_name
        FROM medical_staff
        WHERE role = 'doctor'
    """)
    doctors = cursor.fetchall()

    if request.method == 'POST':

        # patient_id = 1

        patient_id = get_logged_in_patient_id()

        if not patient_id:
            return redirect("/")

        errors = {}

        selected_date = request.form.get('shared_date')
        reason = request.form.get('reason')
        doctor_id = request.form.get('doctor_id') or None

        # which types were selected
        types_selected = request.form.getlist('appointment_types')

        if not selected_date:
            errors['shared_date'] = "Date is required."

        if not reason:
            errors['reason'] = "Reason is required."

        if not types_selected:
            errors['types'] = "Please select at least one appointment type."

        if 'consultation' in types_selected and not doctor_id:
            errors['doctor_id'] = "Doctor is required for consultation."

        # collect times per type
        times = {}
        for t in types_selected:
            time_val = request.form.get(f'time_{t}')
            if not time_val:
                errors[f'time_{t}'] = f"Time is required for {t.replace('_', ' ').title()}."
            else:
                times[t] = time_val

        # validate no clashes between selected types in this form
        if not errors:
            parsed_times = {}
            for t, time_val in times.items():
                try:
                    dt = datetime.strptime(f"{selected_date} {time_val}", "%Y-%m-%d %H:%M")
                    if dt <= datetime.now():
                        errors[f'time_{t}'] = "Appointment must be in the future."
                    duration = 50 if t == 'consultation' else 30
                    parsed_times[t] = (dt, dt + timedelta(minutes=duration))
                except ValueError:
                    errors[f'time_{t}'] = "Invalid time."

            # check clashes between types in this form
            if not errors:
                type_list = list(parsed_times.keys())
                for i in range(len(type_list)):
                    for j in range(i + 1, len(type_list)):
                        t1, t2 = type_list[i], type_list[j]
                        start1, end1 = parsed_times[t1]
                        start2, end2 = parsed_times[t2]
                        if start1 < end2 and start2 < end1:
                            errors[f'time_{t2}'] = (
                                f"{t2.replace('_',' ').title()} clashes with "
                                f"{t1.replace('_',' ').title()} time."
                            )

        if errors:
            cursor.close()
            db.close()
            return render_template(
                'patient/create_multi.html',
                doctors=doctors,
                errors=errors,
                form_data=request.form,
                datetime=datetime,
                role="patient",
                active_page="appointments"
            )

        # ======================
        # ASSIGN ROOM
        # ======================

        if t == "consultation":

            cursor.execute("""
                SELECT room_id, room_name
                FROM medical_room
                WHERE room_type = 'consultation'
                AND status = 'available'
                ORDER BY RAND()
                LIMIT 1
            """)

        else:

            cursor.execute("""
                SELECT room_id, room_name
                FROM medical_room
                WHERE room_type = 'laboratory'
                AND status = 'available'
                ORDER BY RAND()
                LIMIT 1
            """)

        room = cursor.fetchone()

        if not room:
            flash("No available room found.", "error")
            return redirect("/patient/create-multi")

        room_id = room["room_id"]
        room_name = room["room_name"]

        # ======================
        # INSERT SINGLE CONSULTATION
        # ======================
        consult_time = datetime.strptime(
            f"{selected_date} {times.get('consultation', list(times.values())[0])}",
            "%Y-%m-%d %H:%M"
        )

        cursor.execute("""
            INSERT INTO consultation (
                patient_id, staff_id,
                visit_type, service_type,
                consultation_time
            ) VALUES (%s, %s, 'appointment', 'consultation', %s)
        """, (
            patient_id,
            doctor_id if 'consultation' in types_selected else None,
            consult_time
        ))

        consultation_id = cursor.lastrowid

        # ======================
        # INSERT APPOINTMENT + LAB RESULT PER TYPE
        # ======================
        for t in types_selected:

            appt_dt = datetime.strptime(
                f"{selected_date} {times[t]}",
                "%Y-%m-%d %H:%M"
            )

            cursor.execute("""
                INSERT INTO appointment (
                    patient_id, doctor_id,
                    appointment_type, reason,
                    appointment_date, queue_status,
                    consultation_room
                ) VALUES (%s, %s, %s, %s, %s, 'waiting', %s)
            """, (
                patient_id,
                doctor_id if t == 'consultation' else None,
                t,
                reason,
                appt_dt,
                room_name
            ))

            appointment_id = cursor.lastrowid

            # ======================
            # GENERATE QUEUE NUMBER
            # ======================

            prefix = "C" if t == "consultation" else "L"

            cursor.execute("""
                SELECT queue_number
                FROM queue
                WHERE queue_number LIKE %s
                ORDER BY queue_id DESC
                LIMIT 1
            """, (prefix + "%",))

            last = cursor.fetchone()

            if last is None:
                next_number = 1
            else:
                last_num = int(last["queue_number"][1:])
                next_number = last_num + 1

            queue_number = f"{prefix}{next_number:03d}"


            # ======================
            # INSERT QUEUE
            # ======================

            cursor.execute("""
                INSERT INTO queue (
                    appointment_id,
                    patient_id,
                    assigned_staff_id,
                    room_id,
                    queue_number,
                    queue_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                appointment_id,
                patient_id,
                doctor_id if t == "consultation" else None,
                room_id,
                queue_number,
                "waiting"
            ))

            queue_id = cursor.lastrowid

            # link appointment to consultation
            cursor.execute("""
                UPDATE consultation
                SET appointment_id = %s,
                    queue_id = %s
                WHERE consultation_id = %s
                AND appointment_id IS NULL
            """, (
                appointment_id,
                queue_id,
                consultation_id
            ))

            # insert lab result for lab types
            if t in ('blood_test', 'urine_test'):
                cursor.execute("""
                    INSERT INTO lab_result (
                        consultation_id, test_type,
                        result_details, result_date, result_status
                    ) VALUES (%s, %s, NULL, NULL, NULL)
                """, (consultation_id, t))
            
        db.commit()
        cursor.close()
        db.close()

        return redirect('/patient/appointments')

    cursor.close()
    db.close()

    return render_template(
        'patient/create_multi.html',
        doctors=doctors,
        errors={},
        form_data={},
        datetime=datetime,
        role="patient",
        active_page="appointments"
    )

# ======================
# GET NOTIFICATIONS
# ======================

@patient_bp.route('/notifications')
def notifications():

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return {"notifications": []}

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            notification_id,
            message,
            is_read,
            created_at
        FROM notification
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient_id,))

    notifications = cursor.fetchall()

    cursor.close()
    db.close()

    return {"notifications": notifications}


# ======================
# MARK AS READ
# ======================
@patient_bp.route('/read-notification/<int:notification_id>', methods=['POST'])
def read_notification(notification_id):

    patient_id = get_logged_in_patient_id()

    if not patient_id:
        return {"success": False}

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE notification
        SET is_read = TRUE
        WHERE notification_id = %s
        AND patient_id = %s
    """, (notification_id, patient_id))

    db.commit()

    cursor.close()
    db.close()

    return {"success": True}