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

# ─── Config ───────────────────────────────────────────────────────────────────
app    = Flask(__name__)
CORS(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── Keyword pre-check ────────────────────────────────────────────────────────
# If the player's reasoning contains NONE of these words it is flagged as
# too vague before we even hit the AI — mirrors the datastructures.py pattern.
# Keys are lowercase substrings of the epiphany effect; values are the concept
# words we expect a thoughtful player to mention.
REASONING_KEYWORDS: dict[str, list[str]] = {
    # Attack upgrades — player should mention damage, hits, or crits
    "damage":   ["damage", "hit", "crit", "attack", "burst", "pressure"],
    # Shield / defensive upgrades
    "shield":   ["shield", "block", "defend", "protect", "sustain", "tank"],
    # Draw / hand-size upgrades
    "draw":     ["draw", "hand", "cycle", "card", "combo"],
    # Cost-reduction upgrades
    "cost":     ["cost", "energy", "mana", "cheap", "free", "efficient"],
    # Buff / status upgrades
    "vulnerable":["vulnerable", "weaken", "debuff", "status", "setup"],
    "counterattack":["counter", "react", "retaliate", "punish"],
    # Utility / hybrid (fallback — matches anything with an explanation)
    "retrieve": ["retrieve", "recycle", "reuse", "discard", "exhaust"],
    "exhaust":  ["exhaust", "once", "powerful", "big", "nuke"],
}

# Minimum word count for a reasoning answer to be considered non-trivial
MIN_WORD_COUNT = 6


def _check_reasoning_quality(effect: str, student_input: str) -> tuple[bool, str]:
    """
    Returns (passes: bool, hint: str).
    Mirrors check_manual_correct() from datastructures.py.
    Checks:
      1. Answer is long enough to be a real explanation.
      2. At least one keyword group relevant to the chosen effect is addressed.
    """
    words = student_input.strip().split()
    if len(words) < MIN_WORD_COUNT:
        return False, (
            "Your explanation is very short. "
            "Please describe *why* you chose this upgrade and how you plan to use it."
        )

    lower_input  = student_input.lower()
    lower_effect = effect.lower()

    # Find which keyword groups are relevant to this effect
    relevant_groups: list[list[str]] = []
    for trigger, concepts in REASONING_KEYWORDS.items():
        if trigger in lower_effect:
            relevant_groups.append(concepts)

    # If we matched at least one group, check the student addressed it
    if relevant_groups:
        for group in relevant_groups:
            if any(kw in lower_input for kw in group):
                return True, ""
        # None of the relevant concept groups were mentioned
        joined = ", ".join(relevant_groups[0])   # show first group as hint
        return False, (
            f"Your reasoning doesn't seem to address the key mechanic of this upgrade. "
            f"Think about: {joined}."
        )

    # No trigger matched — accept any non-trivial answer (generic upgrade)
    return True, ""


# ─── OpenAI structured-output evaluation ──────────────────────────────────────

def evaluate_epiphany_decision(
    question: str,
    student_input: str,
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
You are a tactical advisor for a strategic card game.

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


#  Extract effect from the prompt string

def _extract_effect(question: str) -> str:
    """
    Pull the 'Effect : ...' line out of the prompt that main.py sends.
    Falls back to the full question string if not found.
    """
    match = re.search(r"Effect\s*:\s*(.+)", question)
    return match.group(1).strip() if match else question


# Flask route

@app.route("/chatgpt", methods=["POST"])
def chatgpt():
    data          = request.get_json(force=True)
    question      = data.get("question", "").strip()
    student_input = data.get("studentInput", "").strip()
    examples      = data.get("examples", [])

    if not question or not student_input:
        return jsonify({"response": "Error: question and studentInput are required."}), 400

    # Step 1: keyword pre-check (fast, free)
    effect = _extract_effect(question)
    passes, hint = _check_reasoning_quality(effect, student_input)

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