import os
import cv2
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import base64
from datetime import datetime
import uuid
import logging
from models import db, User, Case, Photo, Activity
from utils.sms_service import send_match_notification
from functools import wraps
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateField, MultipleFileField
from wtforms.validators import DataRequired, NumberRange
import face_recognition
import pickle
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///missing_persons.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Create data directories if they don't exist
os.makedirs('data/faces', exist_ok=True)
os.makedirs('data/encodings', exist_ok=True)
os.makedirs('data/uploads', exist_ok=True)

# Path to store face encodings and user data
ENCODINGS_FILE = 'data/encodings/encodings.json'
USER_DATA_FILE = 'data/encodings/user_data.json'

# Log paths and environment
app.logger.info(f"Current working directory: {os.getcwd()}")
app.logger.info(f"ENCODINGS_FILE path: {os.path.abspath(ENCODINGS_FILE)}")
app.logger.info(f"USER_DATA_FILE path: {os.path.abspath(USER_DATA_FILE)}")
app.logger.info(f"Faces directory: {os.path.abspath('data/faces')}")

# Load face detection cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize face recognition model
def load_face_encodings():
    if os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            app.logger.error(f"Error loading face encodings: {str(e)}")
            return {"ids": [], "encodings": []}
    return {"ids": [], "encodings": []}

def save_face_encodings(encodings_data):
    try:
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(encodings_data, f)
    except Exception as e:
        app.logger.error(f"Error saving face encodings: {str(e)}")

# Load face encodings at startup
face_encodings_data = load_face_encodings()

# Initialize user data dictionary
if os.path.exists(USER_DATA_FILE):
    try:
        with open(USER_DATA_FILE, 'r') as f:
            try:
                user_data = json.load(f)
                app.logger.info(f"Loaded user data with {len(user_data)} users")
            except json.JSONDecodeError:
                app.logger.warning(f"Invalid JSON in {USER_DATA_FILE}, initializing empty user data")
                user_data = {}
    except Exception as e:
        app.logger.error(f"Error opening {USER_DATA_FILE}: {str(e)}")
        user_data = {}
else:
    app.logger.info(f"{USER_DATA_FILE} does not exist, initializing empty user data")
    user_data = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Activity logging function
def log_activity(action, details, user_id=None):
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id
    activity = Activity(
        action=action,
        details=details,
        user_id=user_id
    )
    db.session.add(activity)
    db.session.commit()

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            log_activity('login', f'User {user.username} logged in')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

# Admin registration token - change this to a secure random string in production
ADMIN_REGISTRATION_TOKEN = secrets.token_urlsafe(32)

@app.route('/register-admin/<token>', methods=['GET', 'POST'])
def register_admin(token):
    if token != ADMIN_REGISTRATION_TOKEN:
        flash('Invalid registration token', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register_admin', token=token))
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='admin'  # Set role as admin
        )
        db.session.add(user)
        db.session.commit()
        
        log_activity('admin_registration', f'New admin registered: {username}')
        flash('Admin registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_admin.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        total_cases = Case.query.count()
        total_users = User.query.count()
        found_cases = Case.query.filter_by(status='found').count()
        pending_cases = Case.query.filter_by(status='missing').count()
        resolved_cases = found_cases
        recent_cases = Case.query.order_by(Case.created_at.desc()).limit(5).all()
        recent_activity = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        # Calculate storage usage (example)
        storage_usage = 45  # placeholder value
        api_requests = 150  # placeholder value
        
        # Activity chart data (example)
        activity_dates = ['2024-01', '2024-02', '2024-03']  # placeholder
        case_activity = [5, 8, 12]  # placeholder
        user_activity = [2, 4, 6]  # placeholder
        
        return render_template('admin_dashboard.html', 
                             total_cases=total_cases,
                             total_users=total_users,
                             found_cases=found_cases,
                             pending_cases=pending_cases,
                             resolved_cases=resolved_cases,
                             recent_cases=recent_cases,
                             recent_activity=recent_activity,
                             recent_users=recent_users,
                             storage_usage=storage_usage,
                             api_requests=api_requests,
                             activity_dates=activity_dates,
                             case_activity=case_activity,
                             user_activity=user_activity)
    else:
        user_cases = Case.query.filter_by(reporter_id=current_user.id).all()
        return render_template('user_dashboard.html', user_cases=user_cases)

class NewCaseForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=0, max=120)])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('male', 'Male'), ('female', 'Female')], validators=[DataRequired()])
    last_seen_location = StringField('Last Known Location', validators=[DataRequired()])
    last_seen_date = DateField('Last Seen Date', validators=[DataRequired()])
    guardian_name = StringField('Guardian Name', validators=[DataRequired()])
    guardian_phone = StringField('Guardian Phone', validators=[DataRequired()])
    photos = MultipleFileField('Photos')

