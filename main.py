import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from supabase import create_client, Client

from parser import parse_rfp
from rag_engine import run_compliance_check, get_compliance_stats
from scoring import calculate_win_probability
from proposal_engine import build_proposal, export_proposal_to_docx

load_dotenv()

# --- Supabase client ---
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("TRIDENT API starting...")
    print("Pre-loading capability embeddings...")
    from rag_engine import _load_capabilities
    _load_capabilities()
    print("Embeddings ready. TRIDENT is live.")
    yield

# --- FastAPI app ---
app = FastAPI(
    title="TRIDENT API",
    description="AI-Powered Bid & Proposal Response Engine",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORS (allow Fahad's frontend to call this) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "TRIDENT API v1.0.0"}


# ────────────────────────────────────────────────
# MAIN ENDPOINT — Upload RFP PDF → Full Analysis
# ────────────────────────────────────────────────
@app.post("/analyze")
async def analyze_rfp(file: UploadFile = File(...)):
    """
    Full pipeline:
    1. Extract text from PDF
    2. Claude extracts requirements
    3. RAG compliance check
    4. Win probability scoring
    5. Claude generates proposal + directives
    6. Save to Supabase
    7. Return full result
    """

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        # Step 1 + 2: Parse PDF + Extract requirements via Claude
        print(f"[1/5] Parsing PDF: {file.filename}")
        parsed = parse_rfp(file_bytes)
        requirements = parsed["requirements"]

        mandatory_reqs = requirements.get("mandatory_requirements", [])
        sector = requirements.get("sector", "Other")
        budget_pkr = requirements.get("budget_pkr", 0)

        if not mandatory_reqs:
            raise HTTPException(
                status_code=422,
                detail="No mandatory requirements could be extracted from this PDF."
            )

        # Step 3: RAG compliance check
        print(f"[2/5] Running compliance check on {len(mandatory_reqs)} requirements...")
        compliance_items = run_compliance_check(mandatory_reqs)
        stats = get_compliance_stats(compliance_items)

        # Step 4: Win probability scoring
        print("[3/5] Calculating win probability...")
        scoring_result = calculate_win_probability(
            compliance_pct=stats["compliance_pct"],
            gaps_count=stats["gaps_count"],
            sector=sector,
            budget_pkr=budget_pkr
        )

        # Step 5: Build full proposal via Claude
        print("[4/5] Generating proposal with Claude...")
        proposal = build_proposal(
            requirements=requirements,
            compliance_items=compliance_items,
            scoring_result=scoring_result
        )

        # Step 6: Save to Supabase
        print("[5/5] Saving to Supabase...")
        db_record = {
            "win_probability": proposal["win_probability"],
            "budget_score": proposal["budget_score"],
            "capability_score": proposal["capability_score"],
            "decision": proposal["decision"],
            "compliance": proposal["compliance"],
            "directives": proposal["directives"],
            "proposal_narrative": proposal["proposal_narrative"]
        }

        result = supabase.table("proposal_data").insert(db_record).execute()

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Analysis complete but failed to save to Supabase."
            )

        inserted_id = result.data[0].get("id", "unknown")
        print(f"Saved to Supabase. Record ID: {inserted_id}")

        return {
            "success": True,
            "record_id": inserted_id,
            "data": proposal
        }

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude returned malformed JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# ────────────────────────────────────────────────
# EXPORT ENDPOINT — Download latest proposal as DOCX
# ────────────────────────────────────────────────
@app.get("/export/docx")
def export_latest_docx():
    """
    Fetch latest proposal from Supabase and export as Word document.
    """
    try:
        result = (
            supabase.table("proposal_data")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="No proposals found in database.")

        proposal = result.data[0]
        output_path = export_proposal_to_docx(proposal, "trident_proposal.docx")

        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="TRIDENT_Proposal.docx"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ────────────────────────────────────────────────
# FETCH LATEST — For debugging/testing
# ────────────────────────────────────────────────
@app.get("/latest")
def get_latest_proposal():
    """Return the latest proposal record from Supabase."""
    try:
        result = (
            supabase.table("proposal_data")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="No proposals found.")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────
# RUN
# ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )