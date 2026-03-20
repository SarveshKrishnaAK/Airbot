import argparse
import json
import sys

import requests


EXPECTED_BLOCK = (
    "I'm not allowed to answer questions outside aerospace/aircraft context. "
    "Please ask an aerospace- or aircraft-related question."
)


def call_chat(base_url: str, question: str) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/",
        json={"question": question, "mode": "general_chat"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("answer", "")


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

    try:
        aerospace_answer = call_chat(args.base_url, aerospace_question)
        off_topic_answer = call_chat(args.base_url, off_topic_question)
    except Exception as exc:
        print(f"ERROR: Request failed: {exc}")
        return 2

    aerospace_ok = bool(aerospace_answer.strip()) and aerospace_answer.strip() != EXPECTED_BLOCK
    off_topic_ok = off_topic_answer.strip() == EXPECTED_BLOCK

    result = {
        "base_url": args.base_url,
        "aerospace_question_allowed": aerospace_ok,
        "off_topic_blocked": off_topic_ok,
        "off_topic_answer": off_topic_answer,
    }
    print(json.dumps(result, indent=2))

    if aerospace_ok and off_topic_ok:
        print("PASS: general_chat scope guard is working.")
        return 0

    print("FAIL: general_chat scope guard behavior is not as expected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
