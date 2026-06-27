from flask import Blueprint, Flask, render_template, redirect
from flask import Flask, render_template, redirect, request, flash
from dotenv import load_dotenv
from datetime import datetime
import os
import mysql.connector

from routes.auth import auth
from routes.admin import admin
from routes.patient import patient_bp

from routes.doctor import doctor_bp
from routes.nurse import nurse_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(auth)
app.register_blueprint(admin)

# SECRET KEY
app.secret_key = os.getenv("SECRET_KEY")
# Register blueprint
app.register_blueprint(doctor_bp)
app.register_blueprint(nurse_bp)

# DB CONNECTION
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

@app.route('/logout')
def logout():
    return redirect('/')

app.register_blueprint(patient_bp)

if __name__ == '__main__':
    app.run(debug=True)