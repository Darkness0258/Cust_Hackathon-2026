import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url="https://openrouter.ai/api"
)
MODEL = "openrouter/auto"

def extract_requirements(rfp_text: str) -> dict:
    """
    Extract structured requirements from raw RFP/tender text.
    Returns a dict with keys: mandatory_requirements, evaluation_criteria, deadlines, key_questions, sector, budget_pkr
    """
    prompt = f"""You are a government tender analysis expert. Analyze this RFP/tender document text and extract structured information.

RFP TEXT:
{rfp_text[:12000]}

Return ONLY a valid JSON object with exactly this structure (no markdown, no explanation):
{{
  "mandatory_requirements": [
    "requirement text 1",
    "requirement text 2"
  ],
  "evaluation_criteria": [
    "criteria 1",
    "criteria 2"
  ],
  "deadlines": [
    "deadline description 1"
  ],
  "key_questions": [
    "question that needs addressing in proposal"
  ],
  "sector": "best matching sector from: IT, Construction, Healthcare, Defense, Education, Energy, Transport, Finance, Telecom, Other",
  "budget_pkr": 0
}}

Rules:
- mandatory_requirements: extract every MUST, SHALL, REQUIRED item
- evaluation_criteria: scoring criteria, weightages, pass/fail conditions
- deadlines: submission dates, milestones
- key_questions: questions the client wants answered in the proposal
- sector: pick the single best match from the list provided
- budget_pkr: extract numeric budget in PKR (integer), or 0 if not stated
- Return raw JSON only. No triple backticks. No prose.
- CRITICAL: Each mandatory_requirements array item must be ONE single requirement only. Never combine multiple requirements into one string."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    print("CLAUDE RESPONSE BLOCKS:", message.content)
    # Extract text from the first text block, ignoring thinking blocks
    text_blocks = [b.text for b in message.content if getattr(b, 'type', '') == 'text']
    raw = text_blocks[0].strip() if text_blocks else ""

    # Use regex to find JSON object
    import re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    else:
        # Fallback to naive clean
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


def generate_proposal_narrative(
    requirements: list[str],
    compliance_items: list[dict],
    sector: str,
    win_probability: int,
    decision: str
) -> str:
    """
    Generate a full professional proposal narrative.
    compliance_items: list of {id, req, match, status}
    """
    compliant_items = [c for c in compliance_items if c["status"] == "COMPLIANT"]
    gaps = [c for c in compliance_items if c["status"] == "NON-COMPLIANT"]

    compliant_text = "\n".join(
        f"- {c['req']} → {c['match']}" for c in compliant_items
    )
    gaps_text = "\n".join(f"- {g['req']}" for g in gaps) or "None identified"

    prompt = f"""You are a senior proposal writer for TEKROWE Systems, a Pakistani IT and engineering firm.
Write a complete formal government tender proposal. Replace ALL placeholders with real data provided below.
Never use brackets like [mention X] or [Your Company]. Always use the actual data given.

TENDER SECTOR: {sector}
WIN PROBABILITY: {win_probability}%
DECISION: {decision}

REAL REQUIREMENTS FROM THIS TENDER:
{chr(10).join(f'- {r}' for r in requirements) if requirements else 'General IT infrastructure and software delivery'}

TEKROWE MATCHED CAPABILITIES (use these as past project references):
{compliant_text if compliant_text else 'General IT delivery, software development, cloud infrastructure, project management'}

GAPS (address with mitigation plans, do NOT mention them as failures):
{gaps_text}

Write exactly these sections with these exact headers:
Executive Summary
Understanding of Requirements
Our Capabilities & Relevant Experience
Technical Approach
Why Choose Us
Conclusion

