import mysql.connector
from dotenv import load_dotenv
import os

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
    username VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    user_type ENUM('patient','doctor','nurse','admin'),
    status ENUM('active','suspended') DEFAULT 'active'
)
""")

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
# MEDICAL STAFF
# ======================
cursor.execute("""
CREATE TABLE medical_staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    full_name VARCHAR(100),
    role ENUM('doctor','nurse'),
    department VARCHAR(100),
    specialisation VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
)
""")

# ======================
# WEB ADMIN
# ======================
cursor.execute("""
CREATE TABLE web_admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    full_name VARCHAR(100),
    admin_role ENUM('account_manager','queue_manager','system_admin'),
    FOREIGN KEY (user_id) REFERENCES user_account(user_id)
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
            'active',
            'completed',
            'cancelled'
        ) DEFAULT 'waiting',

        consultation_room VARCHAR(20),

        FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES medical_staff(staff_id)
    )
    """)

# ======================
# WALK-IN QUEUE
# ======================
cursor.execute("""
CREATE TABLE walk_in_queue (
    queue_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    assigned_staff_id INT,
    managed_by_admin_id INT,
    check_in_time DATETIME,
    priority_status ENUM('priority','regular'),
    queue_status ENUM('waiting','in_consultation','completed','cancelled'),
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (assigned_staff_id) REFERENCES medical_staff(staff_id),
    FOREIGN KEY (managed_by_admin_id) REFERENCES web_admin(admin_id)
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
    medical_bill DECIMAL(10,2),
    rating INT,
    consultation_time DATETIME,

    FOREIGN KEY (appointment_id) REFERENCES appointment(appointment_id),
    FOREIGN KEY (queue_id) REFERENCES walk_in_queue(queue_id),
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (staff_id) REFERENCES medical_staff(staff_id)
)
""")

# ======================
# LAB RESULT
# ======================
cursor.execute("""
CREATE TABLE lab_result (
    lab_result_id INT AUTO_INCREMENT PRIMARY KEY,
    consultation_id INT,
    test_type ENUM('blood_test','urine_test'),
    result_details TEXT,
    result_date DATETIME,
    result_status ENUM('pending','ready'),

    FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id)
)
""")

# ======================
# SAMPLE TEST DATA
# ======================

# ----------------------
# USER ACCOUNTS
# ----------------------
cursor.execute("""
INSERT INTO user_account
(username, password, user_type)
VALUES
('patient1', 'test123', 'patient'),
('doctorA', 'test123', 'doctor'),
('doctorB', 'test123', 'doctor'),
('doctorC', 'test123', 'doctor')
""")

# ----------------------
# PATIENT
# patient_id = 1
# ----------------------
cursor.execute("""
INSERT INTO patient
(
    user_id,
    full_name,
    nric,
    phone,
    email,
    date_of_birth
)
VALUES
(
    1,
    'John Tan',
    'S1234567A',
    '91234567',
    'john@email.com',
    '2001-03-14'
)
""")

# ----------------------
# DOCTORS
# staff_id = 1,2,3
# ----------------------
cursor.execute("""
INSERT INTO medical_staff
(
    user_id,
    full_name,
    role,
    department,
    specialisation
)
VALUES
(
    2,
    'Dr Sarah Lim',
    'doctor',
    'General Medicine',
    'Family Medicine'
),
(
    3,
    'Dr Michael Ong',
    'doctor',
    'Internal Medicine',
    'Cardiology'
),
(
    4,
    'Dr Rachel Lee',
    'doctor',
    'Diagnostics',
    'Pathology'
)
""")

# ----------------------
# APPOINTMENTS
# For testing slot availability
# ----------------------

# Doctor Sarah → 27 Jun 10AM
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
VALUES
(
    1,
    1,
    'consultation',
    'Severe headache',
    '2026-06-27 10:00:00',
    'waiting',
    'Room 3A'
)
""")

# Doctor Michael → same date same time
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
VALUES
(
    1,
    2,
    'consultation',
    'Fever and flu',
    '2026-06-27 10:00:00',
    'waiting',
    'Room 4B'
)
""")

# Doctor Sarah → another slot
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
VALUES
(
    1,
    1,
    'consultation',
    'Chest pain',
    '2026-06-28 11:00:00',
    'active',
    'Room 3A'
)
""")

# Blood Test
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
VALUES
(
    1,
    NULL,
    'blood_test',
    'Routine blood screening',
    '2026-06-29 14:00:00',
    'waiting',
    'Lab 1'
)
""")

# Urine Test
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
VALUES
(
    1,
    NULL,
    'urine_test',
    'Kidney function check',
    '2026-06-29 15:00:00',
    'completed',
    'Lab 2'
)
""")

# Cancelled appointment
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
VALUES
(
    1,
    3,
    'consultation',
    'Back pain',
    '2026-06-30 09:00:00',
    'cancelled',
    'Room 5A'
)
""")

# ----------------------
# CONSULTATION RECORDS
# ----------------------

# consultation_id = 1
cursor.execute("""
INSERT INTO consultation
(
    appointment_id,
    patient_id,
    staff_id,
    visit_type,
    service_type,
    symptoms,
    doctor_notes,
    prescription_notes,
    medical_bill,
    consultation_time
)
VALUES
(
    1,
    1,
    1,
    'appointment',
    'consultation',
    'Migraine',
    'Needs rest',
    'Paracetamol 500mg',
    45.00,
    '2026-06-27 10:00:00'
)
""")

# consultation_id = 2
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
VALUES
(
    4,
    1,
    3,
    'appointment',
    'blood_test',
    '2026-06-29 14:00:00'
)
""")

# ----------------------
# LAB RESULTS
# ----------------------

cursor.execute("""
INSERT INTO lab_result
(
    consultation_id,
    test_type,
    result_details,
    result_date,
    result_status
)
VALUES
(
    2,
    'blood_test',
    '{"Hemoglobin":"13.8","WBC":"6200","Platelets":"250000"}',
    NOW(),
    'ready'
)
""")

conn.commit()
cursor.close()
conn.close()

print("Clean database reset completed successfully!")