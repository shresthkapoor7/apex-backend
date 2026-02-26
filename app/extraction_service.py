import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-3-flash-preview")


def extract_metrics(full_text: str):
    prompt = f"""
Extract structured financial data from this commercial real estate offering memorandum.

Return ONLY valid JSON. Do not include markdown. Do not include explanation text.

Schema:
{{
  "purchase_price": number or null,
  "noi": number or null,
  "cap_rate": decimal like 0.065 or null,
  "occupancy": decimal like 0.92 or null,
  "units": integer or null,
  "year_built": integer or null,
  "property_type": string or null,
  "location": string or null,
  "risk_summary": string or null
}}

If a value is not found, return null.

Text:
{full_text[:12000]}
"""

    response = model.generate_content(prompt)

    raw = (response.text or "").strip()

    print("Gemini raw response:", raw)

    # ✅ Remove markdown code fences safely
    if raw.startswith("```"):
        raw = raw.replace("```json", "")
        raw = raw.replace("```", "")
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed

    except Exception as e:
        print("JSON parsing failed:", e)
        print("Raw response was:", raw)

        # ✅ Safe fallback so pipeline never crashes
        return {
            "purchase_price": None,
            "noi": None,
            "cap_rate": None,
            "occupancy": None,
            "units": None,
            "year_built": None,
            "property_type": None,
            "location": None,
            "risk_summary": "Extraction failed",
        }