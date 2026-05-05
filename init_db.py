from app import app, db
from models.database import User
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Creating default admin user...")
            admin = User(
                username='admin',
                email='admin@tkrag.com',
                password_hash=generate_password_hash('admin123'),
                full_name='Administrator',
                is_admin=True,
                is_active=True
            )
            db.session.add(admin)
            
        # Check if test user exists
        testuser = User.query.filter_by(username='testuser').first()
        if not testuser:
            print("Creating default test user...")
            testuser = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('test123'),
                full_name='Test User',
                is_admin=False,
                is_active=True
            )
            db.session.add(testuser)
            
        db.session.commit()
        print("Database initialization complete!")

if __name__ == '__main__':
    init_database()
