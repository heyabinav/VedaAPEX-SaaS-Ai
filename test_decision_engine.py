import sys
sys.path.insert(0, r'c:\Users\heyhi\Downloads\backend')

from app.services.search_decision_engine import SearchDecisionEngine

test_queries = [
    "What is Python?",
    "What is the latest Python version?",
    "Write a Python function",
    "What happened today?",
    "Latest news about AI",
    "Current price of Bitcoin",
    "Explain REST APIs",
    "Search the web for...",
]

print("\n" + "="*70)
print("SEARCH DECISION ENGINE TEST")
print("="*70 + "\n")

for query in test_queries:
    should_search = SearchDecisionEngine.should_search(query)
    request_type = SearchDecisionEngine.classify_request(query)
    reason = SearchDecisionEngine.get_search_reason(query)
    
    status = "🔍 SEARCH" if should_search else "✓ NO SEARCH"
    print(f"{status}: '{query}'")
    print(f"     Type: {request_type} | Reason: {reason}")
    print()

print("="*70)
print("✓ Test completed successfully")
print("="*70)
