import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from data_loader import load_capability_library

# Load model once at module level (CPU-compatible, ~80MB)
# Try online first, fall back to local cache if no network
try:
    _model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

# Cache for capability embeddings
_capability_embeddings: np.ndarray = None
_capability_records: list[dict] = None

COMPLIANCE_THRESHOLD = 0.65


def _load_capabilities():
    """Load capability library and generate embeddings (runs once)."""
    global _capability_embeddings, _capability_records

    if _capability_embeddings is not None:
        return  # Already loaded

    df = load_capability_library()

    # Build list of capability dicts
    _capability_records = []
    summaries = []

    for _, row in df.iterrows():
        record = {
            "cap_id": str(row.get("cap_id", "")),
            "domain": str(row.get("domain", "")),
            "project_summary": str(row.get("project_summary", "")),
            "certification": str(row.get("certification", "")),
            "year_completed": str(row.get("year_completed", "")),
            "contract_value_pkr": str(row.get("contract_value_pkr", "")),
            "duration_months": str(row.get("duration_months", "")),
            "client_type": str(row.get("client_type", ""))
        }
        _capability_records.append(record)

        # Embed the project_summary + domain for richer matching
        embed_text = f"{record['domain']}. {record['project_summary']}"
        summaries.append(embed_text)

    # Generate all embeddings in one batch (faster than one-by-one)
    _capability_embeddings = _model.encode(
        summaries,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True
    )


def match_requirement(requirement_text: str) -> dict:
    """
    Match a single requirement against the capability library.

    Returns:
    {
        "status": "COMPLIANT" | "NON-COMPLIANT",
        "matched_capability": str,   # best match summary or empty string
        "matched_cap_id": str,
        "similarity_score": float
    }
    """
    _load_capabilities()

    # Embed the requirement
    req_embedding = _model.encode(
        [requirement_text],
        convert_to_numpy=True
    )

    # Compute cosine similarity against all capabilities
    similarities = cosine_similarity(req_embedding, _capability_embeddings)[0]

    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])
    best_cap = _capability_records[best_idx]

    if best_score >= COMPLIANCE_THRESHOLD:
        return {
            "status": "COMPLIANT",
            "matched_capability": best_cap["project_summary"],
            "matched_cap_id": best_cap["cap_id"],
            "similarity_score": round(best_score, 4)
        }
    else:
        return {
            "status": "NON-COMPLIANT",
            "matched_capability": "",
            "matched_cap_id": "",
            "similarity_score": round(best_score, 4)
        }


def run_compliance_check(requirements: list[str]) -> list[dict]:
    """
    Run compliance check on all extracted requirements.

    Returns list of compliance items matching frontend schema:
    [
        {
            "id": "MANDATE-TRD-01",
            "req": "requirement text",
            "match": "matched capability text",
            "status": "COMPLIANT" | "NON-COMPLIANT"
        }
    ]
    """
    _load_capabilities()

    compliance_items = []

    for idx, req_text in enumerate(requirements):
        if not req_text.strip():
            continue

        result = match_requirement(req_text)

        compliance_items.append({
            "id": f"MANDATE-TRD-{idx + 1:02d}",
            "req": req_text.strip(),
            "match": result["matched_capability"],
            "status": result["status"]
        })

    return compliance_items


def get_compliance_stats(compliance_items: list[dict]) -> dict:
    """
    Return summary stats from compliance results.

    Returns:
    {
        "total": int,
        "compliant": int,
        "non_compliant": int,
        "compliance_pct": float,
        "gaps_count": int
    }
    """
    total = len(compliance_items)
    compliant = sum(1 for c in compliance_items if c["status"] == "COMPLIANT")
    non_compliant = total - compliant

    return {
        "total": total,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "compliance_pct": round((compliant / total * 100) if total > 0 else 0, 2),
        "gaps_count": non_compliant
    }