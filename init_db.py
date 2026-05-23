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
    doctor_id INT,
    appointment_type ENUM('consultation','vaccination','blood_test','urine_test'),
    appointment_date DATETIME,
    status ENUM('booked','completed','cancelled'),
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

conn.commit()
cursor.close()
conn.close()

print("Clean database reset completed successfully!")