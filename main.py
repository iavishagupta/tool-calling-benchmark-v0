"""
Main benchmark runner.

Flow: question -> prompt (with schema) -> LLM raw text output ->
decode_ast() -> ast_checker() against ground truth -> score.
"""

import json
import os
from openai import OpenAI  # swap for whichever provider/local model you're testing
from ast_utils import decode_ast, ast_checker

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # or point base_url at a local Hindi model server


def build_system_prompt(tools_schema):
    """
    Tells the model exactly what tools exist and the exact output format
    we need, so decode_ast() can parse it. This is the prompt-engineering
    equivalent of what OpenAI's native function-calling does internally.
    """
    return f"""आपको निम्नलिखित टूल्स दिए गए हैं:

{json.dumps(tools_schema, ensure_ascii=False, indent=2)}

उपयोगकर्ता के प्रश्न के आधार पर सही टूल(स) को कॉल करें।
जवाब में केवल फंक्शन कॉल लिखें, कोई अतिरिक्त टेक्स्ट नहीं।

फॉर्मेट:
- एक कॉल: func_name(param="value")
- कई कॉल: [func_name1(param="value"), func_name2(param="value")]
- कोई भी टूल उपयुक्त न हो तो: []
"""


def call_llm(system_prompt, user_query):
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # swap for the model you're actually benchmarking
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def run_benchmark():
    with open("tools_schema.json", encoding="utf-8") as f:
        tools_schema = json.load(f)
    with open("hindi_dataset.json", encoding="utf-8") as f:
        dataset = json.load(f)["queries"]
    with open("hindi_ground_truth.json", encoding="utf-8") as f:
        ground_truths = json.load(f)

    system_prompt = build_system_prompt(tools_schema)

    passed = 0
    results = []

    for item in dataset:
        qid = item["id"]
        user_query = item["question"][0]["content"]

        raw_output = call_llm(system_prompt, user_query)
        decoded = decode_ast(raw_output)
        check = ast_checker(decoded, ground_truths[qid])

        status = "PASS" if check["valid"] else "FAIL"
        print(f"[{status}] {qid}: {user_query}")
        if not check["valid"]:
            print(f"        raw_output = {raw_output!r}")
            print(f"        reason     = {check['error']}")

        if check["valid"]:
            passed += 1
        results.append({"id": qid, "status": status, "raw_output": raw_output, "reason": check["error"]})

    print(f"\nScore: {passed}/{len(dataset)}")

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_benchmark()