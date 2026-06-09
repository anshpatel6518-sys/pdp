from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Voter(db.Model):
    __tablename__ = 'voter'
    aadhaar_id = db.Column(db.String(12), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    mobile_number = db.Column(db.String(15), nullable=True)
    fingerprint_id = db.Column(db.Integer, unique=True, nullable=False)
    face_encoding = db.Column(db.Text, nullable=True) # JSON stored array of face descriptors
    has_voted = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    __tablename__ = 'candidate'
    candidate_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    logo_filename = db.Column(db.String(255), nullable=True)

class Vote(db.Model):
    __tablename__ = 'vote'
    vote_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    aadhaar_id = db.Column(db.String(12), db.ForeignKey('voter.aadhaar_id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.candidate_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
