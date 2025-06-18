from flask import Blueprint, request, jsonify
from models.case import Case
from models.person import Person
from utils.face_recognition import compare_faces
from utils.sms_service import send_match_notification, TabaarakSMS
import base64
import numpy as np
import cv2
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/api/match_face', methods=['POST'])
def match_face():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]  # Remove data URL prefix
        location = data['location']
        
        # Convert base64 to image
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get all open cases
        open_cases = Case.query.filter_by(status='Open').all()
        
        for case in open_cases:
            # Compare face with missing person's photo
            if compare_faces(img, case.person.photo):
                # Prepare person data for SMS
                person_data = {
                    'age': case.person.age,
                    'gender': case.person.gender,
                    'description': case.person.description,
                    'last_seen': case.last_seen_at.strftime('%Y-%m-%d %H:%M') if case.last_seen_at else None
                }
                
                # Automatically send notification to guardian using new SMS service
                success, message, message_id = send_match_notification(
                    case.guardian_phone,
                    case.person.name,
                    location,
                    person_data
                )
                
                if success:
                    # Update case with location
                    case.last_seen_location = f"{location['latitude']}, {location['longitude']}"
                    case.last_seen_address = location['address']
                    case.last_seen_at = datetime.fromisoformat(location['timestamp'])
                    case.save()
                
                return jsonify({
                    'match': True,
                    'person': {
                        'name': case.person.name,
                        'case_id': case.id,
                        'notification_sent': success,
                        'notification_error': None if success else message,
                        'message_id': message_id
                    }
                })
        
        return jsonify({'match': False})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/api/notify_guardian', methods=['POST'])
def notify_guardian():
    try:
        data = request.json
        case_id = data['case_id']
        location = data['location']
        
        # Get case details
        case = Case.query.get(case_id)
        if not case:
            return jsonify({'success': False, 'error': 'Case not found'})
        
        # Prepare person data for SMS
        person_data = {
            'age': case.person.age,
            'gender': case.person.gender,
            'description': case.person.description,
            'last_seen': case.last_seen_at.strftime('%Y-%m-%d %H:%M') if case.last_seen_at else None
        }
        
        # Send SMS notification using new service
        success, message, message_id = send_match_notification(
            case.guardian_phone,
            case.person.name,
            location,
            person_data
        )
        
        if success:
            # Update case with location
            case.last_seen_location = f"{location['latitude']}, {location['longitude']}"
            case.last_seen_address = location['address']
            case.last_seen_at = datetime.fromisoformat(location['timestamp'])
            case.save()
            
            return jsonify({
                'success': True,
                'message_id': message_id
            })
        else:
            return jsonify({'success': False, 'error': message})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route('/api/sms/status/<message_id>', methods=['GET'])
def check_sms_status(message_id):
    """
    Check the delivery status of an SMS message
    """
    try:
        sms_service = TabaarakSMS()
        status, details = sms_service.check_delivery_status(message_id)
        
        return jsonify({
            'success': True,
            'status': status,
            'details': details
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 