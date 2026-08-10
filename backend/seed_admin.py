import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def seed_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("Creating default admin user...")
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123")
            )
            db.add(admin_user)
            db.commit()
            print("Admin user created successfully. Username: admin, Password: admin123")
        else:
            print("Admin user already exists.")
    except Exception as e:
        print(f"Error seeding admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
