import unittest
import json
import os
from app import app, db
from models import Voter, Candidate, Vote

class VotingAppTestCase(unittest.TestCase):
    def setUp(self):
        # Set up a test database file
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_voting.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Clear existing engine cache in Flask-SQLAlchemy 3.x
        if 'sqlalchemy' in app.extensions:
            sqla = app.extensions['sqlalchemy']
            if hasattr(sqla, '_engines'):
                sqla._engines.clear()
        
        # Drop and recreate tables in the test database
        db.drop_all()
        db.create_all()
        self.seed_test_data()
        
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        # Clean up test database file
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'test_voting.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        db_path_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_voting.db')
        if os.path.exists(db_path_root):
            try:
                os.remove(db_path_root)
            except Exception:
                pass

    def seed_test_data(self):
        # 1. Seed some voters
        self.voters = [
            Voter(aadhaar_id='123456789011', name='Manikanta', age=18, mobile_number='9876543210', fingerprint_id=101),
            Voter(aadhaar_id='234567890123', name='Ansh patel', age=17, mobile_number='9876543211', fingerprint_id=102),
            Voter(aadhaar_id='345678901234', name='P.Kavya', age=18, mobile_number='9876543212', fingerprint_id=103),
        ]
        # 2. Seed candidates
        self.candidates = [
            Candidate(name='Arjun Kumar', party='Development Party', logo_filename='dp_logo.svg'),
            Candidate(name='Pooja Bhatt', party='Progressive Alliance', logo_filename='pa_logo.svg'),
        ]
        db.session.add_all(self.voters)
        db.session.add_all(self.candidates)
        db.session.commit()

    def test_01_landing_page(self):
        print("\n[TEST] Accessing login / landing page...")
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Facial Voter Authentication', response.data)
        print(" -> SUCCESS: Landing page accessed and loaded correctly.")

    def test_02_face_login_invalid_encoding(self):
        print("\n[TEST] Face login with invalid face encoding...")
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": [0.1] * 50}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid face encoding.')
        print(" -> SUCCESS: Handled invalid face encoding array length.")

    def test_03_face_login_unregistered_face(self):
        print("\n[TEST] Face login with unregistered face...")
        # A valid 128-float descriptor
        fake_descriptor = [0.2] * 128
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": fake_descriptor}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Face not recognized. Please register with an admin.')
        print(" -> SUCCESS: Unregistered face rejected as expected.")

    def test_04_admin_login_fail(self):
        print("\n[TEST] Admin login with incorrect PIN...")
        response = self.client.post('/admin/login', data=dict(pin='99999'), follow_redirects=True)
        self.assertIn(b'Invalid Admin PIN.', response.data)
        print(" -> SUCCESS: Rejected invalid PIN.")

    def test_05_admin_login_success(self):
        print("\n[TEST] Admin login with correct PIN...")
        # Correct ADMIN_PIN is '12345'
        response = self.client.post('/admin/login', data=dict(pin='12345'), follow_redirects=True)
        self.assertIn(b'Live Election Results', response.data)
        print(" -> SUCCESS: Logged into Admin portal.")

    def test_06_admin_voter_lookup(self):
        print("\n[TEST] Looking up voter via admin API...")
        # Set up admin session
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
            
        # Lookup existing voter
        response = self.client.get('/api/lookup-voter?aadhaar_id=123456789011')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['name'], 'Manikanta')
        
        # Lookup non-existent voter
        response = self.client.get('/api/lookup-voter?aadhaar_id=999999999999')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Voter not found in system.')
        print(" -> SUCCESS: Lookup API correctly identifies existing and non-existing voters.")

    def test_07_admin_register_face_and_login(self):
        print("\n[TEST] Registering face and authenticating voter...")
        # Set up admin session
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True

        test_descriptor = [0.123] * 128
        response = self.client.post('/api/register-face',
                                   data=json.dumps({
                                       "aadhaar_id": "123456789011",
                                       "face_encoding": test_descriptor
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        print(" -> SUCCESS: Face registered successfully for Manikanta.")

        # Now, try logging in with the same face descriptor
        # Clear session first (log out admin)
        self.client.get('/admin/logout')

        print("[TEST] Logging in with the registered face...")
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": test_descriptor}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect'], '/vote')
        print(" -> SUCCESS: Face recognized and redirected to vote page.")

    def test_08_voting_flow(self):
        print("\n[TEST] Entire voting flow including double-voting prevention...")
        
        # 1. Register face
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        test_descriptor = [0.5] * 128
        self.client.post('/api/register-face',
                         data=json.dumps({
                             "aadhaar_id": "123456789011",
                             "face_encoding": test_descriptor
                         }),
                         content_type='application/json')
        self.client.get('/admin/logout')

        # 2. Login
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": test_descriptor}),
                                   content_type='application/json')
        login_data = json.loads(response.data)
        self.assertTrue(login_data['success'])

        # Set session details representing the successful login redirect flow
        # In Flask test client, session is maintained across requests, but let's ensure it has correct values
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['aadhaar_id'], '123456789011')
            self.assertEqual(sess['name'], 'Manikanta')
            self.assertTrue(sess['face_verified'])

        # 3. Access vote page
        response = self.client.get('/vote')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Arjun Kumar', response.data)
        print(" -> SUCCESS: Vote page loaded and shows candidates.")

        # 4. Submit vote for Arjun Kumar (candidate_id=1)
        response = self.client.post('/submit-vote', data=dict(candidate_id='1'), follow_redirects=True)
        self.assertIn(b'Vote Recorded Successfully!', response.data)
        print(" -> SUCCESS: Vote submitted and confirmation page loaded.")

        # 5. Check database to ensure vote is recorded and voter has_voted is True
        voter = Voter.query.get('123456789011')
        self.assertTrue(voter.has_voted)
        vote_count = Vote.query.filter_by(aadhaar_id='123456789011').count()
        self.assertEqual(vote_count, 1)
        print(" -> SUCCESS: Database records updated correctly.")

        # 6. Attempt to login/vote again (double-voting prevention check)
        # Re-authenticate face
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": test_descriptor}),
                                   content_type='application/json')
        login_data = json.loads(response.data)
        self.assertTrue(login_data['success'])
        self.assertEqual(login_data['redirect'], '/already-voted')
        
        # Accessing the vote page directly with existing session should also redirect
        # Re-set session manually to mimic active authenticated voter
        with self.client.session_transaction() as sess:
            sess['aadhaar_id'] = '123456789011'
            sess['name'] = 'Manikanta'
            sess['face_verified'] = True
            
        response = self.client.get('/vote', follow_redirects=True)
        self.assertIn(b'already cast your vote', response.data)
        print(" -> SUCCESS: Double-voting prevention worked perfectly.")

    def test_09_underage_voter(self):
        print("\n[TEST] Underage voter eligibility check...")
        
        # Ansh patel (234567890123) is age 17 in seed data.
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        test_descriptor = [0.8] * 128
        self.client.post('/api/register-face',
                         data=json.dumps({
                             "aadhaar_id": "234567890123",
                             "face_encoding": test_descriptor
                         }),
                         content_type='application/json')
        self.client.get('/admin/logout')

        # Login
        response = self.client.post('/api/face-login', 
                                   data=json.dumps({"face_encoding": test_descriptor}),
                                   content_type='application/json')
        login_data = json.loads(response.data)
        self.assertTrue(login_data['success'])
        self.assertEqual(login_data['redirect'], '/not-eligible')
        
        # Let's verify that visiting /vote redirects to /not-eligible for underage voter
        with self.client.session_transaction() as sess:
            sess['aadhaar_id'] = '234567890123'
            sess['name'] = 'Ansh patel'
            sess['face_verified'] = True
            
        response = self.client.get('/vote', follow_redirects=True)
        self.assertIn(b'Not Eligible to Vote', response.data)
        print(" -> SUCCESS: Underage voter correctly redirected to not-eligible page.")

if __name__ == '__main__':
    unittest.main()
