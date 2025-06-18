# Missing Person Finder System

A web-based system that helps find missing persons using facial recognition and real-time location tracking. The system supports both English and Somali languages.

## Features

- 👤 Face scanning and recognition
- 📍 Real-time location tracking
- 🗺️ Interactive map integration
- 📱 SMS notifications to guardians
- 🌍 Bilingual support (English/Somali)
- 📸 Camera integration
- 📊 Case management dashboard

## Requirements

- Python 3.8 or higher
- Web camera or device with camera
- Internet connection
- Modern web browser (Chrome, Firefox, Safari, or Edge)
- GPS-enabled device for location tracking

### Python Dependencies

All required Python packages are listed in `requirements.txt`, including:
- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug
- SQLAlchemy, alembic
- face-recognition, opencv-python, numpy, Pillow
- geopy, requests
- python-dotenv, bcrypt, PyJWT
- Bootstrap-Flask
- python-dateutil, pytz, validators
- pytest, black, flake8

## Setup & Installation

1. **Download or copy the project files** to a folder on your computer.
2. **Open a terminal** and navigate to the project folder.
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On Linux/Mac:
     ```bash
     source venv/bin/activate
     ```
5. **Set up environment variables:**
   - Create a `.env` file in the root directory with:
     ```
     FLASK_APP=app.py
     FLASK_ENV=development
     SECRET_KEY=your_secret_key_here
     ```

## Running the Application

1. **Start the Flask server:**
   ```bash
   flask run
   ```
2. **Open your web browser and navigate to:**
   ```
   http://127.0.0.1:5000
   ```

## Using the System

### 1. Registration
- Click "Register" to create a new account
- Fill in required information
- Upload reference photos for missing person

### 2. Face Scanning
- Go to "Face Scan" page
- Allow camera access when prompted
- Allow location access when prompted
- Click "Start Scan" to begin face detection

### 3. Location Tracking
- System automatically tracks location when scanning
- Shows current address and map
- Updates in real-time as location changes

### 4. Notifications
- Automatic SMS notifications sent to guardians when match found
- Includes location details and map link
- Delivery status tracking available

## Troubleshooting

### Camera Issues
- Ensure camera permissions are enabled in browser
- Check if another application is using the camera
- Try refreshing the page

### Location Issues
- Enable GPS on your device
- Allow location access in browser
- Ensure you have internet connectivity
- Try outdoors for better GPS accuracy

### SMS Notifications
- Verify phone number format (starts with 252 for Somalia)
- Check internet connectivity
- Contact support if messages not received

## Security

- All data is encrypted
- Location data is only shared when match is found
- Phone numbers are verified before sending SMS
- User authentication required for sensitive operations

## Support

For technical support or questions:
- Email: support@example.com
- Phone: +252 XX XXX XXXX
- Working hours: 8 AM - 8 PM EAT

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.