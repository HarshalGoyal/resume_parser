import pdfplumber
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def detect_sections(text):
    doc = nlp(text)
    sections = {
        "work_experience": [],
        "education": [],
        "skills": [],
        "summary": [],
        "contact": []
    }
    for sent in doc.sents:
        lowered = sent.text.lower()
        if "work" in lowered or "experience" in lowered:
            sections["work_experience"].append(sent.text)
        elif "education" in lowered or "degree" in lowered:
            sections["education"].append(sent.text)
        elif "skill" in lowered or "skills" in lowered:
            sections["skills"].append(sent.text)
        elif "summary" in lowered or "objective" in lowered:
            sections["summary"].append(sent.text)
        elif "email" in lowered or "phone" in lowered:
            sections["contact"].append(sent.text)
    return sections

def extract_information(text, model):
    doc = nlp(text)
    extracted_info = {
        "work_experience": [],
        "education": [],
        "skills": [],
        "summary": [],
        "contact": []
    }

    def extract_work_experience(sent):
        title = None
        company = None
        duration = None
        location = None
        description_parts = []

        for ent in sent.ents:
            if ent.label_ == "ORG":
                company = ent.text
            elif ent.label_ == "DATE":
                duration = ent.text
            elif ent.label_ == "GPE":
                location = ent.text

        job_titles = ["engineer", "developer", "manager", "analyst", "scientist"]
        for token in sent:
            if token.text.lower() in job_titles:
                title = token.text

        description_parts.append(sent.text)

        return {
            "title": title or "Unknown",
            "company": company or "Unknown",
            "duration": duration or "Unknown",
            "location": location or "Unknown",
            "description": " ".join(description_parts),
        }

    for sent in doc.sents:
        prediction = model.predict([sent.text])[0]

        if prediction == "work_experience":
            enriched = extract_work_experience(sent)
            extracted_info[prediction].append(enriched)
        elif prediction == "education":
            extracted_info[prediction].append({"description": sent.text})
        elif prediction == "skills":
            extracted_info[prediction].append({"name": sent.text})
        elif prediction == "summary" or prediction == "contact":
            extracted_info[prediction].append(sent.text)

    return extracted_info


def train_ml_model():
    training_data = [
        ("Company: Google", "work_experience"),
        ("Title: Software Engineer", "work_experience"),
        ("Education: Stanford University", "education"),
        ("Skill: Python", "skills"),
        ("Summary: A passionate software developer", "summary"),
        ("Contact: john.doe@example.com", "contact")
    ]
    X = [item[0] for item in training_data]
    y = [item[1] for item in training_data]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('clf', LinearSVC())
    ])
    model.fit(X_train, y_train)
    return model