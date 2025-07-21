import gradio as gr
import os
from google import genai
from google.genai import types
import pathlib
import json
import re
import requests
import urllib.parse
from fpdf import FPDF
import tempfile

# Track global state
context_summary = ""
context_primary_response = ""
context_modification = ""

# Function: Analyze Resume
def resume_pipeline(file, user_query):
    if not file:
        return "❌ Please upload a resume."

    with open(file.name, "rb") as f:
        resume_bytes = f.read()

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    resume_data = types.Part.from_bytes(data=resume_bytes, mime_type='application/pdf')

    prompt = f"""
You are an expert resume analyzer. Perform the following tasks from the given resume:
1. Extract the user's **email ID**.
2. Determine the **job role** preference from the query: "{user_query}". If not found in query, extract from the resume.
3. Identify the **experience level** of the candidate: choose from ["fresher", "intermediate", "senior"].
4. Extract **location preference** from query first, then from resume if missing. Default to "anywhere in India" if not found.
5. Summarize the resume in detail.
6. If the query is a salary search find the company name from query
7. If the query is salary search determine experiance in year: choose from [LESS_THAN_ONE, ONE_TO_THREE, FOUR_TO_SIX, SEVEN_TO_NINE, TEN_TO_FOURTEEN, ABOVE_FIFTEEN] based on the resume.
8. Summarize "{user_query}.
Respond in JSON:
{{
  "email": "...",
  "experience_level": "...",
  "job_role": "...",
  "location": "...",
  "summary": "..."
  "company": "..."
  "expy": "..."
  "uq": "..."
  
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[resume_data, prompt]
        )

        clean = re.sub(r"^```(?:json)?|```$", "", response.text.strip(), flags=re.MULTILINE)
        info = json.loads(clean)

        global context_summary
        context_summary = info["summary"]

        return info
    except Exception as e:
        return f"❌ Error: {e}"

# Function: Classify Query Type
def classify_query(query):
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    prompt = f"""
Classify the following user query into one of these three categories ONLY:
- "job_search"
- "salary_search"
- "career_advice"

Query: "{query}"

Respond with only one word: job_search, salary_search, or career_advice.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )
        category = response.text.strip().lower()
        if category in ["job_search", "salary_search", "career_advice"]:
            return category
        return "job_search"
    except Exception as e:
        print(f"❌ Error classifying query: {e}")
        return "job_search"

