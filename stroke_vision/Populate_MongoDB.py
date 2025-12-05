# realistic_population_generator_fixed.py
from mongoengine import connect
from datetime import datetime, timedelta
import random
import math
from faker import Faker
from app.models.patient import Patient
from app.utils.prediction import StrokePredictor

fake = Faker(["en_us"])
fake.seed_instance(42)
predictor = StrokePredictor()

CREATORS = [
    "MadCkull",
    "Awais Anwar",
    "Nida Yasir",
    "Dr. Irfan",
    "Dr. Hassan",
    "Dr. Muqaddas",
    "Dr. Laraib",
    "Dr. Kinza",
    "Dr. Atiqa",
    "Dr. Nadeem",
    "Sayan Dev",
]

# Allowed enum for work_type in Patient model
ALLOWED_WORK_TYPES = [
    "Children",
    "Govt Job",
    "Never Worked",
    "Private",
    "Self-Employed",
]


def truncate(value, low, high):
    return max(low, min(high, value))


def sample_trunc_normal(mu, sigma, low, high):
    for _ in range(100):
        v = random.gauss(mu, sigma)
        if low <= v <= high:
            return v
    return truncate(v, low, high)


AGE_BUCKETS = [
    (10, 17, 0.20),
    (18, 24, 0.20),
    (25, 39, 0.30),
    (40, 59, 0.18),
    (60, 74, 0.10),
    (75, 100, 0.02),
]


def sample_age():
    buckets = [(a, b) for (a, b, _) in AGE_BUCKETS]
    weights = [w for (_, _, w) in AGE_BUCKETS]
    chosen = random.choices(buckets, weights=weights, k=1)[0]
    return random.randint(chosen[0], chosen[1])


def sample_bmi(age, gender):
    if age < 18:
        mu, sd, low, high = 19.0, 2.0, 12.0, 30.0
    elif age < 25:
        mu, sd = (24.0, 3.0) if gender == "Female" else (23.0, 3.0)
        low, high = 15.0, 40.0
    elif age < 40:
        mu, sd = (26.0, 4.0) if gender == "Female" else (24.5, 3.5)
        low, high = 15.0, 45.0
    elif age < 60:
        mu, sd = (28.0, 4.5) if gender == "Female" else (26.0, 4.0)
        low, high = 15.0, 50.0
    else:
        mu, sd = (27.0, 4.5) if gender == "Female" else (25.5, 4.0)
        low, high = 14.0, 48.0

    bmi = sample_trunc_normal(mu, sd, low, high)
    if random.random() < 0.005:
        bmi = truncate(bmi + random.uniform(8, 18), low, high)
    return round(bmi, 1)


DIABETES_PREVALENCE_BY_AGE = [
    (10, 17, 0.005),
    (18, 24, 0.02),
    (25, 39, 0.07),
    (40, 49, 0.15),
    (50, 59, 0.26),
    (60, 100, 0.30),
]


def age_group_prevalence(age, table):
    for a, b, p in table:
        if a <= age <= b:
            return p
    return table[-1][2]


def sample_glucose(age, bmi, hypertensive=False):
    p_diab = age_group_prevalence(age, DIABETES_PREVALENCE_BY_AGE)
    if bmi >= 30:
        p_diab = min(0.9, p_diab + 0.12)
    is_diabetic = random.random() < p_diab

    if is_diabetic:
        g = sample_trunc_normal(150, 40, 110, 350)
    else:
        base_mu = 90 + max(0, (age - 30) * 0.25)
        base_mu += max(0, (bmi - 24) * 0.6)
        g = sample_trunc_normal(base_mu, 10, 60, 140)

    return round(g, 1), is_diabetic


HYPERTENSION_BY_AGE = [
    (10, 17, 0.01),
    (18, 39, 0.08),
    (40, 59, 0.30),
    (60, 100, 0.45),
]


def sample_hypertension(age, diabetic=False):
    p = age_group_prevalence(age, HYPERTENSION_BY_AGE)
    if diabetic:
        p = min(0.95, p + 0.18)
    p = truncate(random.gauss(p, p * 0.12), 0.0, 0.99)
    return random.random() < p


