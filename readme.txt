polyclinic-app/
│
├── .venv                 # create venv file and install all the required lib
├── app.py                # Main Flask application entry point
├── database.db           # Database file (MySQL)
|
│
├── templates/             # HTML pages (frontend)
│   ├── layout/            # Shared layout files
│   │   ├── base.html      # Main template wrapper
│   │   ├── navbar.html   # Top navigation bar
│   │   └── sidebar.html  # Side navigation menu
│   │
│   ├── auth/             # Authentication pages
│   │   └── login.html    # Login page
│   │
│   ├── doctor/           # Doctor dashboard pages
│   │   └── dashboard.html
│   │
│   ├── nurse/            # Nurse dashboard pages
│   │   └── dashboard.html
│   │
│   ├── patient/          # Patient dashboard pages
│   │   └── dashboard.html
│   │
│   └── admin/            # Admin dashboard pages
│       └── dashboard.html
│
├── static/               # CSS, JavaScript, Images
│   ├── css/
│   │   ├── style.css     # Main styling
│   │   ├── navbar.css    # Navbar styling
│   │   └── dashboard.css # Dashboard styling
│   │
│   ├── js/              # JavaScript files (if any)
│   └── images/          # Images (e.g. login healthcare image)
│
├── routes/             # Flask route files (modular structure)
   ├── auth.py          # Login / authentication routes
   ├── doctor.py        # Doctor routes
   ├── nurse.py         # Nurse routes
   ├── patient.py       # Patient routes
   └── admin.py         # Admin routes
