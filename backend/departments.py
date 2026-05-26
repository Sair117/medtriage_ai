DEPARTMENTS = {
    "Emergency Medicine": {
        "description": "Life-threatening conditions requiring immediate intervention",
        "examples": ["chest pain", "stroke symptoms", "severe bleeding", "difficulty breathing", "loss of consciousness"],
    },
    "Cardiology": {
        "description": "Heart and cardiovascular system",
        "examples": ["palpitations", "irregular heartbeat", "chest tightness", "high blood pressure", "swollen ankles"],
    },
    "Orthopedics": {
        "description": "Bones, joints, muscles, and ligaments",
        "examples": ["fracture", "joint pain", "back pain", "sports injury", "swollen knee"],
    },
    "Dermatology": {
        "description": "Skin, hair, and nails",
        "examples": ["rash", "acne", "mole changes", "itching", "skin infection"],
    },
    "Gastroenterology": {
        "description": "Digestive system — stomach, intestines, liver",
        "examples": ["abdominal pain", "nausea", "vomiting", "diarrhea", "acid reflux", "blood in stool"],
    },
    "Neurology": {
        "description": "Brain, spinal cord, and nerves",
        "examples": ["headache", "dizziness", "numbness", "seizures", "memory problems", "tremors"],
    },
    "Respiratory / Pulmonology": {
        "description": "Lungs and breathing",
        "examples": ["cough", "shortness of breath", "wheezing", "asthma", "chest congestion"],
    },
    "ENT (Ear, Nose & Throat)": {
        "description": "Ears, nose, throat, and sinuses",
        "examples": ["ear pain", "sore throat", "sinus congestion", "hearing loss", "nosebleed"],
    },
    "Mental Health": {
        "description": "Psychological and psychiatric conditions",
        "examples": ["anxiety", "depression", "insomnia", "panic attacks", "stress"],
    },
    "General Practice": {
        "description": "General health concerns, check-ups, and anything not fitting other departments",
        "examples": ["fever", "fatigue", "weight changes", "general check-up", "flu symptoms"],
    },
}


def get_departments_prompt_context() -> str:
    lines = []
    for name, info in DEPARTMENTS.items():
        examples = ", ".join(info["examples"])
        lines.append(f"- **{name}**: {info['description']}. Common presentations: {examples}")
    return "\n".join(lines)
