# run.py
from app import create_app, db
import os

app = create_app()

# Automatically create SQLite database tables if they do not exist
with app.app_context():
    db_path = app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
    if db_path and not os.path.exists(db_path):
        db.create_all()
        print(f"Database created at {db_path} with all tables.")
    else:
        print("Database already exists. Skipping creation.")

if __name__ == "__main__":
    app.run(debug=True)
