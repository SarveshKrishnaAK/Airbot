import requests
import csv
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types

# -----------------------------
# CONFIGURATION
# -----------------------------

load_dotenv()

AIRBOT_URL = "http://127.0.0.1:8000/chat/"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

materials = ["6061-T6", "2024-T3", "7075-T6", "7050-T7451"]
conditions = [
    "high RPM",
    "thermal cycling",
    "fatigue loading",
    "corrosion exposure",
    "machining tolerance limits"
]

# -----------------------------
# PROMPT GENERATOR
# -----------------------------

def generate_prompt(material, condition):
    return f"""
Generate 4 edge test cases for aircraft propeller blade manufacturing 
using {material} under {condition} conditions.
"""

# -----------------------------
# QUERY AIRBOT
# -----------------------------

def query_airbot(prompt):
    response = requests.post(
        AIRBOT_URL,
        json={"question": prompt, "level": "engineering"}
    )
    return response.json()["answer"]

# -----------------------------
# QUERY GEMINI
# -----------------------------

def query_gemini(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # safe model name
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=400,
        )
    )

    return response.text

# -----------------------------
# SAVE RESULTS
# -----------------------------

def save_results(rows):
    with open("evaluation_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Prompt", "Airbot Response", "Gemini Response"])
        writer.writerows(rows)

# -----------------------------
# MAIN
# -----------------------------

def main():
    results = []

    for material in materials:
        for condition in conditions:
            prompt = generate_prompt(material, condition)

            print("Running:", prompt)

            airbot_resp = query_airbot(prompt)
            gemini_resp = query_gemini(prompt)

            results.append([prompt, airbot_resp, gemini_resp])

    save_results(results)
    print("Evaluation complete. Results saved.")

if __name__ == "__main__":
    main()
