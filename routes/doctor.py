from flask import Blueprint, render_template, request, redirect, url_for
import json
import mysql.connector
import os
from dotenv import load_dotenv
import random
import json
import random
from flask import request, redirect, url_for

load_dotenv()

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

# dashboard (QUEUE)
@doctor_bp.route("/dashboard")
def dashboard():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
            SELECT
                q.queue_id,
                q.queue_number,
                q.queue_status,
                p.full_name,
                c.consultation_time
            FROM queue q
            JOIN patient p
                ON p.patient_id = q.patient_id
            JOIN consultation c
                ON c.queue_id = q.queue_id
            WHERE c.service_type = 'consultation'
            ORDER BY
                CASE
                    WHEN q.queue_status = 'waiting' THEN 0
                    WHEN q.queue_status = 'in_consultation' THEN 1
                    WHEN q.queue_status = 'completed' THEN 2
                    WHEN q.queue_status = 'cancelled' THEN 3
                    ELSE 4
                END,
                c.consultation_time
        """)

    queue = cursor.fetchall()

    cursor.close()
    db.close()

    next_patient = queue[0] if queue else None
    rest_queue = queue[1:] if len(queue) > 1 else []

    return render_template("doctor/dashboard.html", next_patient=next_patient, queue=rest_queue, role="doctor", active_page="dashboard")
    
# consult form
@doctor_bp.route("/consultation/<int:queue_id>")
def consultation(queue_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Update queue status
    cursor.execute("""
        UPDATE queue
        SET queue_status = 'in_consultation'
        WHERE queue_id = %s
        AND queue_status = 'waiting'
    """, (queue_id,))

    # Update appointment status
    cursor.execute("""
        UPDATE appointment a
        JOIN queue q ON a.appointment_id = q.appointment_id
        SET a.queue_status = 'in_consultation'
        WHERE q.queue_id = %s
    """, (queue_id,))

    db.commit()

    # patient info
    cursor.execute("""
        SELECT w.queue_id, p.patient_id, p.full_name, p.date_of_birth
        FROM queue w
        JOIN patient p ON p.patient_id = w.patient_id
        WHERE w.queue_id = %s
    """, (queue_id,))

    patient = cursor.fetchone()
    patient_id = patient["patient_id"]

    # consultation history
    cursor.execute("""
        SELECT consultation_id,
               consultation_time,
               temperature,
               blood_pressure
        FROM consultation
        WHERE patient_id = %s
        ORDER BY consultation_time ASC
    """, (patient_id,))

    rows = cursor.fetchall()

    # lab history
    cursor.execute("""
        SELECT
            l.lab_result_id,
            l.test_type,
            c.consultation_time
        FROM lab_result l
        JOIN consultation c
            ON c.consultation_id = l.consultation_id
        WHERE c.patient_id = %s
        ORDER BY c.consultation_time DESC
    """, (patient_id,))

    lab_history = cursor.fetchall()

    cursor.close()
    db.close()

    systolic = []
    diastolic = []
    temperatures = []
    labels = []

    for r in rows:

        x = r["consultation_time"].strftime("%Y-%m-%d %H:%M:%S")
        labels.append(x)

        # blood pressure
        if r["blood_pressure"]:
            try:
                sys, dia = r["blood_pressure"].split("/")
                systolic.append({"x": x, "y": int(sys)})
                diastolic.append({"x": x, "y": int(dia)})
            except:
                pass

        # temperature
        try:
            temperatures.append({"x": x, "y": float(r["temperature"])})
        except:
            pass

    return render_template(
        "doctor/create.html",
        q=patient,
        labels=labels,
        systolic=systolic,
        diastolic=diastolic,
        temperatures=temperatures,
        lab_history=lab_history,
        role="doctor",
        active_page="create"
    )
    
# save consult form
@doctor_bp.route("/consultation/save", methods=["POST"])
def save_consultation():

    db = get_db()
    cursor = db.cursor()

    queue_id = request.form["queue_id"]
    patient_id = request.form["patient_id"]

    symptoms = request.form["symptoms"]
    doctor_notes = request.form["doctor_notes"]
    temp = request.form["temperature"]
    bp = request.form["blood_pressure"]

    #lab test selection
    test_order = request.form.get("test_order", "none")

    # prescription
    medicine_names = request.form.getlist("medicine[]")
    dosage_list = request.form.getlist("dosage[]")

    prescription = []
    for m, d in zip(medicine_names, dosage_list):
        if m.strip():
            prescription.append({
                "medicine": m,
                "dosage": d
            })

    prescription_json = json.dumps(prescription)

    # billing
    consultation_fee = 18.50
    medications = []
    medicine_total = 0

    for name in medicine_names:
        if name.strip():
            price = round(random.uniform(0.5, 3.0), 2)

            medications.append({
                "name": name,
                "price": price
            })

            medicine_total += price

    total_bill = round(consultation_fee + medicine_total, 2)

    bill_json = json.dumps({
        "consultation_fee": consultation_fee,
        "medications": medications,
        "total_price": total_bill
    })

    cursor.execute("""
        INSERT INTO consultation (
            queue_id, patient_id, staff_id,
            symptoms, doctor_notes, prescription_notes,
            temperature, blood_pressure,
            visit_type, service_type, medical_bill, consultation_time
        )
        VALUES (%s,%s,1,%s,%s,%s,%s,%s,'walkin','consultation',%s,NOW())
    """, (
        queue_id,
        patient_id,
        symptoms,
        doctor_notes,
        prescription_json,
        temp,
        bp,
        bill_json
    ))
    consultation_id = cursor.lastrowid
    if test_order in ["blood", "urine"]:

        test_type = 'blood_test' if test_order == "blood" else 'urine_test'

        cursor.execute("""
            INSERT INTO lab_result (
                consultation_id,
                test_type,
                result_details,
                result_date,
                result_status
            )
            VALUES (%s,%s,%s,NOW(),%s)
        """, (
            consultation_id,
            test_type,
            None,
            None
        ))

        cursor.execute("""
            UPDATE queue
            SET queue_status = 'pending'
            WHERE queue_id = %s
        """, (queue_id,))

    else:
        cursor.execute("""
            UPDATE queue
            SET queue_status = 'completed'
            WHERE queue_id = %s
        """, (queue_id,))

        cursor.execute("""
            UPDATE appointment
            SET queue_status = 'completed'
            WHERE queue_id = %s
        """, (queue_id,))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for("doctor.dashboard"))

# lab results
@doctor_bp.route("/labs")
def labs():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    status = request.args.get("status", "all")

    query = """
        SELECT
            l.*,
            p.full_name AS patient_name
        FROM lab_result l
        JOIN consultation c
            ON c.consultation_id = l.consultation_id
        JOIN patient p
            ON p.patient_id = c.patient_id
    """

    if status == "pending":
        query += """
            WHERE l.result_status IS NULL
        """

    elif status == "ready":
        query += """
            WHERE l.result_status IS NOT NULL
        """

    query += """
        ORDER BY
            COALESCE(l.result_date, c.consultation_time) DESC
    """

    cursor.execute(query)

    labs = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "doctor/lab_results.html",
        labs=labs,
        role="doctor",
        active_page="labs"
    )

# consultations
import json

@doctor_bp.route("/consultations")
def consultations():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.consultation_id,
            c.doctor_notes,
            c.medical_bill,
            c.consultation_time,
            p.full_name AS patient_name
        FROM consultation c
        JOIN patient p ON p.patient_id = c.patient_id
        ORDER BY c.consultation_time DESC
    """)

    bills = cursor.fetchall()

    total_revenue = 0.0

    for bill in bills:

        raw = bill.get("medical_bill")

        bill_data = {
            "consultation_fee": 18.5,
            "medications": [],
            "total_price": 0.0
        }

        try:
            if raw and isinstance(raw, str) and raw.strip().startswith("{"):
                parsed = json.loads(raw)
                bill_data.update(parsed)

            elif raw:
                bill_data["total_price"] = float(raw)

        except Exception:
            pass

        # ensure total_price always valid float
        bill_data["total_price"] = float(bill_data.get("total_price", 0) or 0)

        bill["bill_data"] = bill_data
        total_revenue += bill_data["total_price"]

    total_consultations = len(bills)

    cursor.close()
    db.close()

    return render_template(
        "doctor/consultations.html",
        consultations=bills,
        total_revenue=round(total_revenue, 2),
        total_consultations=total_consultations,
        role="doctor",
        active_page="consultations"
    )

