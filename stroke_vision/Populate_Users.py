import random
import string
from datetime import datetime, timedelta
from faker import Faker
from app import create_app, db
from app.models.user import User
from sqlalchemy.exc import IntegrityError

# Initialize Faker
fake = Faker()

def generate_strong_password(length=12):
    """
    Generates a strong password meeting the requirements:
    - At least 8 characters (default 12 for safety)
    - Uppercase, Lowercase, Number, Special Character
    """
    if length < 8:
        length = 8

    # Ensure at least one of each required type
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(string.punctuation)
    ]

    # Fill the rest with random choices from all sets
    all_chars = string.ascii_letters + string.digits + string.punctuation
    for _ in range(length - 4):
        password.append(random.choice(all_chars))

    random.shuffle(password)
    return "".join(password)

def populate_users():
    app = create_app()
    with app.app_context():
        print("--- Initializing Database ---")
        db.create_all()
        print("--- Starting User Population (last 6 months distribution) ---")
        
        # Determine number of users to generate (5 to 7)
        num_users = random.randint(5, 7)
        users_created = []

        # Ensure at least one Admin exists
        if not User.query.filter_by(email_hash=User.hash_email("admin@strokevision.com")).first():
            admin = User(
                name="System Admin",
                email="admin@strokevision.com",
                email_hash=User.hash_email("admin@strokevision.com"),
                role="Admin"
            )
            admin.set_password("Admin123!")
            db.session.add(admin)
            db.session.commit()
            users_created.append({
                "Name": admin.name,
                "Email": admin.email,
                "Role": admin.role,
                "Password": "Admin123!",
                "Date": datetime.utcnow().strftime("%Y-%m-%d")
            })

        ROLES = ["Doctor", "Nurse"]

        for _ in range(num_users):
            success = False
            attempts = 0
            # Retry loop in case of email collision (unlikely with Faker but possible)
            while not success and attempts < 5:
                try:
                    profile = fake.profile()
                    name = profile['name']
                    # Ensure unique email base
                    email = f"{name.replace(' ', '.').lower()}.{random.randint(100, 999)}@example.com"
                    
                    role = random.choice(ROLES)
                    password = generate_strong_password()
                    
                    # Backdate creation time (0 to 180 days ago) for graph distribution
                    days_ago = random.randint(0, 180)
                    created_at = datetime.utcnow() - timedelta(days=days_ago)

                    # Check if email exists
                    if User.query.filter_by(email=email).first():
                        attempts += 1
                        continue

                    user = User(
                        name=name,
                        email=email,
                        email_hash=User.hash_email(email),
                        role=role,
                        created_at=created_at
                    )
                    user.set_password(password)
                    
                    db.session.add(user)
                    db.session.commit()
                    
                    users_created.append({
                        "Name": name,
                        "Email": email,
                        "Role": role,
                        "Password": password,
                        "Date": created_at.strftime("%Y-%m-%d")
                    })
                    success = True
                    print(f"[+] Created user: {email} ({role}) - {created_at.strftime('%Y-%m-%d')}")

                except IntegrityError:
                    db.session.rollback()
                    attempts += 1
                except Exception as e:
                    db.session.rollback()
                    print(f"[-] Error creating user: {e}")
                    break

        print("\n" + "="*95)
        print(f"{'NAME':<25} | {'EMAIL':<35} | {'ROLE':<8} | {'DATE':<12} | {'PASSWORD'}")
        print("="*95)
        for u in users_created:
            print(f"{u['Name']:<25} | {u['Email']:<35} | {u['Role']:<8} | {u['Date']:<12} | {u['Password']}")
        print("="*95)
        print(f"\nSuccessfully created {len(users_created)} users.")

if __name__ == "__main__":
    populate_users()
