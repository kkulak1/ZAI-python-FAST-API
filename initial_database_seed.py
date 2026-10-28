from config import settings
from database.database import SessionLocal, engine
from database.models import User, hash_password, Base

def create_initial_admin():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if (existing_admin):
            print("Admin user already exists.")
            return

        new_admin = User(
            username="admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        )

        db.add(new_admin)
        db.commit()
        print("Initial admin user created successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error creating initial admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()
