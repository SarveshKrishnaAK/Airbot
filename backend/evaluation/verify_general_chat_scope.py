import argparse
import json
import sys

import requests


EXPECTED_GREETING_PREFIX = "Hello! I'm Airbot"
EXPECTED_FAREWELL_PREFIX = "Goodbye from Airbot!"


def call_chat(base_url: str, question: str) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/",
        json={"question": question, "mode": "general_chat"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("answer", "")


def is_blocked_answer(answer: str) -> bool:
    normalized = answer.lower()
    has_scope_constraint = (
        "limited" in normalized
        or "not allowed" in normalized
        or "outside" in normalized
        or "out of context" in normalized
    )
    has_domain = "aerospace" in normalized or "aircraft" in normalized
    return has_scope_constraint and has_domain


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that general chat allows aerospace questions and blocks off-topic ones."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    aerospace_question = "Explain how lift and drag trade off on an aircraft wing."
    off_topic_question = "Write a chocolate cake recipe."
    greeting_question = "hello"
    greeting_phrase_1 = "good morning"
    greeting_phrase_2 = "how are you"
    greeting_phrase_3 = "good night"
    greeting_phrase_4 = "thank you"
    farewell_phrase_1 = "bye"
    farewell_phrase_2 = "goodbye"
    farewell_phrase_3 = "see you"

    try:
        greeting_answer = call_chat(args.base_url, greeting_question)
        greeting_phrase_answer_1 = call_chat(args.base_url, greeting_phrase_1)
        greeting_phrase_answer_2 = call_chat(args.base_url, greeting_phrase_2)
        greeting_phrase_answer_3 = call_chat(args.base_url, greeting_phrase_3)
        greeting_phrase_answer_4 = call_chat(args.base_url, greeting_phrase_4)
        farewell_phrase_answer_1 = call_chat(args.base_url, farewell_phrase_1)
        farewell_phrase_answer_2 = call_chat(args.base_url, farewell_phrase_2)
        farewell_phrase_answer_3 = call_chat(args.base_url, farewell_phrase_3)
        aerospace_answer = call_chat(args.base_url, aerospace_question)
        off_topic_answer = call_chat(args.base_url, off_topic_question)
    except Exception as exc:
        print(f"ERROR: Request failed: {exc}")
        return 2

    greeting_ok = greeting_answer.strip().startswith(EXPECTED_GREETING_PREFIX)
    greeting_phrase_ok_1 = greeting_phrase_answer_1.strip().startswith(EXPECTED_GREETING_PREFIX)
    greeting_phrase_ok_2 = greeting_phrase_answer_2.strip().startswith(EXPECTED_GREETING_PREFIX)
    greeting_phrase_ok_3 = greeting_phrase_answer_3.strip().startswith(EXPECTED_GREETING_PREFIX)
    greeting_phrase_ok_4 = greeting_phrase_answer_4.strip().startswith(EXPECTED_GREETING_PREFIX)
    farewell_phrase_ok_1 = farewell_phrase_answer_1.strip().startswith(EXPECTED_FAREWELL_PREFIX)
    farewell_phrase_ok_2 = farewell_phrase_answer_2.strip().startswith(EXPECTED_FAREWELL_PREFIX)
    farewell_phrase_ok_3 = farewell_phrase_answer_3.strip().startswith(EXPECTED_FAREWELL_PREFIX)
    aerospace_ok = bool(aerospace_answer.strip()) and not is_blocked_answer(aerospace_answer)
    off_topic_ok = is_blocked_answer(off_topic_answer)

    result = {
        "base_url": args.base_url,
        "greeting_returns_intro": greeting_ok,
        "good_morning_returns_intro": greeting_phrase_ok_1,
        "how_are_you_returns_intro": greeting_phrase_ok_2,
        "good_night_returns_intro": greeting_phrase_ok_3,
        "thank_you_returns_intro": greeting_phrase_ok_4,
        "bye_returns_signoff": farewell_phrase_ok_1,
        "goodbye_returns_signoff": farewell_phrase_ok_2,
        "see_you_returns_signoff": farewell_phrase_ok_3,
        "aerospace_question_allowed": aerospace_ok,
        "off_topic_blocked": off_topic_ok,
        "greeting_answer": greeting_answer,
        "good_morning_answer": greeting_phrase_answer_1,
        "how_are_you_answer": greeting_phrase_answer_2,
        "good_night_answer": greeting_phrase_answer_3,
        "thank_you_answer": greeting_phrase_answer_4,
        "bye_answer": farewell_phrase_answer_1,
        "goodbye_answer": farewell_phrase_answer_2,
        "see_you_answer": farewell_phrase_answer_3,
        "off_topic_answer": off_topic_answer,
    }
    print(json.dumps(result, indent=2))

    if (
        greeting_ok
        and greeting_phrase_ok_1
        and greeting_phrase_ok_2
        and greeting_phrase_ok_3
        and greeting_phrase_ok_4
        and farewell_phrase_ok_1
        and farewell_phrase_ok_2
        and farewell_phrase_ok_3
        and aerospace_ok
        and off_topic_ok
    ):
        print("PASS: general_chat scope guard is working.")
        return 0

    print("FAIL: general_chat scope guard behavior is not as expected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
