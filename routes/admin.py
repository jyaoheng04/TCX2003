from flask import Blueprint, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
import os

load_dotenv()


admin = Blueprint("admin", __name__)

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

# ADMIN
@admin.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html', role="admin",active_page="dashboard")

@admin.route('/admin/users')
def admin_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT user_id, email, user_type, status
        FROM user_account
        WHERE user_type != 'admin'
        ORDER BY user_id DESC
    """)

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/users.html',
        role="admin",
        active_page="users",
        users=users
    )

@admin.route("/admin/users/edit/<int:id>", methods=["GET", "POST"])
def admin_user_edit(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # =====================
    # UPDATE USER (POST)
    # =====================
    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        user_type = request.form["user_type"]
        status = request.form["status"]
        staff_id = request.form["staff_id"]
        department = request.form["department"]
        specialisation = request.form["specialisation"]

        # 1. update user_account
        cursor.execute("""
            UPDATE user_account
            SET email=%s,
                user_type=%s,
                status=%s
            WHERE user_id=%s
        """, (email, user_type, status, id))

        # 2. update medical_staff
        cursor.execute("""
            UPDATE medical_staff
            SET full_name=%s,
                staff_id=%s,
                department=%s,
                specialisation=%s
            WHERE user_id=%s
        """, (full_name, staff_id, department, specialisation, id))

        conn.commit()

        cursor.close()
        conn.close()

        flash("User updated successfully")
        return redirect("/admin/users")

    # =====================
    # LOAD USER (GET)
    # =====================
    cursor.execute("""
        SELECT 
            ua.user_id,
            ua.email,
            ua.user_type,
            ua.status,
            ms.full_name,
            ms.staff_id,
            ms.department,
            ms.specialisation
        FROM user_account ua
        LEFT JOIN medical_staff ms ON ua.user_id = ms.user_id
        WHERE ua.user_id = %s
    """, (id,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "admin/user_edit.html",
        role="admin",
        active_page="users",
        user=user
    )

@admin.route('/admin/security')
def admin_security():
    return render_template('admin/security.html', role="admin",active_page="security")


@admin.route('/admin/system')
def admin_system():
    return render_template('admin/system.html', role="admin",active_page="system")


@admin.route('/admin/logs')
def admin_logs():
    return render_template('admin/logs.html', role="admin",active_page="logs")