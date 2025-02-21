import os
import json
from flask import Flask, render_template, request, send_file, session, abort
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from markdown import markdown  

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "supersecretkey12345")  # Secure secret key
app.config["SESSION_PERMANENT"] = False  # Ensure session expires on browser close

# Configure Google Gemini API
API_KEY = os.getenv("GOOGLE_API_KEY")  # Secure API Key handling
if not API_KEY:
    raise ValueError("Missing Google Gemini API Key! Set GOOGLE_API_KEY as an environment variable.")

genai.configure(api_key=API_KEY)

# Directory for saving resumes
SAVE_DIR = "saves"
os.makedirs(SAVE_DIR, exist_ok=True)


# ✅ Function to save text as a properly formatted PDF
def save_to_pdf(text, filename):
    """Converts a string (text) into a properly formatted ATS-friendly PDF file."""
    if not text.strip():
        text = "No content available."

    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("<b>Resume</b>", styles["Title"]), Spacer(1, 0.2 * inch)]

    for line in text.split("\n"):
        if "**" in line:  # Bold formatting for headers
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph(f"<b>{line.replace('**', '')}</b>", styles["Heading2"]))
        elif "-" in line:
            elements.append(Paragraph(f"• {line.replace('-', '')}", styles["Normal"]))
        else:
            elements.append(Paragraph(line, styles["Normal"]))

    doc.build(elements)


# ✅ Function to save resume data as JSON
def save_resume_data(name, resume_data):
    """Saves resume data as a JSON file."""
    filename = os.path.join(SAVE_DIR, f"{name.replace(' ', '_')}_resume.json")
    try:
        with open(filename, "w") as f:
            json.dump(resume_data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Error saving data: {e}")


# ✅ Function to load saved resume data
def load_resume_data(name):
    """Loads saved resume data from JSON."""
    filename = os.path.join(SAVE_DIR, f"{name.replace(' ', '_')}_resume.json")
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Error loading JSON: Corrupt or invalid file -> {filename}")
            return None
    return None


# ✅ Function to list saved resumes
def get_saved_resumes():
    """Retrieves a list of saved resumes."""
    return [file.replace("_resume.json", "").replace("_", " ") for file in os.listdir(SAVE_DIR) if file.endswith("_resume.json")]


# ✅ Function to generate ATS-optimized resume
def generate_resume(name, job_title, experience_summary, work_experience, education, certifications, skills):
    """Generates an ATS-ready resume using Google Gemini AI."""
    if not all([name, job_title, experience_summary, work_experience, education, skills]):
        return "Error: Missing required fields for resume generation."

    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
    Create a professional ATS-optimized resume for {name}, applying for {job_title}.
    - **Professional Summary** (Concise, keyword-rich)
    - **Education** (Degrees, Institutions)
    - **Work Experience** (2-4 positions with bullet points)
    - **Certifications** (If applicable)
    - **Skills** (Optimized for ATS parsing)

    Experience Summary: {experience_summary}
    Work Experience: {work_experience}
    Education: {education}
    Certifications: {certifications or "None"}
    Skills: {skills}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error generating resume: {e}")
        return "⚠️ Unable to generate resume due to an error."


# ✅ Function to analyze ATS optimization score
def analyze_ats_score(resume_text):
    """Analyzes ATS compatibility, missing keywords, and suggests improvements."""
    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
    Analyze this resume for ATS (Applicant Tracking System) compatibility.
    - Provide an **ATS Score (0-100)**
    - Identify **missing critical keywords**
    - Suggest **improvements for better ATS ranking**

    Resume Text:
    {resume_text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error analyzing ATS score: {e}")
        return "⚠️ Unable to analyze ATS compatibility."
    
def generate_cover_letter(name, job_title, company, experience_summary, skills):
    """Generate a professional, ATS-optimized cover letter using Gemini AI."""
    if not all([name, job_title, company, experience_summary, skills]):
        return "⚠️ Error: Missing required fields for cover letter generation."

    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
    Write a compelling, ATS-friendly personalized cover letter for {name} applying to {company} as a {job_title}.
    
    Guidelines:
    - Start with a strong **introduction** addressing the hiring manager.
    - Highlight **why you're the perfect fit** (using experience & skills).
    - End with a **call to action** requesting an interview.
    - Keep the tone **professional, confident, and enthusiastic**.

    Experience Summary: {experience_summary}
    Skills: {skills}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()  # Ensure no extra whitespace
    except Exception as e:
        print(f"❌ Error generating cover letter: {e}")
        return f"⚠️ Error generating cover letter content: {str(e)}"


# ✅ Flask Route: Home Page
@app.route("/", methods=["GET", "POST"])
def index():
    resume_text = None
    cover_letter_text = None
    ats_feedback = None
    saved_resumes = get_saved_resumes()

    if request.method == "POST":
        if "generate_resume_btn" in request.form:
            name = request.form.get("name", "").strip()
            job_title = request.form.get("job_title", "").strip()
            company = request.form.get("company", "").strip()
            experience_summary = request.form.get("experience_summary", "").strip()
            work_experience = request.form.get("work_experience", "").strip()
            education = request.form.get("education", "").strip()
            certifications = request.form.get("certifications", "").strip()
            skills = request.form.get("skills", "").strip()

            resume_text = generate_resume(name, job_title, experience_summary, work_experience, education, certifications, skills)
            ats_feedback = analyze_ats_score(resume_text)
            cover_letter_text = generate_cover_letter(name, job_title, company, experience_summary, skills)

            # Convert ATS feedback markdown to HTML
            ats_feedback = markdown(ats_feedback)

            

            resume_data = {
                "name": name,
                "job_title": job_title,
                "company": company,
                "experience_summary": experience_summary,
                "work_experience": work_experience,
                "education": education,
                "certifications": certifications,
                "skills": skills,
                "resume_text": resume_text,
                "cover_letter_text": cover_letter_text,
                "ats_feedback": ats_feedback
            }
            save_resume_data(name, resume_data)

    return render_template("index.html",
                           resume_text=resume_text,
                           cover_letter_text=cover_letter_text,
                           ats_feedback=ats_feedback,
                           saved_resumes=saved_resumes)


# ✅ Flask Route: Download Resume
@app.route("/download_resume/<filename>")
def download_resume(filename):
    """Allows users to download saved resumes."""
    filepath = os.path.join(SAVE_DIR, filename)
    return send_file(filepath, as_attachment=True) if os.path.exists(filepath) else abort(404, "File not found.")


# ✅ Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
