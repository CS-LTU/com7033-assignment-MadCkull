from datetime import datetime
import random
from app.models.patient import Patient
from app.utils.log_utils import (
    log_activity,
)  # patient-related events (visible to doctors/admin)


class IDGenerator:
    @staticmethod
    def generate_patient_id():
        max_attempts = 5

        for attempt in range(max_attempts):
            now = datetime.now()
            year_digit = str(now.year)[-1]
            month_digits = str(now.month).zfill(2)
            day_digits = str(now.day).zfill(2)

            date_portion = f"{year_digit}{month_digits}{day_digits}"
            random_sequence = str(random.randint(0, 9999)).zfill(4)
            patient_id = f"{date_portion}{random_sequence}"

            # Log attempt
            if attempt == 0:
                log_activity(
                    f"Generating new patient ID attempt 1: {patient_id}", level=1
                )
            else:
                log_activity(
                    f"Retry attempt {attempt + 1} generating patient ID: {patient_id}",
                    level=2,
                )

            if IDGenerator.validate_patient_id(patient_id):
                log_activity(
                    f"Successfully generated valid patient ID: {patient_id}", level=1
                )
                return str(patient_id)
            else:
                print(
                    f"Attempt {attempt + 1}: Generated invalid ID {patient_id}. Retrying..."
                )
                log_activity(
                    f"Generated invalid patient ID (will retry): {patient_id}", level=2
                )

        log_activity(
            f"Failed to generate a valid patient ID after {max_attempts} attempts.",
            level=3,
        )
        raise ValueError(
            "Failed to generate a valid patient ID after maximum attempts."
        )

    @staticmethod
    def check_patient_id(patient_id):
        """
        Returns True if the patient_id is NOT present in DB (i.e., available).
        """
        patient = Patient.objects(patient_id=patient_id).first()

        if not patient:
            return True
        else:
            # Log collision
            log_activity(
                f"Patient ID collision detected: {patient_id} is already in use.",
                level=2,
            )
            return False

    @staticmethod
    def validate_patient_id(patient_id):
        if not patient_id or not isinstance(patient_id, str):
            log_activity(
                f"Invalid patient_id format (not a string or empty): {patient_id}",
                level=2,
            )
            return False

        if len(patient_id) != 9 or not patient_id.isdigit():
            log_activity(
                f"Invalid patient_id format (length/digits): {patient_id}", level=2
            )
            return False

        try:
            year_digit = patient_id[0]
            month = int(patient_id[1:3])
            day = int(patient_id[3:5])

            if month < 1 or month > 12:
                log_activity(
                    f"Invalid month in patient_id '{patient_id}': {month}", level=2
                )
                return False

            if day < 1 or day > 31:
                log_activity(
                    f"Invalid day in patient_id '{patient_id}': {day}", level=2
                )
                return False

            if IDGenerator.check_patient_id(str(patient_id)):
                return True
            else:
                return False
        except ValueError as e:
            log_activity(
                f"Exception parsing date portion of patient_id '{patient_id}': {e}",
                level=3,
            )
            return False

        return False
