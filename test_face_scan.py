import cv2
import numpy as np
import os

def test_face_detection():
    # Create test image with a face
    test_image = np.zeros((300, 300, 3), dtype=np.uint8)
    test_image.fill(255)  # White background
    
    # Draw a simple face
    # Head
    cv2.circle(test_image, (150, 150), 80, (0, 0, 0), 2)
    
    # Eyes
    cv2.circle(test_image, (120, 130), 10, (0, 0, 0), 2)
    cv2.circle(test_image, (180, 130), 10, (0, 0, 0), 2)
    
    # Mouth
    cv2.ellipse(test_image, (150, 180), (40, 20), 0, 0, 180, (0, 0, 0), 2)
    
    # Save test image
    os.makedirs('data/uploads', exist_ok=True)
    cv2.imwrite('data/uploads/test_face.jpg', test_image)
    
    # Load face cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Detect faces
    gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    print(f"Number of faces detected: {len(faces)}")
    for (x, y, w, h) in faces:
        print(f"Face detected at: x={x}, y={y}, width={w}, height={h}")
        cv2.rectangle(test_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    # Save result
    cv2.imwrite('data/uploads/test_face_result.jpg', test_image)
    print("\nTest completed. Check data/uploads/test_face_result.jpg for results.")

if __name__ == "__main__":
    test_face_detection() 