from flask import Blueprint, render_template, request, redirect, url_for
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import date
import json
import random

load_dotenv()

nurse_bp = Blueprint("nurse", __name__, url_prefix="/nurse")

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

# queue
@nurse_bp.route("/dashboard")
def queue():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
       SELECT
            lr.lab_result_id,
            p.full_name,
            w.priority_status,
            w.queue_status
        FROM lab_result lr
        JOIN consultation c ON c.consultation_id = lr.consultation_id
        JOIN patient p ON p.patient_id = c.patient_id
        JOIN walk_in_queue w ON w.queue_id = c.queue_id
        ORDER BY 
            CASE 
                WHEN w.queue_status = 'pending' AND w.priority_status = 'priority' THEN 0
                WHEN w.queue_status = 'pending' THEN 1
                WHEN w.queue_status = 'in_consultation' THEN 2
                WHEN w.queue_status = 'waiting' THEN 3
                ELSE 4
            END,
            w.check_in_time ASC
    """)

    queue = cursor.fetchall()

    next_patient = None
    for q in queue:
        if q["queue_status"] == "pending":
            next_patient = q
            break

    cursor.close()
    db.close()

    return render_template(
        "nurse/dashboard.html",
        queue=queue,
        next_patient=next_patient,
        role="nurse",
        active_page="dashboard"
    )

# VITALS PAGE
@nurse_bp.route("/lab/<int:lab_result_id>")
def lab_test(lab_result_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            lr.lab_result_id,
            lr.test_type,
            lr.result_status,

            c.consultation_id,
            c.symptoms,
            c.consultation_time,

            p.patient_id,
            p.full_name,

            w.queue_id,
            w.priority_status,
            w.queue_status

        FROM lab_result lr

        JOIN consultation c
            ON c.consultation_id = lr.consultation_id

        JOIN patient p
            ON p.patient_id = c.patient_id

        LEFT JOIN walk_in_queue w
            ON w.queue_id = c.queue_id

        WHERE lr.lab_result_id = %s
    """, (lab_result_id,))

    lab = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "nurse/vitals.html",
        lab=lab,
        role="nurse"
    )

# SAVE VITALS
@nurse_bp.route("/lab/save", methods=["POST"])
def save_lab():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    lab_result_id = request.form["lab_result_id"]

    result_json = (
        request.form.get("blood_json")
        or request.form.get("urine_json")
    )

    result_status = request.form["result_status"]

    # Update lab result
    cursor.execute("""
        UPDATE lab_result
        SET result_details = %s,
            result_status = %s,
            result_date = NOW()
        WHERE lab_result_id = %s
    """, (
        result_json,
        result_status,
        lab_result_id
    ))

    # Get linked consultation
    cursor.execute("""
        SELECT
            lr.test_type,
            c.consultation_id,
            c.patient_id,
            c.queue_id,
            c.consultation_time,
            c.medical_bill
        FROM lab_result lr
        JOIN consultation c
            ON c.consultation_id = lr.consultation_id
        WHERE lr.lab_result_id = %s
    """, (lab_result_id,))

    lab = cursor.fetchone()

    consultation_id = lab["consultation_id"]
    patient_id = lab["patient_id"]
    queue_id = lab["queue_id"]
    test_type = lab["test_type"]

    consultation_date = lab["consultation_time"].date()
    today = date.today()

    test_price = round(random.uniform(10, 50), 2)

    bill_item_name = (
        "Blood Test"
        if test_type == "blood_test"
        else "Urine Test"
    )

    note = (
        f"{bill_item_name} Result is "
        f"{result_status.capitalize()}."
    )

    # Same day -> add to bill
    if consultation_date == today:

        bill = json.loads(lab["medical_bill"])

        bill[bill_item_name] = test_price

        bill["total_price"] = round(
            float(bill.get("total_price", 0))
            + test_price,
            2
        )

        cursor.execute("""
            UPDATE consultation
            SET medical_bill=%s,
                doctor_notes=CONCAT(
                    IFNULL(doctor_notes,''),
                    '\n',
                    %s
                )
            WHERE consultation_id=%s
        """, (
            json.dumps(bill),
            note,
            consultation_id
        ))

    # Different day -> new consult
    else:

        bill = {
            bill_item_name: test_price,
            "medications": [],
            "total_price": test_price
        }

        cursor.execute("""
            INSERT INTO consultation (
                patient_id,
                doctor_notes,
                visit_type,
                service_type,
                medical_bill,
                consultation_time
            )
            VALUES (
                %s,
                %s,
                'walkin',
                %s,
                %s,
                NOW()
            )
        """, (
            patient_id,
            note,
            test_type,
            json.dumps(bill)
        ))

    cursor.execute("""
        UPDATE walk_in_queue
        SET queue_status='completed'
        WHERE queue_id=%s
    """, (queue_id,))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for("nurse.queue"))

@nurse_bp.route("/consultations")
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
        "nurse/consultations.html",
        consultations=bills,
        total_revenue=round(total_revenue, 2),
        total_consultations=total_consultations,
        role="nurse",
        active_page="consultations"
    )

@nurse_bp.route("/consult_detail/<int:consultation_id>")
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
        "nurse/consult_detail.html",
        bill=bill,
        bill_data=bill_data,
        role="nurse"
    )
    
# patient history
@nurse_bp.route("/patients")
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
        "nurse/patients.html",
        patients=patients,
        role="nurse",
        active_page="patients",
        search=search
    )
    
# patients detail
@nurse_bp.route("/patients/<int:patient_id>")
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
        "nurse/patient_detail.html",
        patient=patient,
        consultations=consultations,
        labels=labels,
        systolic=systolic,
        diastolic=diastolic,
        temperatures=temperatures,
        role="nurse",
        active_page="patients"
    )

# MEDICATION
# @nurse_bp.route("/medication")
# def medication():
#     db = get_db()
#     cursor = db.cursor(dictionary=True)

#     cursor.execute("""
#         SELECT c.consultation_id, p.full_name, c.prescription_notes
#         FROM consultation c
#         JOIN patient p ON p.patient_id = c.patient_id
#         ORDER BY c.consultation_time DESC
#     """)

#     meds = cursor.fetchall()

#     cursor.close()
#     db.close()

#     return render_template("nurse/medication.html", meds=meds, role="nurse")