@app.route('/new-case', methods=['GET', 'POST'])
@login_required
def new_case():
    form = NewCaseForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        name = form.name.data
        age = form.age.data
        gender = form.gender.data
        last_seen_location = form.last_seen_location.data
        last_seen_date = form.last_seen_date.data
        guardian_name = form.guardian_name.data
        guardian_phone = form.guardian_phone.data
        
        case = Case(
            name=name,
            age=age,
            gender=gender,
            last_seen_location=last_seen_location,
            last_seen_date=last_seen_date,
            guardian_name=guardian_name,
            guardian_phone=guardian_phone,
            reporter_id=current_user.id
        )
        db.session.add(case)
        db.session.commit()
        
        # Handle photo uploads
        photos = request.files.getlist('photos')
        for photo in photos:
            if photo:
                filename = f"{case.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_path = os.path.join('data/faces', filename)
                photo.save(photo_path)
                
                # Load image and detect face
                image = face_recognition.load_image_file(photo_path)
                face_locations = face_recognition.face_locations(image)
                
                if len(face_locations) > 0:
                    # Get face encoding
                    face_encoding = face_recognition.face_encodings(image, face_locations)[0]
                    
                    # Store face encoding
                    face_encodings_data["ids"].append(str(case.id))
                    face_encodings_data["encodings"].append(face_encoding)
                    save_face_encodings(face_encodings_data)
                    
                    # Store face location data
                    face_data = {
                        'top': int(face_locations[0][0]),
                        'right': int(face_locations[0][1]),
                        'bottom': int(face_locations[0][2]),
                        'left': int(face_locations[0][3])
                    }
                    
                    photo_record = Photo(
                        filename=filename,
                        face_encoding=json.dumps(face_data),
                        case_id=case.id
                    )
                    db.session.add(photo_record)
        
        db.session.commit()
        log_activity('new_case', f'New case registered: {name}')
        flash('Case registered successfully', 'success')
        return redirect(url_for('view_cases'))
    
    return render_template('new_case.html', form=form)

@app.route('/cases')
@login_required
def view_cases():
    if current_user.role == 'admin':
        cases = Case.query.all()
    else:
        cases = Case.query.filter_by(reporter_id=current_user.id).all()
    return render_template('cases.html', cases=cases)

@app.route('/case/<int:case_id>')
@login_required
def case_details(case_id):
    case = Case.query.get_or_404(case_id)
    if current_user.role != 'admin' and case.reporter_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('view_cases'))
    return render_template('case_details.html', case=case)

@app.route('/scan')
@login_required
def scan():
    return render_template('scan.html')

