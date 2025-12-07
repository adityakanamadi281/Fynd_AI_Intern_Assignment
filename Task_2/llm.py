# llm.py
import os
import json
import requests
from dotenv import load_dotenv

# Load .env locally; on HF Spaces you’ll set secrets via UI instead
load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"  # or any other instruct model

API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}


class LLMError(Exception):
    pass


def call_llm(prompt: str, max_new_tokens: int = 256) -> str:
    if not HF_API_TOKEN:
        raise LLMError("HF_API_TOKEN is not set in environment variables.")

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.4,
        }
    }
    resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
    if resp.status_code != 200:
        raise LLMError(f"HF API error: {resp.status_code} - {resp.text}")

    data = resp.json()

    # HF inference can return list[dict] or dict; handle both
    if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
        return data[0]["generated_text"]
    elif isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    else:
        # Worst case: just str(data)
        return str(data)


def build_prompt(rating: int, review: str) -> str:
    return f"""
You are an AI assistant helping a business understand customer feedback.

You will receive:
- A star rating (1 to 5)
- A short free-text review

Your tasks:
1. Write a short, warm, user-facing reply directly to the customer.
2. Summarise the essence of the review in <= 20 words.
3. Suggest 2–3 concrete next actions for the business.

Return ONLY a valid JSON object with these exact keys:
- "user_response": string
- "summary": string
- "actions": array of strings

Example of the required format:
{{
  "user_response": "Thank you for your feedback...",
  "summary": "Customer loved the food but found service slow.",
  "actions": [
    "Train staff to reduce wait time",
    "Monitor peak hours and add staff"
  ]
}}

Now generate the JSON.

Rating: {rating}
Review: \"\"\"{review}\"\"\" 

JSON:
""".strip()


def parse_llm_json(raw_text: str) -> dict:
    """
    Try to extract the first JSON object from the LLM output.
    """
    # Find first { and last }
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("No JSON object found in LLM output.")

    json_str = raw_text[start:end+1]
    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMError(f"Failed to parse JSON: {e}")
    return obj


def generate_feedback(rating: int, review: str) -> dict:
    """
    Main function used by dashboards.
    Returns:
      {
        "user_response": str,
        "summary": str,
        "actions": [str, ...]
      }
    """
    prompt = build_prompt(rating, review)
    raw_output = call_llm(prompt)
    data = parse_llm_json(raw_output)

    # Basic safety defaults
    user_response = data.get("user_response", "Thank you for your feedback!")
    summary = data.get("summary", "Customer left feedback.")
    actions = data.get("actions", [])
    if not isinstance(actions, list):
        actions = [str(actions)]

    return {
        "user_response": user_response,
        "summary": summary,
        "actions": actions,
    }
