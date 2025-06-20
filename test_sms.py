from utils.sms_service import TabaarakSMS, send_match_notification
from datetime import datetime

def test_direct_sms():
    """Test direct SMS sending"""
    print("\n1. Testing direct SMS sending...")
    sms = TabaarakSMS()
    
    # Test phone number (update this with your test number)
    test_number = "617255950"  # Format: 61XXXXXX
    
    # Test message
    test_message = "This message is from Missing Person Finder System.  "
    
    print(f"Sending SMS to: {test_number}")
    print(f"Message: {test_message}")
    
    success, message = sms.send_sms(test_number, test_message)
    print(f"Result: {'Success' if success else 'Failed'}")
    print(f"Response: {message}")

def test_notification():
    """Test missing person notification"""
    print("\n2. Testing missing person notification...")
    
    # Test data
    test_phone = "619837755"  # Format: 61XXXXXX
    test_person = "Test Person"
    test_location = {
        "latitude": 2.0469,
        "longitude": 45.3182,
        "address": "Mogadishu",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Sending notification to: {test_phone}")
    print(f"Person name: {test_person}")
    print(f"Location: {test_location}")
    
    success, message = send_match_notification(test_phone, test_person, test_location)
    print(f"Result: {'Success' if success else 'Failed'}")
    print(f"Response: {message}")

if __name__ == "__main__":
    print("=== SMS Testing Script ===")
    
    while True:
        print("\nChoose a test to run:")
        print("1. Test direct SMS")
        print("2. Test missing person notification")
        print("3. Run both tests")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            test_direct_sms()
        elif choice == "2":
            test_notification()
        elif choice == "3":
            test_direct_sms()
            test_notification()
        elif choice == "4":
            print("\nExiting test script...")
            break
        else:
            print("\nInvalid choice. Please try again.") 