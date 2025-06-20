import requests
from urllib.parse import quote
import time
from datetime import datetime

class TabaarakSMS:
    def __init__(self):
        self.base_url = "https://tabaarakict.so/SendSMS.aspx"
        self.username = "Find"
        self.password = "Find@!2@25"
        self.contact_number = "619837755"  # Default contact number
        
    def get_address_from_coordinates(self, latitude, longitude):
        """
        Get address from coordinates using reverse geocoding
        """
        try:
            # Using Nominatim for reverse geocoding (free, no API key required)
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&accept-language=so"
            headers = {
                'User-Agent': 'MissingPersonFinder/1.0'  # Required by Nominatim
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Get the display name in Somali if available
                address = data.get('display_name', '')
                return address
            return None
        except Exception:
            return None
    
    def send_sms(self, recipient_number, message):
        """
        Send SMS using Tabaarak ICT service
        :param recipient_number: The recipient's phone number (should be in format 61XXXXXX)
        :param message: The message to send
        :return: tuple (success: bool, response/error message: str, message_id: str)
        """
        try:
            # Format the phone number
            # Remove any non-digit characters
            formatted_number = ''.join(filter(str.isdigit, str(recipient_number)))
            
            # Remove country code if present (252 or +252)
            if formatted_number.startswith('252'):
                formatted_number = formatted_number[3:]
            
            # Remove leading 0 if present
            if formatted_number.startswith('0'):
                formatted_number = formatted_number[1:]
            
            # Ensure number starts with 61
            if not formatted_number.startswith('61'):
                if len(formatted_number) >= 7:
                    # Take the last 7 digits and prepend 61
                    formatted_number = '61' + formatted_number[-7:]
                else:
                    return False, "Invalid phone number length", None
            
            # Ensure exactly 9 digits (61 + 7 digits)
            if len(formatted_number) != 9:
                formatted_number = formatted_number[:9]
            
            print(f"Formatted Somalia number: {formatted_number}")  # Debug log
            
            # URL encode the message
            encoded_message = quote(message)
            
            # Construct the URL with parameters
            url = f"{self.base_url}?user={self.username}&pass={self.password}&cont={encoded_message}&rec={formatted_number}"
            
            # Send the request
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Generate a unique message ID (you can modify this based on Tabaarak's response format)
                message_id = f"MSG_{int(time.time())}_{recipient_number}"
                return True, "Message sent successfully", message_id
            else:
                return False, f"Failed to send message. Status code: {response.status_code}", None
                
        except Exception as e:
            return False, str(e), None
            
    def check_delivery_status(self, message_id):
        """
        Check the delivery status of an SMS
        :param message_id: The message ID returned from send_sms
        :return: tuple (status: str, details: str)
        """
        try:
            # Construct the status check URL (modify this based on Tabaarak's API)
            url = f"{self.base_url}/status?user={self.username}&pass={self.password}&msgid={message_id}"
            
            # Send the request
            response = requests.get(url)
            
            if response.status_code == 200:
                # Parse the response (modify this based on Tabaarak's response format)
                status_data = response.json()
                status = status_data.get('status', 'unknown')
                details = status_data.get('details', '')
                
                # Map status to standard format
                status_mapping = {
                    'DELIVERED': 'delivered',
                    'FAILED': 'failed',
                    'PENDING': 'sent',
                    'SENT': 'sent',
                    'UNKNOWN': 'unknown'
                }
                
                return status_mapping.get(status, 'unknown'), details
            else:
                return 'unknown', f"Failed to check status. Status code: {response.status_code}"
                
        except Exception as e:
            return 'unknown', str(e)

def send_match_notification(guardian_phone, person_name=None, location_data=None, person_data=None):
    """
    Send SMS notification with simplified Somali location
    """
    sms_service = TabaarakSMS()
    
    # Format message with details
    message = f"Mudane/Marwo {person_data.get('guardian_name', 'qoyskooda')}, "
    message += f"waxaan gacanta ku haynaa {person_name}. "
    
    # Add location information in simple Somali format
    if location_data:
        # Start with basic location description
        message += "\nGoobta uu ku sugan yahay: "
        
        # Add address in simple format if available
        if location_data.get('addressDetails'):
            details = location_data['addressDetails']
            parts = []
            
            # Add road/building if available
            if details.get('road') or details.get('building'):
                parts.append(details.get('road') or details.get('building'))
            
            # Add neighborhood/area
            if details.get('suburb') or details.get('neighbourhood'):
                parts.append(details.get('suburb') or details.get('neighbourhood'))
            
            # Add district/city
            if details.get('city') or details.get('district'):
                parts.append(details.get('city') or details.get('district'))
            
            if parts:
                message += ", ".join(parts)
            else:
                # Fallback to simple address
                message += location_data.get('address', 'Goob aan la aqoon')
        
        # Add simple maps link for directions
        if location_data.get('latitude') and location_data.get('longitude'):
            message += f"\n\nSi aad u hesho tilmaamaha goobta: https://www.google.com/maps?q={location_data['latitude']},{location_data['longitude']}"
    
    # Format the phone number
    formatted_number = guardian_phone.replace('+', '').replace('252', '')
    if formatted_number.startswith('0'):
        formatted_number = formatted_number[1:]
    
    if not formatted_number.startswith('61'):
        formatted_number = '61' + formatted_number[-7:]
    elif len(formatted_number) > 9:
        formatted_number = formatted_number[:9]
    
    print(f"Sending SMS to formatted number: {formatted_number}")
    
    return sms_service.send_sms(formatted_number, message) 