"""
Seed script to populate the database with initial data
Run this after migrations: python -m app.seed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Role, User, Form, PermissionGroup
from app.utils.auth import hash_password
from app.config import settings


def seed_database():
    """Seed the database with initial data"""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding database...")
        
        # Create roles
        print("Creating roles...")
        roles_data = [
            {"name": settings.ROLE_GRANTEE},
            {"name": settings.ROLE_GRANTOR},
            {"name": settings.ROLE_ADMIN},
            {"name": settings.ROLE_SUPERUSER}
        ]
        
        roles = {}
        for role_data in roles_data:
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(**role_data)
                db.add(role)
                db.flush()
                roles[role_data["name"]] = role
                print(f"  ✓ Created role: {role_data['name']}")
            else:
                roles[role_data["name"]] = existing
                print(f"  - Role already exists: {role_data['name']}")
        
        db.commit()
        
        # Create users
        print("\nCreating users...")
        users_data = [
            {"cwid": "10000001", "username": "grantee1", "password": "password", "role": settings.ROLE_GRANTEE},
            {"cwid": "20000001", "username": "grantor1", "password": "password", "role": settings.ROLE_GRANTOR},
            {"cwid": "20000002", "username": "grantor2", "password": "password", "role": settings.ROLE_GRANTOR},
            {"cwid": "30000001", "username": "admin1", "password": "password", "role": settings.ROLE_ADMIN},
            {"cwid": "40000001", "username": "superuser1", "password": "password", "role": settings.ROLE_SUPERUSER},
        ]
        
        for user_data in users_data:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                role = db.query(Role).filter(Role.name == user_data["role"]).first()
                user = User(
                    cwid=user_data["cwid"],
                    username=user_data["username"],
                    password_hash=hash_password(user_data["password"]),
                    role_id=role.id
                )
                db.add(user)
                print(f"  ✓ Created user: {user_data['username']} ({user_data['role']})")
            else:
                print(f"  - User already exists: {user_data['username']}")
        
        db.commit()
        
        # Create forms
        print("\nCreating forms...")
        forms_data = [
            {"code": "SFAREGS", "description": "Student Finance - Accounts Receivable - General Student"},
            {"code": "SFAAPLC", "description": "Student Finance - Accounts Receivable - Application Center"},
            {"code": "STVTERM", "description": "Student - Term Codes"},
            {"code": "FAISMGR", "description": "Financial Aid - ISIR Manager"},
            {"code": "FTVFUND", "description": "Finance - Fund Codes"},
            {"code": "PAYROLL", "description": "Payroll Processing"},
            {"code": "HRROSTER", "description": "HR - Employee Roster"},
        ]
        
        for form_data in forms_data:
            existing = db.query(Form).filter(Form.code == form_data["code"]).first()
            if not existing:
                form = Form(**form_data, active=True)
                db.add(form)
                print(f"  ✓ Created form: {form_data['code']}")
            else:
                print(f"  - Form already exists: {form_data['code']}")
        
        db.commit()
        
        # Create permission groups
        print("\nCreating permission groups...")
        groups_data = [
            {"name": "Student Records - Read Only", "description": "View student academic records"},
            {"name": "Student Records - Full Access", "description": "View and edit student academic records"},
            {"name": "Financial Aid - Query", "description": "Query financial aid information"},
            {"name": "Financial Aid - Update", "description": "Update financial aid records"},
            {"name": "Finance - Budget", "description": "Access budget and finance information"},
            {"name": "HR - Employee Data", "description": "Access employee information"},
        ]
        
        for group_data in groups_data:
            existing = db.query(PermissionGroup).filter(PermissionGroup.name == group_data["name"]).first()
            if not existing:
                group = PermissionGroup(**group_data, active=True)
                db.add(group)
                print(f"  ✓ Created permission group: {group_data['name']}")
            else:
                print(f"  - Permission group already exists: {group_data['name']}")
        
        db.commit()
        
        print("\n✅ Database seeded successfully!")
        print("\nDefault Login Credentials:")
        print("=" * 50)
        for user_data in users_data:
            print(f"  {user_data['role']:15} | {user_data['username']:12} | password")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
