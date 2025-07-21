# CareerPilot 🚀 – Agentic AI Career Assistant

CareerPilot is an intelligent, context-aware AI agent that helps job seekers find jobs, discover salary insights, and get career guidance — all powered by Google Gemini, real-time APIs, and multi-step reasoning.

Built on Hugging Face Spaces with Gradio, CareerPilot uses your resume and query to automatically classify your intent, invoke the right APIs, retain memory for follow-ups, and generate professional PDF reports.




---

## 🎯 Objective

The goal was to create an **Agentic AI backend** that:
- Performs tasks beyond LLM capabilities using external tools
- Handles multi-turn, memory-aware interactions
- Demonstrates modular task orchestration across APIs


## 🎥 Demo
 - Hosted On Hugging Face Space https://huggingface.co/spaces/malavika-2016/CareerPilot
 - Demo Video https://youtu.be/UIiZRUMUcqU
   

---

## 🧩 Features

<img width="1536" height="1024" alt="Architecture_CareerPilot" src="https://github.com/user-attachments/assets/aaa0309e-0a74-46b4-8989-ce2ea33e5963" />



✅ **Resume Analysis**  
Parses resume content using Google Gemini and extracts:
- Job role preference
- Experience level
- Location preference
- Summary of skills and background

✅ **Query Classification**  
Classifies user query into one of three categories:
- `job_search`
- `salary_search`
- `career_advice`

✅ **Job Search (via SERPAPI)**  
Finds top job listings in real time using SERPAPI.

✅ **Salary Insights (via RapidAPI)**  
Provides salary breakdown (base, bonus, median) based on company, role, location, and experience.

✅ **Career Advice (via Gemini)**  
Uses LLM reasoning with resume context to provide detailed, helpful suggestions for career planning.

✅ **Memory & Multi-Step Reasoning**  
Each step stores state across the workflow to enable:
- Contextual chat follow-up
- Strategy discussions
- PDF generation with combined outputs

✅ **Professional PDF Report Generation**  
Summarizes outputs and advice into a downloadable PDF using `fpdf`.

---

## 🛠️ Tech Stack

| Layer            | Technology            |
|------------------|------------------------|
| LLM Reasoning    | Google Gemini 2.5 Flash |
| UI               | Gradio (Hugging Face Space) |
| Backend          | Python (modular functions) |
| Resume Parsing   | Gemini PDF input analysis |
| Job Search API   | SERPAPI (Google Jobs)     |
| Salary API       | RapidAPI – Job Salary Data |
| PDF Generation   | `fpdf`                   |

---

## 🧠 Agentic Workflow

```text
[User Resume + Query]
       ↓
[Gemini LLM Resume Parsing]
       ↓
[Query Classification]
 → Job Search
 → Salary Lookup
 → Career Guidance
       ↓
[Tool Call / API Invocation]
       ↓
[Tool Output + Memory Saved]
       ↓
[User Follow-Up Query]
       ↓
[LLM Response with Memory Context]
       ↓
[Generate Structured PDF Summary]
