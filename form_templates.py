FORM_TEMPLATES = {
    "Biodata": {
        "Personal Information": [
            {"field": "Full Name", "regex": r"Full Name[:\s]*([A-Za-z\s]+)"},
            {"field": "Date of Birth", "regex": r"Date of Birth[:\s]*(\d{2}/\d{2}/\d{4})"},
            {"field": "Gender", "regex": r"Gender[:\s]*(\w+)"},
        ],
        "Contact Details": [
            {"field": "Address", "regex": r"Address[:\s]*(.+?)(?=City)"},
            {"field": "City", "regex": r"City[:\s]*([A-Za-z\s]+)"},
            {"field": "Phone Number", "regex": r"Phone Number[:\s]*([\d\s]+)"},
            {"field": "Email Address", "regex": r"Email Address[:\s]*([\w\.-]+@[\w\.-]+)"},
        ],
        "Family Information": [
            {"field": "Father's Name", "regex": r"Father's Name[:\s]*([A-Za-z\s]+)"},
            {"field": "Father's Occupation", "regex": r"Father's Occupation[:\s]*([\w\s&,-]+)"},
            {"field": "Mother's Name", "regex": r"Mother's Name[:\s]*([A-Za-z\s]+)"},
            {"field": "Mother's Occupation", "regex": r"Mother's Occupation[:\s]*([\w\s&,-]+)"},
        ],
        "Educational Background": [
            {"field": "Highest Qualification", "regex": r"Highest Qualification[:\s]*([\w\s&,-]+)"},
            {"field": "Institution Name", "regex": r"Institution Name[:\s]*([\w\s&,-]+)"},
            {"field": "Year of Passing", "regex": r"Year of Passing[:\s]*(\d{4})"},
            {"field": "Percentage", "regex": r"Percentage[:\s]*(\d+\.?\d*)"},
        ],
        "Professional Details": [
            {"field": "Current Occupation", "regex": r"Current Occupation[:\s]*([\w\s&,-]+)"},
            {"field": "Company Name", "regex": r"Company Name[:\s]*([\w\s&,-]+)"},
            {"field": "Work Experience (years)", "regex": r"Work Experience \(years\)[:\s]*([\w\s&,-]+)"},
            {"field": "Key Skills", "regex": r"Key Skills[:\s]*([\w\s&,-]+)"},
        ],
        "Miscellaneous": [
            {"field": "Hobby", "regex": r"Hobby[:\s]*([\w\s&,-]+)"},
            {"field": "Languages Known", "regex": r"Languages Known[:\s]*([\w\s&,-]+)"},
        ],
    },
    "Admission": {
        "Personal Details": [
            {"field": "Full Name", "regex": r"Full Name[:\s]*([A-Za-z\s]+)"},
            {"field": "Date of Birth", "regex": r"Date of Birth[:\s]*(\d{2}/\d{2}/\d{4})"},
            {"field": "Gender", "regex": r"Gender[:\s]*(\w+)"},
        ],
        "Educational Details": [
            {"field": "School", "regex": r"School[:\s]*([\w\s&,-]+)"},
            {"field": "Percentage", "regex": r"Percentage[:\s]*(\d+\.?\d*)"},
        ],
        "Contact Information": [
            {"field": "Address", "regex": r"Address[:\s]*(.+?)(?=City)"},
            {"field": "City", "regex": r"City[:\s]*([A-Za-z\s]+)"},
            {"field": "State", "regex": r"State[:\s]*([A-Za-z\s]+)"},
            {"field": "Postal Code", "regex": r"Postal Code[:\s]*(\d+)"},
            {"field": "Phone Number", "regex": r"Phone Number[:\s]*([\d\s]+)"},
            {"field": "Email Address", "regex": r"Email Address[:\s]*([\w\.-]+@[\w\.-]+)"},
        ],
        "Course Details": [
            {"field": "Course Applied For", "regex": r"Course Applied For[:\s]*([\w\s&,-]+)"},
            {"field": "Preferred Stream", "regex": r"Preferred Stream[:\s]*([\w\s&,-]+)"},
        ],
    },
    "Bank Account": {
        "Bank Details": [
            {"field": "Bank Name", "regex": r"Bank Name[:\s]*([\w\s&,-]+)"},
            {"field": "Branch", "regex": r"Branch[:\s]*([\w\s&,-]+)"},
            {"field": "Form Type", "regex": r"Form Type[:\s]*([\w\s&,-]+)"},
            {"field": "Date", "regex": r"Date[:\s]*(\d{2}/\d{2}/\d{4})"},
            {"field": "Type of Account", "regex": r"Type of Account[:\s]*([\w\s&,-]+)"},
        ],
        "Personal Details": [
            {"field": "Full Name", "regex": r"Full Name[:\s]*([A-Za-z\s]+)"},
            {"field": "Date of Birth", "regex": r"Date of Birth[:\s]*(\d{2}/\d{2}/\d{4})"},
            {"field": "Gender", "regex": r"Gender[:\s]*(\w+)"},
            {"field": "Nationality", "regex": r"Nationality[:\s]*([\w\s&,-]+)"},
            {"field": "Marital Status", "regex": r"Marital Status[:\s]*([\w\s&,-]+)"},
            {"field": "Occupation", "regex": r"Occupation[:\s]*([\w\s&,-]+)"},
            {"field": "Monthly Income (approx.)", "regex": r"Monthly Income \(approx.\)[:\s]*([\w\s&,-]+)"},
        ],
        "Contact Information": [
            {"field": "Address", "regex": r"Address[:\s]*(.+?)(?=City)"},
            {"field": "City", "regex": r"City[:\s]*([A-Za-z\s]+)"},
            {"field": "State", "regex": r"State[:\s]*([A-Za-z\s]+)"},
            {"field": "Postal Code", "regex": r"Postal Code[:\s]*(\d+)"},
            {"field": "Phone Number", "regex": r"Phone Number[:\s]*([\d\s]+)"},
            {"field": "Email Address", "regex": r"Email Address[:\s]*([\w\.-]+@[\w\.-]+)"},
        ],
    },
}
