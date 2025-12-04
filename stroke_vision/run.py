# run.py
import os

# Suppress TensorFlow logging before importing anything else
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from app import create_app, db
from dotenv import load_dotenv

load_dotenv()

app = create_app()

# Automatically create SQLite database tables if they do not exist
is_reloader = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

with app.app_context():
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_filename = db_uri.replace("sqlite:///", "")
    db_path = os.path.join(app.instance_path, db_filename)
    
    if not os.path.exists(db_path):
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()
        if not is_reloader:
            print(f"Database created at {db_filename} with all tables.")
    else:
        if not is_reloader:
            print(f"Database already exists at {db_filename}. Skipping creation.")

if __name__ == "__main__":
    app.run(debug=True)
