If any features or components are not relevant to your assigned role, you may remove them. I have only provided the basic frontend design direction to guide the overall look and feel.
The remaining functionality should be designed by you, but it should still follow a consistent and similar UI style across all pages.
If any data is required to be accessed or displayed in other role-specific pages outside your own scope, please inform the respective person in charge.

Important!! -> Create your own branch, then clone the main branch into your branch and carry out all development work within your assigned branch.

polyclinic-app/
│
├── .venv/                         # Python virtual environment containing installed dependencies
│
├── app.py                         # Main Flask application file used to start the server
├── database.db                    # MySQL database storing application data
│
├── routes/                        # Application route modules (Flask Blueprints / views) (IGNORE THIS, have not implement anything yet everything is route through app.py)
│   ├── admin.py                   # Handles admin management routes and system controls
│   ├── auth.py                    # Handles login, logout, and authentication logic
│   ├── doctor.py                  # Handles doctor dashboard, consultations, and records
│   ├── nurse.py                   # Handles nurse operations, medications, and patient support
│   └── patient.py                 # Handles patient dashboard, appointments, and profile routes
│
├── static/                        # Static frontend assets
│   ├── css/                       # Stylesheet files for UI design
│   │   ├── admin.css              # Styling for admin pages
│   │   ├── dashboard.css          # Shared dashboard styling
│   │   ├── doctor.css             # Styling for doctor interface
│   │   ├── navbar.css             # Styling for top navigation bar
│   │   ├── nurse.css              # Styling for nurse interface
│   │   ├── patient.css            # Styling for patient interface
│   │   └── style.css              # Global application styling
│   │
│   ├── images/                    # Image resources used in the application
│   │   └── healthcare.jpg         # Main healthcare-related image asset
│   │
│   └── js/                        # JavaScript files for frontend interactions
│       └── admin.js               # JavaScript functionality for admin features
│
├── templates/                     # HTML template files rendered by Flask
│   │
│   ├── admin/                     # Admin dashboard and management templates
│   │   ├── dashboard.html         # Main admin dashboard page
│   │   ├── logs.html              # System activity and audit logs page
│   │   ├── security.html          # Security settings and monitoring page
│   │   ├── system.html            # System configuration and overview page
│   │   ├── user_create.html       # Form page for creating new users
│   │   ├── user_edit.html         # Form page for editing user details
│   │   └── users.html             # User management and listing page
│   │
│   ├── auth/                      # Authentication templates
│   │   └── login.html             # User login page
│   │
│   ├── doctor/                    # Doctor-related templates
│   │   ├── consultation.html      # Patient consultation and diagnosis page
│   │   ├── create.html            # Form for creating medical records or consultations
│   │   ├── dashboard.html         # Doctor dashboard overview page
│   │   └── edit.html              # Edit existing consultation or medical records
│   │
│   ├── layout/                    # Shared reusable layout templates
│   │   ├── base.html              # Base template containing common structure
│   │   ├── navbar.html            # Shared top navigation bar
│   │   └── sidebar.html           # Shared sidebar navigation menu
│   │
│   ├── nurse/                     # Nurse-related templates
│   │   ├── clinic_op.html         # Clinic operations and patient assistance page
│   │   ├── dashboard.html         # Nurse dashboard overview page
│   │   ├── medication.html        # Medication management and updates page
│   │   └── patients.html          # Patient monitoring and information page
│   │
│   └── patient/                   # Patient-related templates
│       ├── appointments.html      # Appointment scheduling and history page
│       ├── create.html            # Form for creating patient requests or records
│       ├── dashboard.html         # Patient dashboard overview page
│       ├── profile.html           # Patient personal profile page
│       └── records.html           # Patient medical records and history page
│
└── README.txt                     # Project documentation and setup instructions
