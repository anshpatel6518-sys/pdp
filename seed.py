from app import app
from models import db, Voter, Candidate

def seed_data():
    with app.app_context():
        db.drop_all()
        db.create_all()

        voters = [
            Voter(aadhaar_id='123456789011', name='Manikanta', age=18, mobile_number='9876543210', fingerprint_id=101),
            Voter(aadhaar_id='234567890123', name='Ansh patel', age=17, mobile_number='9876543211', fingerprint_id=102),
            Voter(aadhaar_id='345678901234', name='P.Kavya', age=18, mobile_number='9876543212', fingerprint_id=103),
            Voter(aadhaar_id='456789012344', name='K.Govardhan', age=18, mobile_number='9876543213', fingerprint_id=104),
            Voter(aadhaar_id='567890123456', name='L.Nagalaxshmi', age=18, mobile_number='9876543214', fingerprint_id=105),
            Voter(aadhaar_id='678901234567', name='Akhil', age=60, mobile_number='9876543215', fingerprint_id=106),
            Voter(aadhaar_id='789012345678', name='D.Praddep', age=22, mobile_number='9876543216', fingerprint_id=107),
            Voter(aadhaar_id='890123456789', name='Dr.Balakrishna', age=35, mobile_number='9876543217', fingerprint_id=108),
            Voter(aadhaar_id='901234567890', name='Akshay', age=50, mobile_number='9876543218', fingerprint_id=109),
            Voter(aadhaar_id='012345678901', name='Ganesh', age=40, mobile_number='9876543219', fingerprint_id=110),
        ]

        candidates = [
            Candidate(name='Arjun Kumar', party='Development Party', logo_filename='dp_logo.svg'),
            Candidate(name='Pooja Bhatt', party='Progressive Alliance', logo_filename='pa_logo.svg'),
            Candidate(name='Sameer Khan', party='National Youth Front', logo_filename='nyf_logo.svg'),
            Candidate(name='Divya Nair', party='Green Future Party', logo_filename='gfp_logo.svg'),
            Candidate(name='Manish Tiwari', party='People\'s Voice', logo_filename='pv_logo.svg'),
        ]

        db.session.add_all(voters)
        db.session.add_all(candidates)
        db.session.commit()
        print("Database seeded completely with 10 voters and 5 candidates!")

if __name__ == '__main__':
    seed_data()