@doctor_bp.route("/consult_detail/<int:consultation_id>")
def consult_detail(consultation_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.*,
            p.full_name AS patient_name
        FROM consultation c
        JOIN patient p ON p.patient_id = c.patient_id
        WHERE c.consultation_id = %s
    """, (consultation_id,))

    bill = cursor.fetchone()

    cursor.close()
    db.close()

    bill_data = {
        "consultation_fee": 18.5,
        "medications": [],
        "total_price": 0
    }

    if bill and bill.get("medical_bill"):
        try:
            bill_data = json.loads(bill["medical_bill"])
        except:
            pass

    return render_template(
        "doctor/consult_detail.html",
        bill=bill,
        bill_data=bill_data,
        role="doctor"
    )
    
# patient history
@doctor_bp.route("/patients")
def patients():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    search = request.args.get("q", "")

    if search:
        cursor.execute("""
            SELECT 
                p.patient_id, 
                p.full_name, 
                p.nric, 
                p.phone, 
                p.email,
                MAX(c.consultation_time) AS last_visit
            FROM patient p
            LEFT JOIN consultation c 
                ON c.patient_id = p.patient_id
            WHERE p.full_name LIKE %s
            OR p.nric LIKE %s
            OR p.phone LIKE %s
            GROUP BY 
                p.patient_id, p.full_name, p.nric, p.phone, p.email
            ORDER BY p.full_name ASC
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))

    else:
        cursor.execute("""
            SELECT 
                p.patient_id, 
                p.full_name, 
                p.nric, 
                p.phone, 
                p.email,
                MAX(c.consultation_time) AS last_visit
            FROM patient p
            LEFT JOIN consultation c 
                ON c.patient_id = p.patient_id
            GROUP BY 
                p.patient_id, p.full_name, p.nric, p.phone, p.email
            ORDER BY p.full_name ASC
        """)

    patients = cursor.fetchall()

    cursor.close()
    db.close()


    return render_template(
        "doctor/patients.html",
        patients=patients,
        role="doctor",
        active_page="patients",
        search=search
    )
    
