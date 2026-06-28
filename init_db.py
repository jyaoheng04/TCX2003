import mysql.connector
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

cursor = conn.cursor()

# ======================
# CLEAN SLATE RESET
# ======================
cursor.execute("DROP DATABASE IF EXISTS polyclinic")
cursor.execute("CREATE DATABASE polyclinic")
cursor.execute("USE polyclinic")

# ======================
# USER ACCOUNT
# ======================
cursor.execute("""
CREATE TABLE user_account (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    user_type ENUM('patient','doctor','nurse','admin'),
    status ENUM('active','suspended') DEFAULT 'active'
)
""")

# ======================
# Create default admin account
# ======================
email = "admin@polyclinic.com"
password = generate_password_hash("Admin@123")

cursor.execute("""
    INSERT INTO user_account (email, password, user_type, status)
    VALUES (%s, %s, %s, %s)
""", (email, password, "admin", "active"))


# ======================
# PATIENT
# ======================
cursor.execute("""
CREATE TABLE patient (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    full_name VARCHAR(100),
    nric VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(100),
    date_of_birth DATE,
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
)
""")

# ======================
# MEDICAL ROOM
# ======================

cursor.execute("""
CREATE TABLE medical_room (
    room_id INT AUTO_INCREMENT PRIMARY KEY,

    room_name VARCHAR(20) NOT NULL UNIQUE,

    room_type ENUM(
        'consultation',
        'laboratory'
    ) NOT NULL,

    status ENUM(
        'available',
        'maintenance'
    ) DEFAULT 'available'
)
""")

# ======================
# MEDICAL STAFF
# ======================
cursor.execute("""
CREATE TABLE medical_staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    room_id INT,
    full_name VARCHAR(100),
    role ENUM('doctor','nurse'),
    department VARCHAR(100),
    specialisation VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES user_account(user_id),
    FOREIGN KEY (room_id) REFERENCES medical_room(room_id)
)
""")

# ======================
# APPOINTMENT
# ======================
cursor.execute("""
    CREATE TABLE appointment (
        appointment_id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id INT,
        doctor_id INT NULL,

        appointment_type ENUM(
            'consultation',
            'blood_test',
            'urine_test'
        ),

        reason TEXT,
        appointment_date DATETIME,

        queue_status ENUM(
            'waiting',
            'in_consultation',
            'completed',
            'cancelled'
        ) DEFAULT 'waiting',

        consultation_room VARCHAR(20),

        FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES medical_staff(staff_id)
    )
    """)

# ======================
# APPOINTMENT QUEUE
# ======================
cursor.execute("""
CREATE TABLE queue (
    queue_id INT AUTO_INCREMENT PRIMARY KEY,

    appointment_id INT NOT NULL,
    patient_id INT NOT NULL,

    assigned_staff_id INT,
    room_id INT NOT NULL,

    queue_number VARCHAR(10) NOT NULL,

    queue_status ENUM(
        'waiting',
        'in_consultation',
        'completed',
        'cancelled'
    ) DEFAULT 'waiting',

    FOREIGN KEY (appointment_id) REFERENCES appointment(appointment_id),
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (assigned_staff_id) REFERENCES medical_staff(staff_id),
    FOREIGN KEY (room_id) REFERENCES medical_room(room_id)
)
""")

# ======================
# CONSULTATION
# ======================
cursor.execute("""
CREATE TABLE consultation (
    consultation_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NULL,
    queue_id INT NULL,
    patient_id INT,
    staff_id INT,

    visit_type ENUM('appointment','walkin'),
    service_type ENUM('consultation','vaccination','blood_test','urine_test'),

    temperature DECIMAL(5,2),
    blood_pressure VARCHAR(20),
    symptoms TEXT,
    doctor_notes TEXT,
    prescription_notes TEXT,
    medical_bill TEXT,
    rating INT,
    consultation_time DATETIME,

    FOREIGN KEY (appointment_id) REFERENCES appointment(appointment_id),
    FOREIGN KEY (queue_id) REFERENCES queue(queue_id),
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (staff_id) REFERENCES medical_staff(staff_id)
)
""")