@app.route('/api/scan', methods=['POST'])
@login_required
def api_scan():
    try:
        # Get the base64 image from the request
        face_image_base64 = request.form['face_image'].split(',')[1]
        face_image_data = base64.b64decode(face_image_base64)
        
        # Convert image data to numpy array
        nparr = np.frombuffer(face_image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({"success": False, "message": "Failed to load image"}), 400
        
        # Convert to RGB for face_recognition
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) == 0:
            return jsonify({"success": False, "message": "No face detected in the image"}), 400
        
        # Get face encoding
        face_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]
        
        # Compare with all stored face encodings
        matches = []
        if len(face_encodings_data["encodings"]) > 0:
            # Compare face encoding with all stored encodings
            face_distances = face_recognition.face_distance(face_encodings_data["encodings"], face_encoding)
            
            # Get matches with distance less than 0.6 (lower is better)
            match_indices = np.where(face_distances < 0.6)[0]
            
            for idx in match_indices:
                case_id = face_encodings_data["ids"][idx]
                case = Case.query.get(case_id)
                
                if case:
                    # Calculate confidence (convert distance to percentage)
                    confidence = (1 - face_distances[idx]) * 100
                    
                    # Send SMS notification
                    success, message, message_id = send_match_notification(
                        case.guardian_phone,
                        case.name,
                        {
                            'latitude': request.form.get('latitude', '0'),
                            'longitude': request.form.get('longitude', '0'),
                            'address': request.form.get('address', 'Unknown location'),
                            'timestamp': datetime.now().isoformat()
                        },
                        {
                            'guardian_name': case.guardian_name,
                            'age': case.age,
                            'gender': case.gender
                        }
                    )
                    
                    matches.append({
                        'case_id': case.id,
                        'name': case.name,
                        'age': case.age,
                        'gender': case.gender,
                        'last_seen_location': case.last_seen_location,
                        'last_seen_date': case.last_seen_date.strftime('%Y-%m-%d'),
                        'guardian_name': case.guardian_name,
                        'guardian_phone': case.guardian_phone,
                        'match_confidence': round(confidence, 1),
                        'notification_sent': success,
                        'notification_error': None if success else message,
                        'message_id': message_id
                    })
        
        return jsonify({
            "success": True, 
            "matches": matches
        })
        
    except Exception as e:
        app.logger.error(f"Error in face scanning: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        db.session.commit()
        log_activity('profile_update', f'User {current_user.username} updated profile')
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    if not check_password_hash(current_user.password, current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('profile'))
    
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    log_activity('password_change', f'User {current_user.username} changed password')
    flash('Password changed successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    log_activity('logout', f'User {current_user.username} logged out')
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/case/<int:case_id>/status', methods=['POST'])
@login_required
@admin_required
def update_case_status(case_id):
    case = Case.query.get_or_404(case_id)
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['missing', 'found']:
        return jsonify({"success": False, "message": "Invalid status"}), 400
    
    case.status = new_status
    db.session.commit()
    
    log_activity('status_update', f'Case {case.name} status updated to {new_status}')
    return jsonify({"success": True})

@app.route('/api/case/<int:case_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        
        # Delete associated photos from database first
        for photo in case.photos:
            try:
                # Try to delete the physical file
                photo_path = os.path.join('data/faces', photo.filename)
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            except Exception as e:
                app.logger.error(f"Error deleting photo file {photo.filename}: {str(e)}")
            # Delete the photo record from database
            db.session.delete(photo)
        
        # Delete the case
        db.session.delete(case)
        db.session.commit()
        
        log_activity('case_deleted', f'Case {case.name} deleted')
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting case {case_id}: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/api/user/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_role = data.get('role')
    
    if new_role not in ['user', 'admin']:
        return jsonify({"success": False, "message": "Invalid role"}), 400
    
    user.role = new_role
    db.session.commit()
    
    log_activity('role_update', f'User {user.username} role updated to {new_role}')
    return jsonify({"success": True})

@app.route('/api/user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Delete associated cases and photos
    for case in user.cases:
        for photo in case.photos:
            photo_path = os.path.join('data/faces', photo.filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        db.session.delete(case)
    
    db.session.delete(user)
    db.session.commit()
    
    log_activity('user_deleted', f'User {user.username} deleted')
    return jsonify({"success": True})

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    if current_user.role == 'admin':
        # Get date range filters from request and handle None values
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Base query for cases
        cases_query = Case.query
        
        # Apply date filters if provided and not empty
        if start_date and start_date.strip():
            cases_query = cases_query.filter(Case.created_at >= start_date)
        if end_date and end_date.strip():
            cases_query = cases_query.filter(Case.created_at <= end_date)
        
        # Get overall statistics
        total_users = User.query.count()
        total_cases = cases_query.count()
        found_cases = cases_query.filter_by(status='found').count()
        missing_cases = cases_query.filter_by(status='missing').count()
        success_rate = (found_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Get cases by location - Convert to list of tuples and filter out None values
        location_stats = db.session.query(
            Case.last_seen_location,
            db.func.count(Case.id)
        ).filter(Case.id.in_(cases_query.with_entities(Case.id)))\
        .filter(Case.last_seen_location.isnot(None))\
        .group_by(Case.last_seen_location).all()
        location_stats = [(str(loc), int(count)) for loc, count in location_stats if loc]
        
        # Get cases by month - Convert to list of tuples and filter out None values
        month_stats = db.session.query(
            db.func.strftime('%Y-%m', Case.created_at),
            db.func.count(Case.id)
        ).filter(Case.id.in_(cases_query.with_entities(Case.id)))\
        .filter(Case.created_at.isnot(None))\
        .group_by(db.func.strftime('%Y-%m', Case.created_at))\
        .order_by(db.func.strftime('%Y-%m', Case.created_at)).all()
        month_stats = [(str(month), int(count)) for month, count in month_stats if month]
        
        # Get age group statistics - Convert to list of tuples and filter out None values
        age_stats = db.session.query(
            db.case(
                [
                    (Case.age < 18, 'Under 18'),
                    (Case.age.between(18, 30), '18-30'),
                    (Case.age.between(31, 50), '31-50'),
                    (Case.age > 50, 'Over 50')
                ],
                else_='Unknown'
            ).label('age_group'),
            db.func.count(Case.id)
        ).filter(Case.id.in_(cases_query.with_entities(Case.id)))\
        .filter(Case.age.isnot(None))\
        .group_by('age_group').all()
        age_stats = [(str(age), int(count)) for age, count in age_stats if age]
        
        # Get gender statistics - Convert to list of tuples and filter out None values
        gender_stats = db.session.query(
            Case.gender,
            db.func.count(Case.id)
        ).filter(Case.id.in_(cases_query.with_entities(Case.id)))\
        .filter(Case.gender.isnot(None))\
        .group_by(Case.gender).all()
        gender_stats = [(str(gender), int(count)) for gender, count in gender_stats if gender]
        
        # Get recent cases - Convert to list of dictionaries and handle None values
        recent_cases = cases_query.order_by(Case.created_at.desc()).limit(10).all()
        recent_cases_list = []
        for case in recent_cases:
            if case.name and case.created_at:  # Only include cases with required fields
                recent_cases_list.append({
                    'name': case.name or 'Unknown',
                    'age': case.age or 'N/A',
                    'gender': case.gender or 'Unknown',
                    'last_seen_location': case.last_seen_location or 'Unknown',
                    'status': case.status or 'Unknown',
                    'created_at': case.created_at
                })
        
        # Get user registration trend - Convert to list of tuples and filter out None values
        user_reg_stats = db.session.query(
            db.func.strftime('%Y-%m', User.created_at),
            db.func.count(User.id)
        ).filter(User.created_at.isnot(None))\
        .group_by(db.func.strftime('%Y-%m', User.created_at))\
        .order_by(db.func.strftime('%Y-%m', User.created_at)).all()
        user_reg_stats = [(str(month), int(count)) for month, count in user_reg_stats if month]
        
        return render_template('reports.html',
                             is_admin=True,
                             total_users=total_users,
                             total_cases=total_cases,
                             found_cases=found_cases,
                             missing_cases=missing_cases,
                             success_rate=success_rate,
                             location_stats=location_stats,
                             month_stats=month_stats,
                             age_stats=age_stats,
                             gender_stats=gender_stats,
                             recent_cases=recent_cases_list,
                             user_reg_stats=user_reg_stats,
                             start_date=start_date or '',
                             end_date=end_date or '')
    else:
        # Regular user reports
        cases_query = Case.query.filter_by(reporter_id=current_user.id)
        total_cases = cases_query.count()
        found_cases = cases_query.filter_by(status='found').count()
        missing_cases = cases_query.filter_by(status='missing').count()
        success_rate = (found_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Get cases by location for user - Filter out None values
        location_stats = db.session.query(
            Case.last_seen_location,
            db.func.count(Case.id)
        ).filter(Case.reporter_id == current_user.id)\
        .filter(Case.last_seen_location.isnot(None))\
        .group_by(Case.last_seen_location).all()
        location_stats = [(str(loc), int(count)) for loc, count in location_stats if loc]
        
        # Get cases by month for user - Filter out None values
        month_stats = db.session.query(
            db.func.strftime('%Y-%m', Case.created_at),
            db.func.count(Case.id)
        ).filter(Case.reporter_id == current_user.id)\
        .filter(Case.created_at.isnot(None))\
        .group_by(db.func.strftime('%Y-%m', Case.created_at))\
        .order_by(db.func.strftime('%Y-%m', Case.created_at)).all()
        month_stats = [(str(month), int(count)) for month, count in month_stats if month]
        
        # Get age stats for user's cases - Filter out None values
        age_stats = db.session.query(
            db.case(
                [
                    (Case.age < 18, 'Under 18'),
                    (Case.age.between(18, 30), '18-30'),
                    (Case.age.between(31, 50), '31-50'),
                    (Case.age > 50, 'Over 50')
                ],
                else_='Unknown'
            ).label('age_group'),
            db.func.count(Case.id)
        ).filter(Case.reporter_id == current_user.id)\
        .filter(Case.age.isnot(None))\
        .group_by('age_group').all()
        age_stats = [(str(age), int(count)) for age, count in age_stats if age]
        
        # Get gender stats for user's cases - Filter out None values
        gender_stats = db.session.query(
            Case.gender,
            db.func.count(Case.id)
        ).filter(Case.reporter_id == current_user.id)\
        .filter(Case.gender.isnot(None))\
        .group_by(Case.gender).all()
        gender_stats = [(str(gender), int(count)) for gender, count in gender_stats if gender]
        
        return render_template('reports.html',
                             is_admin=False,
                             total_cases=total_cases,
                             found_cases=found_cases,
                             missing_cases=missing_cases,
                             success_rate=success_rate,
                             location_stats=location_stats,
                             month_stats=month_stats,
                             age_stats=age_stats,
                             gender_stats=gender_stats)

# Export functions
def export_to_excel():
    # Create a BytesIO object to store the Excel file
    output = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Cases sheet
        cases_data = []
        cases_query = Case.query if current_user.role == 'admin' else Case.query.filter_by(reporter_id=current_user.id)
        for case in cases_query.all():
            cases_data.append({
                'Name': case.name,
                'Age': case.age,
                'Gender': case.gender,
                'Last Seen Location': case.last_seen_location,
                'Last Seen Date': case.last_seen_date.strftime('%Y-%m-%d'),
                'Status': case.status,
                'Guardian Name': case.guardian_name,
                'Guardian Phone': case.guardian_phone,
                'Created At': case.created_at.strftime('%Y-%m-%d')
            })
        pd.DataFrame(cases_data).to_excel(writer, sheet_name='Cases', index=False)
        
        if current_user.role == 'admin':
            # Users sheet (admin only)
            users_data = []
            for user in User.query.all():
                users_data.append({
                    'Username': user.username,
                    'Email': user.email,
                    'Role': user.role,
                    'Created At': user.created_at.strftime('%Y-%m-%d'),
                    'Total Cases': len(user.cases)
                })
            pd.DataFrame(users_data).to_excel(writer, sheet_name='Users', index=False)
            
            # Activity sheet (admin only)
            activity_data = []
            for activity in Activity.query.all():
                activity_data.append({
                    'Action': activity.action,
                    'Details': activity.details,
                    'Timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'User': activity.user.username if activity.user else 'System'
                })
            pd.DataFrame(activity_data).to_excel(writer, sheet_name='Activity Log', index=False)
    
    output.seek(0)
    return output

def export_to_pdf():
    # Create a BytesIO object to store the PDF file
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title = "Missing Person Finder System Report"
    if not current_user.role == 'admin':
        title += f" - Cases for {current_user.username}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Cases table
    elements.append(Paragraph("Cases Overview", styles['Heading1']))
    cases_data = [['Name', 'Age', 'Gender', 'Status', 'Last Seen', 'Date']]
    cases_query = Case.query if current_user.role == 'admin' else Case.query.filter_by(reporter_id=current_user.id)
    for case in cases_query.all():
        cases_data.append([
            case.name,
            str(case.age),
            case.gender,
            case.status,
            case.last_seen_location,
            case.last_seen_date.strftime('%Y-%m-%d')
        ])
    cases_table = Table(cases_data)
    cases_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(cases_table)
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Statistics
    elements.append(Paragraph("Statistics", styles['Heading1']))
    total_cases = cases_query.count()
    found_cases = cases_query.filter_by(status='found').count()
    success_rate = (found_cases / total_cases * 100) if total_cases > 0 else 0
    
    stats_data = [
        ['Total Cases', str(total_cases)],
        ['Found Cases', str(found_cases)],
        ['Success Rate', f"{success_rate:.1f}%"]
    ]
    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(stats_table)
    
    # Build PDF
    doc.build(elements)
    output.seek(0)
    return output

@app.route('/face/<filename>')
@login_required
def serve_face(filename):
    return send_from_directory('data/faces', filename)

@app.route('/export/<format>')
@login_required
def export_data(format):
    if format == 'excel':
        output = export_to_excel()
        filename = 'all_cases_report' if current_user.role == 'admin' else f'my_cases_report_{current_user.username}'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{filename}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_to_pdf()
        filename = 'all_cases_report' if current_user.role == 'admin' else f'my_cases_report_{current_user.username}'
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{filename}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Invalid export format', 'error')
        return redirect(url_for('reports'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        log_activity('registration', f'New user registered: {username}')
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True) 