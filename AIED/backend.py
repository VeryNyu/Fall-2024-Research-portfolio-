"""
backend.py — Flask backend for the Card Epiphany Selector
Modeled on datastructures.py (OpenAI structured outputs + keyword pre-check).

POST /chatgpt
  Body : { "question": <full prompt string>,
           "studentInput": <player's reasoning text>,
           "examples": [] }
  Reply: { "response": <feedback string> }
"""

import os
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from typing import List, Dict, Tuple

# ─── Config ───────────────────────────────────────────────────────────────────
app    = Flask(__name__)
CORS(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


MIN_WORD_COUNT = 6
MIN_BIGRAM_MATCHES = 2


def _build_bigrams(text: str) -> set[str]:
    words = text.lower().split()
    return {f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)}


def _extract_effect_bigrams(options: List[Dict]) -> set[str]:
    bigrams = set()
    for obj in options:
        effect_text = obj.get("effects", "")
        bigrams.update(_build_bigrams(effect_text))
    return bigrams


def _check_reasoning_quality(options: List[Dict], student_input: str) -> Tuple[bool, str]:
    words = student_input.strip().split()
    if len(words) < MIN_WORD_COUNT:
        return False, (
            "Your explanation is very short. "
            "Please describe why you chose this upgrade and how you plan to use it."
        )

    input_bigrams = _build_bigrams(student_input)
    effect_bigrams = _extract_effect_bigrams(options)

    matches = input_bigrams.intersection(effect_bigrams)

    if len(matches) >= MIN_BIGRAM_MATCHES:
        return True, ""

    return False, (
        "Your explanation doesn't seem to reference the upgrade's effect clearly. "
        "Try mentioning what the upgrade actually does and how it helps you."
    )


# ─── OpenAI structured-output evaluation ──────────────────────────────────────

def evaluate_epiphany_decision(
    question: str,
    student_input: str,
    options: list[Dict],
    examples: list[str] | None = None,
) -> dict:
    """
    Calls GPT-4o-mini with a structured JSON schema response.
    Returns {"feedback": str, "is_correct": bool, "rating": int}.
    Mirrors evaluate_student_answer() from datastructures.py.
    """
    examples_text = ""
    if isinstance(examples, list) and examples:
        examples_text = f"Additional context / examples:\n{chr(10).join(examples)}\n"

    prompt = f"""
{question}

{examples_text}

Player's Reasoning:
{student_input}

Your task:
DO NOT:
- Make up card mechanics not described above.
- Simply restate the effect.
- Be overly harsh.

DO:
- Evaluate whether the player's reasoning shows understanding of the upgrade's mechanics.
- Comment on how well this upgrade fits a tactical game plan.
- Suggest one specific way to maximise the upgrade's value.
- Rate the overall reasoning quality from 1 (very weak) to 5 (excellent).
- Determine whether the reasoning demonstrates a correct and thoughtful understanding.

Return JSON in this exact format:
{{
  "feedback": "<your detailed feedback string>",
  "is_correct": <true if reasoning is sound, false otherwise>,
  "rating": <integer 1-5>
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "epiphany_feedback",
                "schema": {
                    "type": "object",
                    "properties": {
                        "feedback":   {"type": "string"},
                        "is_correct": {"type": "boolean"},
                        "rating":     {"type": "integer"},
                    },
                    "required": ["feedback", "is_correct", "rating"],
                },
            },
        },
    )

    content = response.choices[0].message.content
    return json.loads(content)


# Flask route

@app.route("/chatgpt", methods=["POST"])
def chatgpt():
    data          = request.get_json(force=True)
    question      = data.get("question", "").strip()
    student_input = data.get("studentInput", "").strip()
    options       = data.get("options", [])
    examples      = data.get("examples", [])

    if not question or not student_input:
        return jsonify({"response": "Error: question and studentInput are required."}), 400

    passes, hint = _check_reasoning_quality(options, student_input)

    if not passes:
        # Return the hint immediately without calling the A
        response_text = (
            f"Your reasoning needs more depth.\n\n{hint}\n\n"
            "Please go back, reconsider, and explain your choice more thoroughly."
        )
        return jsonify({"response": response_text})

    # Step 2: OpenAI structured-output evaluation
    try:
        result = evaluate_epiphany_decision(
            question=question,
            student_input=student_input,
            options=options,
            examples=examples,
        )
    except Exception as e:
        return jsonify({"response": f"AI Error: {e}"}), 500

    # Step 3: Build human-readable response string
    rating_bar  = "★" * result["rating"] + "☆" * (5 - result["rating"])
    verdict     = " Sound reasoning!" if result["is_correct"] else "Reasoning needs work."
    response_text = (
        f"{verdict}   [{rating_bar}]\n\n"
        f"{result['feedback']}"
    )

    return jsonify({"response": response_text})


#  Health check

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Entry point

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)