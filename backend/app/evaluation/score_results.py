import pandas as pd
import json
from openai import OpenAI

# -----------------------------
# CONFIGURATION
# -----------------------------

NVIDIA_API_KEY = "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"

client = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)

MODEL_NAME = "abacusai/dracarys-llama-3.1-70b-instruct"

df = pd.read_csv("evaluation_results.csv")

# -----------------------------
# SCORING FUNCTION
# -----------------------------

def score_pair(prompt, airbot, nvidia_response):
    evaluation_prompt = f"""
You are an aerospace manufacturing expert.

Evaluate the two responses below on a scale of 1-5 for:
1. Domain Specificity
2. Technical Depth
3. Edge Case Validity
4. Manufacturing Realism
5. Structural Clarity

Return ONLY valid JSON in this format:
{{
  "airbot": {{
    "domain": 0,
    "depth": 0,
    "edge": 0,
    "realism": 0,
    "clarity": 0
  }},
  "nvidia": {{
    "domain": 0,
    "depth": 0,
    "edge": 0,
    "realism": 0,
    "clarity": 0
  }}
}}

Prompt:
{prompt}

Airbot Response:
{airbot}

NVIDIA Response:
{nvidia_response}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a strict aerospace evaluation expert. Return only JSON."},
            {"role": "user", "content": evaluation_prompt}
        ],
        temperature=0,
        max_tokens=600,
    )

    return completion.choices[0].message.content.strip()

# -----------------------------
# LOOP & SAVE RESULTS
# -----------------------------

scores = []

for _, row in df.iterrows():
    try:
        result = score_pair(
            row["Prompt"],
            row["Airbot Response"],
            row["NVIDIA Response"]
        )

        # Convert JSON string to dict safely
        parsed = json.loads(result)

        scores.append({
            "Prompt": row["Prompt"],
            "Airbot_domain": parsed["airbot"]["domain"],
            "Airbot_depth": parsed["airbot"]["depth"],
            "Airbot_edge": parsed["airbot"]["edge"],
            "Airbot_realism": parsed["airbot"]["realism"],
            "Airbot_clarity": parsed["airbot"]["clarity"],
            "NVIDIA_domain": parsed["nvidia"]["domain"],
            "NVIDIA_depth": parsed["nvidia"]["depth"],
            "NVIDIA_edge": parsed["nvidia"]["edge"],
            "NVIDIA_realism": parsed["nvidia"]["realism"],
            "NVIDIA_clarity": parsed["nvidia"]["clarity"],
        })

        print("Scored one prompt.")

    except Exception as e:
        print("Error scoring prompt:", e)
        continue

# Save structured scores
pd.DataFrame(scores).to_csv("scored_results_structured.csv", index=False)

print("Scoring complete.")

