import json
import sys
from pathlib import Path

# Add parent directory to path so we can import rag module
sys.path.append(str(Path(__file__).parent.parent))

from rag.qa_chain_free import get_qa_chain

print("Loading QA chain...")
qa = get_qa_chain()

print("Loading test cases...")
with open("evaluation/text_set.json") as f:
    tests = json.load(f)

print(f"\nRunning {len(tests)} test cases...\n")

score = 0
for i, test in enumerate(tests, 1):
    print(f"Test {i}: {test['question']}")
    response = qa({"question": test["question"], "chat_history": []})
    answer = response["answer"].lower()

    # Check if all expected keywords are in the answer
    keywords_found = [kw for kw in test["expected_keywords"] if kw.lower() in answer]

    if all(word.lower() in answer for word in test["expected_keywords"]):
        score += 1
        print(f"✅ PASS - Found keywords: {keywords_found}")
    else:
        print(f"❌ FAIL - Found: {keywords_found}, Missing: {[kw for kw in test['expected_keywords'] if kw.lower() not in answer]}")

    print(f"Answer: {answer[:200]}...\n")

accuracy = score / len(tests)
print(f"\n{'='*50}")
print(f"Final Accuracy: {accuracy:.2%} ({score}/{len(tests)} tests passed)")
print(f"{'='*50}")