# patients detail
@doctor_bp.route("/patients/<int:patient_id>")
def patient_detail(patient_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM patient WHERE patient_id=%s", (patient_id,))
    patient = cursor.fetchone()

    cursor.execute("""
        SELECT consultation_id, consultation_time, doctor_notes, medical_bill
        FROM consultation
        WHERE patient_id=%s
        ORDER BY consultation_time DESC
    """, (patient_id,))

    consultations = cursor.fetchall()

    for c in consultations:

        bill_data = {
            "consultation_fee": 18.5,
            "medications": [],
            "total_price": 0
        }

        try:
            if c.get("medical_bill"):
                bill_data = json.loads(c["medical_bill"])
        except:
            pass

        c["bill_data"] = bill_data
    
    cursor.execute("""
        SELECT consultation_id, consultation_time, temperature, blood_pressure
        FROM consultation
        WHERE patient_id = %s
        ORDER BY consultation_time ASC
    """, (patient_id,))

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    systolic = []
    diastolic = []
    temperatures = []
    labels = []

    for r in rows:

        x = r["consultation_time"].strftime("%Y-%m-%d %H:%M:%S")
        labels.append(x)

        # BP
        if r["blood_pressure"]:
            try:
                sys, dia = r["blood_pressure"].split("/")
                systolic.append({"x": x, "y": int(sys)})
                diastolic.append({"x": x, "y": int(dia)})
            except:
                pass

        # temperature
        try:
            temperatures.append({"x": x, "y": float(r["temperature"])})
        except:
            pass


    return render_template(
        "doctor/patient_detail.html",
        patient=patient,
        consultations=consultations,
        labels=labels,
        systolic=systolic,
        diastolic=diastolic,
        temperatures=temperatures,
        role="doctor",
        active_page="patients"
    )

@doctor_bp.route("/queue-board")
def queue_board():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    doctor_id = 1  # Doctor 1 for now

    cursor.execute("""
        SELECT full_name, room_id
        FROM medical_staff
        WHERE staff_id=%s
    """, (doctor_id,))
    doctor = cursor.fetchone()

    cursor.execute("""
        SELECT room_name
        FROM medical_room
        WHERE room_id=%s
    """, (doctor["room_id"],))
    room = cursor.fetchone()

    cursor.execute("""
        SELECT queue_number
        FROM queue
        WHERE assigned_staff_id=%s
        AND queue_status='in_consultation'
        LIMIT 1
    """, (doctor_id,))
    current = cursor.fetchone()

    cursor.execute("""
        SELECT queue_number
        FROM queue
        WHERE assigned_staff_id=%s
        AND queue_status='waiting'
        ORDER BY queue_id
    """, (doctor_id,))
    waiting = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "doctor/queue_board.html",
        doctor=doctor,
        room=room,
        current=current,
        waiting=waiting
    )