Critical rules:
- Company name: TEKROWE Systems (always, never a placeholder)
- Use the REAL requirements listed above — quote them specifically
- Use the REAL matched capabilities as past project evidence
- Zero placeholders, zero brackets, zero generic examples
- Never decline or withdraw
- Full prose paragraphs only
- 550-700 words"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system="You are a proposal writer for TEKROWE Systems, a Pakistani IT and engineering firm based in Islamabad. Always refer to the company as 'TEKROWE Systems'. Never use placeholders like [Your Company Name].",
        messages=[{"role": "user", "content": prompt}]
    )

    print("CLAUDE RESPONSE BLOCKS:", message.content)
    # Extract text from the first text block, ignoring thinking blocks
    text_blocks = [b.text for b in message.content if getattr(b, 'type', '') == 'text']
    return text_blocks[0].strip() if text_blocks else ""


def generate_directives(
    requirements: list[str],
    compliance_items: list[dict],
    decision: str
) -> list[str]:
    """
    Generate 4-6 actionable strategic directives as HTML strings.
    Each directive looks like: "<strong>Directive § X.X.X</strong><br>description"
    """
    req_text = "\n".join(f"- {r}" for r in requirements)
    gaps = [c["req"] for c in compliance_items if c["status"] == "NON-COMPLIANT"]
    gaps_text = "\n".join(f"- {g}" for g in gaps) or "None"

    prompt = f"""You are a bid strategy consultant. Based on this tender analysis, generate exactly 5 strategic directives.

DECISION: {decision}
REQUIREMENTS:
{req_text}

IDENTIFIED GAPS:
{gaps_text}

Return ONLY a valid JSON array of exactly 5 strings. Each string must be HTML in this exact format:
"<strong>Directive § X.X.X</strong><br>One clear actionable instruction for the bid team."

Example:
[
  "<strong>Directive § 1.1.1</strong><br>Assign a dedicated compliance officer to track all mandatory certification deadlines.",
  "<strong>Directive § 1.1.2</strong><br>Partner with a certified cybersecurity firm to close the ISO 27001 capability gap before submission."
]

Rules:
- Number directives sequentially: 1.1.1, 1.1.2, 1.1.3, 1.1.4, 1.1.5
- Each directive must be actionable and specific to the tender context
- Address gaps directly where they exist
- Return raw JSON array only. No markdown. No explanation."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system="You are a proposal writer for TEKROWE Systems, a Pakistani IT and engineering firm based in Islamabad. Always refer to the company as 'TEKROWE Systems'. Never use placeholders like [Your Company Name].",
        messages=[{"role": "user", "content": prompt}]
    )

    print("CLAUDE RESPONSE BLOCKS:", message.content)
    text_blocks = [b.text for b in message.content if getattr(b, 'type', '') == 'text']
    raw = text_blocks[0].strip() if text_blocks else ""

    # Use regex to find JSON array
    import re
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    else:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


def generate_gonogo_reasoning(
    win_probability: int,
    decision: str,
    sector: str,
    compliance_pct: float,
    gaps_count: int
) -> str:
    """Returns a 2-sentence GO/NO-GO reasoning string."""
    prompt = f"""You are a bid strategist. Write exactly 2 sentences explaining this GO/NO-GO decision.

Decision: {decision}
Win Probability: {win_probability}%
Sector: {sector}
Compliance Rate: {compliance_pct:.0f}%
Gaps Found: {gaps_count}

Rules:
- Sentence 1: State the decision and primary reason (compliance/sector strength)
- Sentence 2: Address the main risk or opportunity
- Tone: Direct, professional, data-driven
- Return plain text only. No labels. No JSON."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system="You are a proposal writer for TEKROWE Systems, a Pakistani IT and engineering firm based in Islamabad. Always refer to the company as 'TEKROWE Systems'. Never use placeholders like [Your Company Name].",
        messages=[{"role": "user", "content": prompt}]
    )

    print("CLAUDE RESPONSE BLOCKS:", message.content)
    text_blocks = [b.text for b in message.content if getattr(b, 'type', '') == 'text']
    return text_blocks[0].strip() if text_blocks else ""