def sample_heart_disease(age, hypertensive):
    base = 0.0
    if age < 40:
        base = 0.01
    elif age < 60:
        base = 0.05
    elif age < 75:
        base = 0.12
    else:
        base = 0.20
    if hypertensive:
        base = min(0.95, base + 0.12)
    return random.random() < truncate(random.gauss(base, base * 0.3), 0, 0.99)


MALE_SMOKING_PREV = 0.22
FEMALE_SMOKING_PREV = 0.03


def sample_smoking_status(age, gender):
    if age < 15:
        return "Never Smoked"
    p = MALE_SMOKING_PREV if gender == "Male" else FEMALE_SMOKING_PREV
    if random.random() < p:
        return "Formerly Smoked" if random.random() < 0.12 else "Smokes"
    else:
        return "Unknown" if random.random() < 0.02 else "Never Smoked"


# ---- fixed: only return allowed work_type values ----
def sample_work_type(age):
    # Map ages into allowed categories only
    if age < 15:
        return "Children"
    if age < 22:
        # Younger adults: many haven't been in formal jobs yet
        return random.choice(["Never Worked", "Private"])
    if age >= 65:
        # elderly — no 'Retired' in schema, so prefer 'Private' or 'Self-Employed' or 'Govt Job'
        return random.choices(
            ["Private", "Self-Employed", "Govt Job"], weights=[0.6, 0.25, 0.15], k=1
        )[0]
    # otherwise working-age adults
    return random.choice(["Govt Job", "Private", "Self-Employed", "Never Worked"])


def sample_ever_married(age):
    if age < 18:
        return "No"
    if age < 25:
        base = 0.25
    elif age < 35:
        base = 0.75
    elif age < 50:
        base = 0.9
    else:
        base = 0.95
    return "Yes" if random.random() < base else "No"


def customize_name():
    name = fake.name().split()
    return f"{name[0]} {name[-1]}"


def generate_patient_data():
    age = sample_age()
    gender = random.choice(["Male", "Female"])
    bmi = sample_bmi(age, gender)
    avg_glucose_level, is_diabetic = sample_glucose(age, bmi)
    hypertensive = sample_hypertension(age, is_diabetic)
    heart_disease = sample_heart_disease(age, hypertensive)
    smoking_status = sample_smoking_status(age, gender)
    work_type = sample_work_type(age)
    # Safety clamp: ensure work_type is valid for Patient model
    if work_type not in ALLOWED_WORK_TYPES:
        work_type = "Private"
    ever_married = sample_ever_married(age)
    residence_type = random.choice(["Urban", "Rural"])

    data_for_predictor = {
        "gender": gender,
        "age": str(age),
        "hypertension": "1" if hypertensive else "0",
        "heart_disease": "1" if heart_disease else "0",
        "ever_married": ever_married,
        "residence_type": residence_type,
        "avg_glucose_level": str(avg_glucose_level),
        "bmi": str(bmi),
        "work_type": work_type,
        "smoking_status": smoking_status,
    }

    risk = predictor.predict_risk(data_for_predictor)

    return Patient(
        patient_id=str(random.randint(400000000, 499999999)),
        name=customize_name(),
        age=age,
        gender=gender,
        ever_married=ever_married,
        work_type=work_type,
        residence_type=residence_type,
        heart_disease="Yes" if heart_disease else "No",
        hypertension="Yes" if hypertensive else "No",
        avg_glucose_level=avg_glucose_level,
        bmi=bmi,
        smoking_status=smoking_status,
        stroke_risk=risk,
        record_entry_date=datetime.now() - timedelta(days=random.randint(0, 5 * 365)),
        created_by=random.choice(CREATORS),
    )


def generate_database(num_records=5000):
    connect("StrokeDB")
    saved = 0
    for _ in range(num_records):
        try:
            patient = generate_patient_data()
            patient.save()
            saved += 1
        except Exception as e:
            print(f"Error generating patient: {str(e)}")
    print(f"Successfully generated {saved} patient records (requested {num_records})")


if __name__ == "__main__":
    generate_database()
