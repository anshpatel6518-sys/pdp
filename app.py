from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Voter, Candidate, Vote
from datetime import datetime
import os
import random
from functools import wraps
import requests
import threading
import json
import math

asedir = os.path.abspath(os.path.dirname(__file__)) 
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'super-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(asedir, 'voting.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

ADMIN_PIN = "12345"

# --- GOOGLE SHEETS SETTINGS ---
APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxk0WCaopqz-5hPHaqowoZ6qbW40OUsKtk9gTzgNimDtAT8QeuUDVz8gYNWJbQHgBRT/exec'

def send_to_google_sheets(voter_name, aadhaar_id, candidate_name, party, timestamp):
    try:
        data = {
            "voter_name": voter_name,
            "aadhaar_id": "xxxx-xxxx-" + aadhaar_id[-4:] if aadhaar_id else "FACE-ID",
            "candidate_name": candidate_name,
            "party": party,
            "timestamp": timestamp
        }
        res = requests.post(APPS_SCRIPT_URL, json=data, timeout=5)
        print("Google Sheets Sync:", res.text)
    except Exception as e:
        print(f"Error sending to Google Sheets: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'aadhaar_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_eligibility(voter):
    if voter.age < 18:
        return {"redirect": url_for('not_eligible')}
    if voter.has_voted:
        return {"redirect": url_for('already_voted')}
    return None

def calculate_euclidean_distance(enc1, enc2):
    if len(enc1) != len(enc2): return 999.9
    sum_sq = sum((a - b) ** 2 for a, b in zip(enc1, enc2))
    return math.sqrt(sum_sq)

@app.route('/', methods=['GET'])
def login():
    session.clear()
    return render_template('login.html')

@app.route('/api/face-login', methods=['POST'])
def api_face_login():
    data = request.get_json()
    descriptor = data.get('face_encoding')
    
    if not descriptor or len(descriptor) != 128:
        return jsonify({"success": False, "error": "Invalid face encoding."}), 400
        
    voters = Voter.query.all()
    best_match = None
    min_distance = 0.50 # Tolerance threshold for euclidian facial distance
    
    for v in voters:
        if v.face_encoding:
            db_enc = json.loads(v.face_encoding)
            dist = calculate_euclidean_distance(descriptor, db_enc)
            if dist < min_distance:
                min_distance = dist
                best_match = v
                
    if best_match:
        eligibility = check_eligibility(best_match)
        if eligibility:
            session['aadhaar_id'] = best_match.aadhaar_id
            session['name'] = best_match.name
            return jsonify({"success": True, "redirect": eligibility['redirect']})
            
        session['aadhaar_id'] = best_match.aadhaar_id
        session['name'] = best_match.name
        session['face_verified'] = True
        return jsonify({"success": True, "redirect": url_for('vote')})
        
    return jsonify({"success": False, "error": "Face not recognized. Please register with an admin."}), 401

@app.route('/vote', methods=['GET'])
@login_required
def vote():
    if not session.get('face_verified'):
        return redirect(url_for('login'))
        
    voter = Voter.query.get(session['aadhaar_id'])
    # Need redirect route compatibility hack (login returns dict now)
    eligibility = check_eligibility(voter)
    if eligibility: return redirect(eligibility['redirect'])
        
    candidates = Candidate.query.all()
    return render_template('vote.html', candidates=candidates)

@app.route('/submit-vote', methods=['POST'])
@login_required
def submit_vote():
    if not session.get('face_verified'):
        return redirect(url_for('login'))
        
    voter = Voter.query.get(session['aadhaar_id'])
    eligibility = check_eligibility(voter)
    if eligibility: return redirect(eligibility['redirect'])
        
    candidate_id = request.form.get('candidate_id')
    if not candidate_id:
        flash("Please select a candidate.", "danger")
        return redirect(url_for('vote'))
        
    try:
        new_vote = Vote(aadhaar_id=voter.aadhaar_id, candidate_id=candidate_id)
        voter.has_voted = True
        db.session.add(new_vote)
        db.session.commit()
        
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session['vote_timestamp'] = timestamp_str
        
        candidate = Candidate.query.get(candidate_id)
        if APPS_SCRIPT_URL != 'https://script.google.com/macros/s/AKfycbxk0WCaopqz-5hPHaqowoZ6qbW40OUsKtk9gTzgNimDtAT8QeuUDVz8gYNWJbQHgBRT/exec':
            threading.Thread(
                target=send_to_google_sheets, 
                args=(voter.name, voter.aadhaar_id, candidate.name, candidate.party, timestamp_str)
            ).start()
            
        return redirect(url_for('confirmation'))
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while casting vote. Please try again.", "danger")
        return redirect(url_for('vote'))

@app.route('/confirmation', methods=['GET'])
@login_required
def confirmation():
    voter = Voter.query.get(session['aadhaar_id'])
    if not voter.has_voted:
        return redirect(url_for('vote'))
    
    timestamp = session.get('vote_timestamp', 'Unknown time')
    name = session.get('name')
    session.clear() 
    return render_template('confirmation.html', name=name, timestamp=timestamp)

@app.route('/already-voted')
def already_voted():
    return render_template('already_voted.html')

@app.route('/not-eligible')
def not_eligible():
    return render_template('not_eligible.html')


# === ADMIN ROUTES ===

@app.route('/admin')
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_results'))
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def do_admin_login():
    pin = request.form.get('pin')
    if pin == ADMIN_PIN:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_results'))
    flash("Invalid Admin PIN.", "danger")
    return redirect(url_for('admin_login'))

@app.route('/admin/results')
def admin_results():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    candidates_data = []
    candidates = Candidate.query.all()
    for c in candidates:
        count = Vote.query.filter_by(candidate_id=c.candidate_id).count()
        candidates_data.append({
            'name': c.name,
            'party': c.party,
            'logo_filename': c.logo_filename,
            'votes': count
        })
        
    labels = [f"{c['name']} ({c['party']})" for c in candidates_data]
    data = [c['votes'] for c in candidates_data]
    total_votes = sum(data)
        
    return render_template('results.html', labels=labels, data=data, candidates_data=candidates_data, total_votes=total_votes)

@app.route('/admin/register-voter', methods=['GET'])
def admin_register_voter():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('register_voter.html')

@app.route('/api/lookup-voter', methods=['GET'])
def api_lookup_voter():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    aadhaar_id = request.args.get('aadhaar_id')
    voter = Voter.query.filter_by(aadhaar_id=aadhaar_id).first()
    
    if voter:
        # Check if they already have a face?
        if voter.face_encoding:
            pass # We will allow overwriting it for admin correction
        return jsonify({"success": True, "name": voter.name, "age": voter.age})
    return jsonify({"success": False, "error": "Voter not found in system."})

@app.route('/api/register-face', methods=['POST'])
def api_register_face():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.get_json()
    aadhaar_id = data.get('aadhaar_id')
    descriptor = data.get('face_encoding')
    
    if not aadhaar_id or not descriptor or len(descriptor) != 128:
        return jsonify({"success": False, "error": "Invalid request parameters."})
        
    voter = Voter.query.filter_by(aadhaar_id=aadhaar_id).first()
    if not voter:
        return jsonify({"success": False, "error": "Voter not found."})
        
    try:
        voter.face_encoding = json.dumps(descriptor)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error."})

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5001, debug=False)