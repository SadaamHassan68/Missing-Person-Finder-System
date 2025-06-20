from app import app, db, User
from werkzeug.security import generate_password_hash

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\nExisting Users:")
        print("-" * 50)
        for user in users:
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"Password Hash: {user.password}")
            print(f"Created: {user.created_at}")
            print("-" * 50)

def create_admin(username, email, password):
    with app.app_context():
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            print(f"User with email {email} already exists!")
            return False
        
        # Create new admin user
        admin = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {username} created successfully!")
        return True

if __name__ == "__main__":
    # Create admin user with your preferred credentials
    create_admin(
        username="superadmin",  # Change this to your preferred username
        email="superadmin@example.com",  # Change this to your preferred email
        password="superadmin123"  # Change this to your preferred password
    )
    
    # List all users to verify
    list_users() 