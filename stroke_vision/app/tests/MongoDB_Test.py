# Assuming 'db' is your mongoengine connection object or app context is active
from app.models.patient import Patient

# This prints the collection name MongoEngine is using
print(
    f"MongoEngine is looking for data in collection: {Patient._get_collection_name()}"
)

# If your model is Patient, this should print: patient
