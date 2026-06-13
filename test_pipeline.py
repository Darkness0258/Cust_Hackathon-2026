"""Quick integration test for the full Trident pipeline (minus Claude API calls)."""
import sys
sys.path.insert(0, '.')

# Test 1: data_loader
print('=== TEST 1: Data Loader ===')
from data_loader import load_bid_history, load_capability_library, get_sector_win_rate, get_sector_budget_range

bh = load_bid_history()
cl = load_capability_library()
print(f'  Bid history: {len(bh)} rows, cols: {list(bh.columns)[:6]}...')
print(f'  Capability lib: {len(cl)} rows, cols: {list(cl.columns)}')
print(f'  IT win rate: {get_sector_win_rate("IT Services")}')
print(f'  Construction budget range: {get_sector_budget_range("Construction")}')
assert 'sector' in bh.columns, "Missing 'sector' column in bid history"
assert 'outcome' in bh.columns, "Missing 'outcome' column in bid history"
assert 'budget_pkr' in bh.columns, "Missing 'budget_pkr' column in bid history"
assert 'cap_id' in cl.columns, "Missing 'cap_id' column in capability library"
assert 'domain' in cl.columns, "Missing 'domain' column in capability library"
assert 'project_summary' in cl.columns, "Missing 'project_summary' column in capability library"
assert 'contract_value_pkr' in cl.columns, "Missing 'contract_value_pkr' column in capability library"
assert 'duration_months' in cl.columns, "Missing 'duration_months' column in capability library"
print('  PASS\n')

# Test 2: RAG engine
print('=== TEST 2: RAG Engine ===')
from rag_engine import _load_capabilities, match_requirement, run_compliance_check, get_compliance_stats

_load_capabilities()
result = match_requirement('Must have cybersecurity certification')
print(f'  Match result: status={result["status"]}, score={result["similarity_score"]}')
compliance = run_compliance_check([
    'Must have cybersecurity certification',
    'Must have road construction experience'
])
stats = get_compliance_stats(compliance)
print(f'  Compliance items: {len(compliance)}')
print(f'  Stats: {stats}')
for item in compliance:
    print(f'    {item["id"]}: {item["status"]} - {item["req"][:50]}')
print('  PASS\n')

# Test 3: Scoring
print('=== TEST 3: Scoring ===')
from scoring import calculate_win_probability

score = calculate_win_probability(
    compliance_pct=75.0,
    gaps_count=1,
    sector='IT Services',
    budget_pkr=200000000
)
print(f'  Win probability: {score["win_probability"]}%')
print(f'  Budget score: {score["budget_score"]}')
print(f'  Capability score: {score["capability_score"]}')
print(f'  Decision: {score["decision"]}')
assert score["win_probability"] > 0, "Win probability should be > 0"
assert score["decision"], "Decision should not be empty"
print('  PASS\n')

print('=' * 40)
print('ALL TESTS PASSED')