# Function: Search Jobs
def job_search(info):
    if not info or "job_role" not in info or "experience_level" not in info:
        return "❌ Invalid resume info."

    keywords = f"{info['experience_level']} {info['job_role']}"
    location = info.get("location", "India")
    api_key = os.environ.get("SERPAPI_KEY")

    if not api_key:
        return "❌ SERPAPI_KEY not found in environment."

    query = f"{keywords} jobs in {location}"
    params = {
        "engine": "google_jobs",
        "q": query,
        "hl": "en",
        "api_key": api_key
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"❌ Error fetching jobs: {e}"

    jobs = data.get("jobs_results", [])
    if not jobs:
        return "😕 No job results found."

    output = f"\nTop {min(len(jobs), 10)} jobs for: '{keywords}' in {location}\n\n"
    for i, job in enumerate(jobs[:10]):
        title = job.get("title", "No title")
        company = job.get("company_name", "No company")
        loc = job.get("location", "No location")
        posted = job.get("detected_extensions", {}).get("posted_at", "N/A")

        output += f"{i+1}. {title} at {company}\n"
        output += f"   Location: {loc}\n"
        output += f"   Posted: {posted}\n"

        highlights = job.get("job_highlights", [])
        for section in highlights:
            section_title = section.get("title", "")
            items = section.get("items", [])
            if items:
                output += f"   {section_title}:\n"
                for item in items:
                    output += f"      - {item}\n"

        search_query = urllib.parse.quote(f"{title} at {company} {loc}")
        search_link = f"https://www.google.com/search?q={search_query}"
        output += f"   Search Link: {search_link}\n"
        output += "-" * 60 + "\n"

    global context_primary_response
    context_primary_response = output
    return output

# Placeholder: Salary Search
def salary_search(info):
    if not info or not all(k in info for k in ["company", "job_role", "location", "expy"]):
        return "❌ Insufficient info for salary search."

    url = "https://job-salary-data.p.rapidapi.com/company-job-salary"
    headers = {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "job-salary-data.p.rapidapi.com"
    }

    if not headers["x-rapidapi-key"]:
        return "❌ RAPIDAPI_KEY not found in environment."

    querystring = {
        "company": info["company"],
        "job_title": info["job_role"],
        "location_type": "CITY",
        "location": info["location"],
        "years_of_experience": info["expy"]
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"❌ API request error: {e}"

    if data.get("status") != "OK":
        return f"❌ API Error: {data.get('error', {}).get('message', 'Unknown error')}"

    try:
        salary_info = data["data"][0]
    except (KeyError, IndexError):
        return "❌ No salary data found for the given criteria."

    output = f"""
📍 **Location:** {salary_info['location']}
🏢 **Company:** {salary_info['company']}
💼 **Job Title:** {salary_info['job_title']}
🪙 **Currency:** {salary_info['salary_currency']}
📊 **Salary Breakdown**
  ➤ Median Salary: ₹{salary_info['median_salary']:,} per year  
  ➤ Salary Range: ₹{salary_info['min_salary']:,} – ₹{salary_info['max_salary']:,}  
  ➤ Median Base Salary: ₹{salary_info['median_base_salary']:,}  
  ➤ Median Additional Pay: ₹{salary_info['median_additional_pay']:,}  
🔍 **Confidence Level:** {salary_info['confidence']}  
🧾 Based on {salary_info['salary_count']} reported salaries.
"""
    
    global context_primary_response
    context_primary_response = output
    return output.strip()


# Placeholder: Career Advice
# Updated: Career Advice
def career_advice(info):
    global context_summary, context_primary_response

    user_query = info.get("uq", "")
    if not user_query.strip():
        return "❌ No user query provided for career advice."

    if not context_summary.strip():
        return "❌ Resume summary is empty."

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    prompt = f"""
You are a career guidance expert.
The user has the following resume summary:
{context_summary}

Based on this background, respond to the following career query:
"{user_query}"

Provide a detailed, structured, and helpful answer suitable for a fresher or job seeker.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )
        clean_response = re.sub(r"^```(?:\w+)?|```$", "", response.text.strip(), flags=re.MULTILINE)
        context_primary_response = clean_response
        return clean_response
    except Exception as e:
        return f"❌ Error generating career advice: {e}"


# Function: Chat Assistant
def chat(query):
    global context_summary, context_primary_response, context_modification

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    prompt = f"""
You are an AI assistant helping a candidate with job search strategy.
Candidate's Resume Summary:
{context_summary}
Job Listings Retrieved or salary enquiry or carrer query result:
{context_primary_response}
Previous Context (if any):
{context_modification}
Now answer this new user query:
"{query}"
Respond with a helpful, structured answer.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )
        clean_response = re.sub(r"^```(?:\w+)?|```$", "", response.text.strip(), flags=re.MULTILINE)
        context_modification = clean_response
        return clean_response
    except Exception as e:
        return f"❌ Error: {e}"

# Function: Generate PDF
def create_pdf_file():
    global context_primary_response, context_modification

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    prompt = f"""
You are a helpful assistant. Based on the following two sections, create a clean, well-structured PDF content remove all types NON ASCII CHARACTER. Do NOT include emojis or decorative symbols. Use clear headings, bullet points where needed, and avoid unnecessary flair.
Primary output:
{context_primary_response}
Assistant's Advice and Context:
{context_modification}
Now, combine and structure this into a professional-looking PDF content.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )
        clean_text = re.sub(r"^```(?:\w+)?|```$", "", response.text.strip(), flags=re.MULTILINE)

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in clean_text.split("\n"):
            pdf.multi_cell(0, 10, line)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            pdf.output(f.name)
            return f.name

    except Exception as e:
        return f"❌ Error generating PDF: {e}"

# Unified Handler with Classification Logic
def unified_find_jobs(file, query):
    if not query.strip():
        return "❌ Please enter a job query (What's on your mind?).", {}

    info = resume_pipeline(file, query)
    if isinstance(info, str):  # Error occurred
        return info, {}

    category = classify_query(query)

    if category == "job_search":
        result = job_search(info)
    elif category == "salary_search":
        result = salary_search(info)
    elif category == "career_advice":
        result = career_advice(info)
    else:
        result = "❌ Unrecognized query type."

    return result, info

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## 🤖 CareerPilot- AI carrer Assist")

    gr.Markdown("""
#
Hey there, ambitious human! 👋  
Ready to make your career journey smarter, faster, and less painful? 
---
🚀 How to Use This Smart Tool
📄 Upload Your Resume
Let our AI work its magic 

💬 Enter Your prefferd Job Role or Career Query
This helps us understand your need — required to proceed.

🔍 Click “Submit”
The AI will figure out whether you're looking for jobs, find salaries, or career advice — and deliver accordingly.

🤖 Ask Follow-Up Questions
Want strategy tips, profile improvement suggestions, or just clarity? Ask away.

📥 Download Your Job Report (PDF)
Keep it for offline use or share it with your mentors and friends!

Enjoy the job hunt — we’ve got your back! 💼🔥  
""")

    with gr.Row():
        resume_input = gr.File(label="Upload Resume (PDF)")
        query_input = gr.Textbox(label="Job Role / Query (Required)", placeholder="e.g. Software Developer jobs in Kochi", lines=1)

    find_jobs_btn = gr.Button("🚀 SUBMIT")
    job_output = gr.Textbox(label="Result", lines=20)

    with gr.Accordion("🧾 Resume Info (Internal)", open=False):
        resume_output = gr.JSON()

    find_jobs_btn.click(
        unified_find_jobs,
        inputs=[resume_input, query_input],
        outputs=[job_output, resume_output]
    )

    with gr.Accordion("💬 Follow-up", open=False):
        chatbox = gr.Textbox(label="Ask a question")
        submit_btn = gr.Button("Submit")
        download_btn = gr.Button("📥 Download PDF Summary")
        download_output = gr.File(label="Download PDF")
        chat_output = gr.Markdown()

        submit_btn.click(chat, inputs=chatbox, outputs=chat_output)
        chatbox.submit(chat, inputs=chatbox, outputs=chat_output)

        download_btn.click(
            create_pdf_file,
            inputs=[],
            outputs=download_output
        )

# Launch
demo.launch()