# ======================
# LAB RESULT  # originally result_status was pending or ready
# ======================
cursor.execute("""
CREATE TABLE lab_result (
    lab_result_id INT AUTO_INCREMENT PRIMARY KEY,
    consultation_id INT,
    test_type ENUM('blood_test','urine_test'),
    result_details TEXT,
    result_date DATETIME,
    result_status ENUM('normal','abnormal'),

    FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id)
)
""")

# ======================
# NOTIFICATION
# ======================
cursor.execute("""
CREATE TABLE notification (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patient(patient_id)
        ON DELETE CASCADE
)
""")

# ==========================================
# DEFAULT MEDICAL ROOMS
# ==========================================

rooms = [
    ("C101", "consultation"),
    ("C102", "consultation"),
    ("C201", "consultation"),
    ("C202", "consultation"),
    ("C301", "consultation"),
    ("C302", "consultation"),
    ("C401", "consultation"),
    ("C402", "consultation"),

    ("LAB01", "laboratory"),
    ("LAB02", "laboratory"),
    ("LAB03", "laboratory"),
    ("LAB04", "laboratory"),
]

for room_name, room_type in rooms:

    cursor.execute("""
        SELECT room_id
        FROM medical_room
        WHERE room_name=%s
    """, (room_name,))

    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO medical_room
            (room_name, room_type)
            VALUES (%s,%s)
        """, (
            room_name,
            room_type
        ))


# ==========================================
# DEFAULT DOCTORS & NURSES
# ==========================================

departments = {
    "General": ["Family Medicine", "Chronic Care"],
    "Emergency": ["Trauma", "Acute Care"],
    "Pediatrics": ["Child Health", "Neonatology"],
    "Surgery": ["Orthopedic", "General Surgery"]
}

consultation_rooms = [
    "C101",
    "C102",
    "C201",
    "C202",
    "C301",
    "C302",
    "C401",
    "C402"
]

laboratory_rooms = [
    "LAB01",
    "LAB01",
    "LAB02",
    "LAB02",
    "LAB03",
    "LAB03",
    "LAB04",
    "LAB04"
]

password = generate_password_hash("Cyberark1")

doctor_no = 1
nurse_no = 1

for department, specialisations in departments.items():

    for specialisation in specialisations:

        # =====================================
        # DOCTOR
        # =====================================

        doctor_email = f"doctor{doctor_no}@clinic.com"

        cursor.execute("""
            SELECT user_id
            FROM user_account
            WHERE email=%s
        """, (doctor_email,))

        if cursor.fetchone() is None:

            cursor.execute("""
                INSERT INTO user_account
                (email,password,user_type,status)
                VALUES (%s,%s,'doctor','active')
            """, (
                doctor_email,
                password
            ))

            doctor_user_id = cursor.lastrowid

            room_name = consultation_rooms[doctor_no - 1]

            cursor.execute("""
                SELECT room_id
                FROM medical_room
                WHERE room_name=%s
            """, (room_name,))

            room_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO medical_staff
                (
                    user_id,
                    room_id,
                    full_name,
                    role,
                    department,
                    specialisation
                )
                VALUES
                (%s,%s,%s,%s,%s,%s)
            """, (
                doctor_user_id,
                room_id,
                f"Doctor {doctor_no}",
                "doctor",
                department,
                specialisation
            ))

        doctor_no += 1


        # =====================================
        # NURSE
        # =====================================

        nurse_email = f"nurse{nurse_no}@clinic.com"

        cursor.execute("""
            SELECT user_id
            FROM user_account
            WHERE email=%s
        """, (nurse_email,))

        if cursor.fetchone() is None:

            cursor.execute("""
                INSERT INTO user_account
                (email,password,user_type,status)
                VALUES (%s,%s,'nurse','active')
            """, (
                nurse_email,
                password
            ))

            nurse_user_id = cursor.lastrowid

            room_name = laboratory_rooms[nurse_no - 1]

            cursor.execute("""
                SELECT room_id
                FROM medical_room
                WHERE room_name=%s
            """, (room_name,))

            room_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO medical_staff
                (
                    user_id,
                    room_id,
                    full_name,
                    role,
                    department,
                    specialisation
                )
                VALUES
                (%s,%s,%s,%s,%s,%s)
            """, (
                nurse_user_id,
                room_id,
                f"Nurse {nurse_no}",
                "nurse",
                department,
                specialisation
            ))

        nurse_no += 1


conn.commit()
cursor.close()
conn.close()

print("Clean database reset completed successfully!")