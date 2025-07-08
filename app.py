from flask import Flask, render_template, request
import csv
import os
import spacy
import string

app = Flask(__name__)

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Load disease data
DISEASE_DATA = []
with open('datasets/dataset_with_medicines_final.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        DISEASE_DATA.append(row)

# Load descriptions
DESCRIPTION_MAP = {}
with open('datasets/symptom_Description.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        DESCRIPTION_MAP[row['Disease'].strip()] = row['Description']

# Load precautions
PRECAUTION_MAP = {}
with open('datasets/symptom_precaution.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        PRECAUTION_MAP[row['Disease'].strip()] = [row['Precaution_1'], row['Precaution_2'], row['Precaution_3'], row['Precaution_4']]

# Get all unique symptoms
ALL_SYMPTOMS = set()
for row in DISEASE_DATA:
    for i in range(1, 18):
        symptom = row.get(f'Symptom_{i}', '').strip()
        if symptom:
            ALL_SYMPTOMS.add(symptom)
ALL_SYMPTOMS = sorted(list(ALL_SYMPTOMS))

# Preprocess symptoms for NLP matching
SYMPTOM_LEMMAS = {" ".join([token.lemma_ for token in nlp(s.replace('_', ' '))]): s for s in ALL_SYMPTOMS}

def extract_symptoms_from_text(text):
    # Lowercase, remove punctuation
    text = text.lower().translate(str.maketrans('', '', string.punctuation))
    doc = nlp(text)
    lemmas = [token.lemma_ for token in doc]
    found = set()
    # Match single-word symptoms
    for lemma in lemmas:
        for key, original in SYMPTOM_LEMMAS.items():
            if lemma in key.split():
                found.add(original)
    # Match multi-word symptoms
    for key, original in SYMPTOM_LEMMAS.items():
        if key in text:
            found.add(original)
    return found

@app.route('/', methods=['GET', 'POST'])
def index():
    report = None
    extracted = set()
    if request.method == 'POST':
        user_text = request.form.get('symptoms_text', '')
        extracted = extract_symptoms_from_text(user_text)
        # Find all diseases with at least 2 matching symptoms
        matches = []
        for row in DISEASE_DATA:
            disease_symptoms = set([row.get(f'Symptom_{i}', '').strip() for i in range(1, 18) if row.get(f'Symptom_{i}', '').strip()])
            score = len(extracted & disease_symptoms)
            if score >= 2:
                matches.append((score, len(disease_symptoms), row))
        # Sort by: highest score, then fewest total symptoms, then order in dataset
        matches.sort(key=lambda x: (-x[0], x[1]))
        if matches:
            best_score, _, best_match = matches[0]
            disease = best_match['Disease'].strip()
            description = DESCRIPTION_MAP.get(disease, 'No description available.')
            medicines = best_match.get('Medicines', 'Consult doctor')
            precautions = PRECAUTION_MAP.get(disease, [])
            report = {
                'disease': disease,
                'description': description,
                'medicines': medicines,
                'precautions': [p for p in precautions if p],
                'matched_symptoms': best_score,
                'total_symptoms': len(extracted),
                'extracted': extracted
            }
        else:
            report = {'disease': 'No clear match', 'description': 'No disease matched at least 2 symptoms. Please provide more details or consult a doctor.', 'medicines': '', 'precautions': [], 'matched_symptoms': 0, 'total_symptoms': len(extracted), 'extracted': extracted}
    return render_template('index.html', symptoms=ALL_SYMPTOMS, report=report, paragraph_input=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
