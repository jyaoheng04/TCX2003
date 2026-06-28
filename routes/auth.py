from flask import Blueprint, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

auth = Blueprint("auth", __name__)


# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )


# =========================
# LOGIN PAGE
# =========================
@auth.route("/")
def login_page():
    return render_template("auth/login.html")


# =========================
# LOGIN ACTION
# =========================
@auth.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM user_account WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and check_password_hash(user["password"], password):

        session["user_id"] = user["user_id"]
        session["role"] = user["user_type"]

        if user["user_type"] == "admin":
            return redirect("/admin/dashboard")
        elif user["user_type"] == "doctor":
            return redirect("/doctor/dashboard")
        elif user["user_type"] == "nurse":
            return redirect("/nurse/dashboard")
        elif user["user_type"] == "patient":
            return redirect("/patient/dashboard")

    flash("Invalid email or password")
    return redirect("/")


# =========================
# REGISTER PAGE
# =========================
@auth.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")


# =========================
# REGISTER ACTION PATIENT
# =========================
@auth.route("/register", methods=["POST"])
def register():

    first_name = request.form["fname"]
    last_name = request.form["lname"]
    full_name = f"{first_name} {last_name}"
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]
    nric = request.form["nric"]
    phone = request.form["phone"]
    dob = request.form["date_of_birth"]

    if password != confirm_password:
        flash("Passwords do not match")
        return redirect("/register")

    conn = get_db()
    cursor = conn.cursor()

    try:
        # check duplicate
        cursor.execute(
            "SELECT user_id FROM user_account WHERE email=%s",
            (email,)
        )

        if cursor.fetchone():
            flash("Email already registered")
            return redirect("/register")

        # hash password
        hashed_password = generate_password_hash(password)

        # insert useraccount
        cursor.execute("""
            INSERT INTO user_account (email, password, user_type, status)
            VALUES (%s, %s, 'patient', 'active')
        """, (email, hashed_password))

        user_id = cursor.lastrowid

        # insert patient
        cursor.execute("""
            INSERT INTO patient (user_id, full_name, nric, phone, email, date_of_birth)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, full_name, nric, phone, email, dob))

        conn.commit()

        flash("Registration successful")
        return redirect("/")

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        flash(str(e))
        raise

    finally:
        cursor.close()
        conn.close()

# =========================
# REGISTER ACTION MEDICAL STAFF
# =========================
@auth.route("/Register_MedicalStaff", methods=["POST"])
def register_medical_staff():

    first_name = request.form["fname"]
    last_name = request.form["lname"]
    full_name = f"{first_name} {last_name}"
    department = request.form["department"]
    specialisation = request.form["specialisation"]
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    role = request.form.get("role")  # 👈 IMPORTANT

    # whitelist roles
    if role not in ["doctor", "nurse"]:
        flash("Invalid role")
        return redirect("/register")

    if password != confirm_password:
        flash("Passwords do not match")
        return redirect("/register")

    conn = get_db()
    cursor = conn.cursor()

    try:
        # check duplicate email
        cursor.execute(
            "SELECT user_id FROM user_account WHERE email=%s",
            (email,)
        )

        if cursor.fetchone():
            flash("Email already registered")
            return redirect("/Register_MedicalStaff?role=" + role)

        hashed_password = generate_password_hash(password)

        # insert user account with role
        cursor.execute("""
            INSERT INTO user_account (email, password, user_type, status)
            VALUES (%s, %s, %s, 'active')
        """, (email, hashed_password, role))

        user_id = cursor.lastrowid

        # OPTIONAL: store staff info (no patient table anymore)
        cursor.execute("""
            INSERT INTO medical_staff (user_id, full_name, role, department, specialisation)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, full_name, role, department, specialisation))

        conn.commit()

        flash(f"{role.capitalize()} registration successful")
        return redirect("/")

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        flash(str(e))
        return redirect("/Register_MedicalStaff?role=" + role)

    finally:
        cursor.close()
        conn.close()


# =========================
# LOGOUT
# =========================
@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/")