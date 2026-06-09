# Secure Digital Voting Prototype

A complete Aadhaar-inspired digital voting prototype web app using Python, Flask, SQLAlchemy, SQLite, Jinja2, Bootstrap 5, and Chart.js.

## Features

- **Voter Authentication**: Verifies Aadhaar ID and Name
- **2FA OTP**: Simulated OTP generation and validation
- **Eligibility Checking**: Ensures user is $\geq$ 18 and hasn't voted yet
- **Secure Voting**: Votes are recorded through a single atomary DB transaction
- **Admin Dashboard**: Live, auto-refreshing polling results using Chart.js
- **Hardware Endpoint API**: Simulate external fingerprint sensor integration (`/api/verify-finger?fingerprint_id=X`)

## Requirements

- Python 3.8+
- Flask
- Flask-SQLAlchemy

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install flask flask-sqlalchemy
   ```

2. **Initialize Database and Seed Dummy Data**:
   This app ships with a seed script that creates necessary tables and generates 10 dummy voters and 5 candidates.
   ```bash
   python seed.py
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the Portal**:
   - Voter Portal: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
   - Admin Portal: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) (PIN: `12345`)

## Sample Data

**Valid Voters** (Name / Aadhaar):
- Amit Sharma / 123456789012 
- Rahul Verma / 345678901234
- Sneha Patil / 456789012345
- Rohan Das / 789012345678

**Ineligible (Under 18)**:
- Priya Singh / 234567890123
- Vikram Reddy / 567890123456

### Fingerprint API
Test the JSON endpoint simulating a fingerprint hardware interface:
`http://127.0.0.1:5000/api/verify-finger?fingerprint_id=101`
