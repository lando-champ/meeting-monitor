from __future__ import annotations

import json
import re
from typing import Any, Dict, TypedDict, List

from groq import Groq
from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.consilium.services.requirements_research import (
    extract_competitor_pricing,
    fetch_page,
    search_web,
)


class RequirementsState(TypedDict, total=False):
    product_name: str
    product_description: str
    target_users: str
    key_features: str
    competitors: str
    constraints: str
    kickoff_transcript: str
    prd: Dict[str, Any]
    competitor_evidence: list[Dict[str, Any]]
    research_warnings: list[str]


def _requirement_api_keys() -> List[str]:
    candidates = [
        settings.GROQ_REQUIREMENTS_API_KEY_PRIMARY,
        settings.GROQ_REQUIREMENTS_API_KEY_SECONDARY,
        settings.GROQ_REQUIREMENTS_API_KEY,
        settings.GROQ_API_KEY,
    ]
    deduped: list[str] = []
    for key in candidates:
        k = (key or "").strip()
        if k and k not in deduped:
            deduped.append(k)
    return deduped


def _get_clients() -> list[Groq]:
    keys = _requirement_api_keys()
    if not keys:
        raise RuntimeError(
            "Set GROQ_REQUIREMENTS_API_KEY_PRIMARY or GROQ_REQUIREMENTS_API_KEY_SECONDARY "
            "or GROQ_REQUIREMENTS_API_KEY or GROQ_API_KEY in backend/.env for PRD generation"
        )
    return [Groq(api_key=key) for key in keys]


def _requirements_model() -> str:
    return (settings.GROQ_REQUIREMENTS_MODEL or "llama-3.3-70b-versatile").strip()


def _is_retriable_provider_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    if "ratelimit" in name or "rate limit" in text or "429" in text:
        return True
    if "timeout" in name or "timed out" in text:
        return True
    if "apiconnection" in name or "connection" in text:
        return True
    if "502" in text or "503" in text or "504" in text:
        return True
    return False


# ---------------------------------------------------------------------------
# Root causes of the bad PRD output — and how we fix them:
#
# 1. max_tokens=3500  →  a full PRD needs 7000-8000 tokens. Every section
#    was silently truncated mid-sentence because the model hit the limit.
#    Fix: raise to 8000.
#
# 2. Vague system prompt with no quality bar  →  model defaulted to
#    "React, Angular, or Vue" style hedge lists and generic bullets.
#    Fix: explicit BAD vs GOOD examples inline in the prompt, plus hard
#    rules: one specific technology per layer, real field names, real
#    endpoint paths, measurable SLA values, numbered IDs on requirements.
#
# 3. No instruction to never truncate  →  model cut bullets mid-sentence
#    when approaching its internal length limits.
#    Fix: explicit "complete every sentence" rule in the prompt.
#
# 4. Two-pass generation for long PRDs  →  if the product is complex,
#    one call may still feel rushed. We split into two focused calls:
#    Pass A: narrative sections (overview, problem, users, market,
#            stories, functional/non-functional requirements)
#    Pass B: technical sections (stack, architecture, DB, API, security,
#            performance, deployment, folder structure, milestones, MVP,
#            future)
#    Then merge. Each call gets 8000 tokens and a narrower schema.
#
# 5. No JSON-repair fallback  →  on rare malformed output the agent
#    returned {"raw": "<garbage>"} silently. Fix: retry with an explicit
#    repair prompt.
# ---------------------------------------------------------------------------

# --- Shared quality rules injected into both prompts ---
_QUALITY_RULES = """
QUALITY RULES — violating any of these is unacceptable:
- This is a FULL PRD, not a summary. Do NOT compress, skim, or use terse bullets.
  Expand with concrete examples, rationale, and edge cases until minimums are met.
- Every bullet must be a COMPLETE sentence. Never end mid-sentence.
- Be SPECIFIC and OPINIONATED. Never offer lists of alternatives.
  BAD:  "Use React, Angular, or Vue.js"
  GOOD: "React 18 with TypeScript and Zustand for state management,
         chosen for mature ecosystem and existing team expertise."
- Include REAL names: real competitor names, real library versions,
  real column names, real HTTP method + path pairs.
- Include MEASURABLE thresholds: response times in ms, uptime as %,
  token TTL in minutes, cache TTL in seconds — never vague adjectives.
- Functional requirements use numbered IDs: FR-001, FR-002, etc.
- Non-functional requirements use numbered IDs: NFR-001, NFR-002, etc.
- Return STRICT JSON only. No markdown, no prose outside the JSON object.

MINIMUM DEPTH (count words; under-length output is invalid):
- "overview": at least 110 words.
- "problem_statement": at least 220 words total across its paragraphs.
- "target_users": at least 4 entries; each entry at least 45 words.
- "market_analysis": at least 6 entries; each at least 35 words (name a real product or cite a metric).
- "features": at least 10 entries; each at least 50 words (name the capability, user impact, and success signal).
- "user_stories": at least 10 entries; each includes 3 numbered acceptance criteria.
- "functional_requirements": at least 14 items (FR-001 …) with testable acceptance.
- "non_functional_requirements": at least 10 items (NFR-001 …) with measurable thresholds.

Pass B technical arrays: at least 8 items in tech_stack, database_design, api_design, security,
performance, deployment, folder_structure; at least 6 in system_architecture, milestones,
mvp_scope, future_enhancements. Each string entry must be substantive (not a label-only fragment).
"""

# ---------------------------------------------------------------------------
# PASS A: Narrative / product sections
# ---------------------------------------------------------------------------
_SYSTEM_A = f"""
You are a Principal Product Manager at a top-tier software company writing a
corporate-grade Product Requirements Document (PRD).

{_QUALITY_RULES}

Respond with STRICT JSON matching exactly this schema (honor MINIMUM DEPTH word counts above):
{{
  "executive_summary": "150+ words: strategic context, trust assumptions, target segment, business urgency, why now.",
  "overview": "110+ words: product name, core value proposition, target market segment, differentiators, and scope boundaries.",
  "problem_statement": "220+ words in 3 paragraphs: quantified pain, why incumbents fail, opportunity and urgency.",
  "target_users": [
    "Role title — 2-3 sentences describing their daily workflow, specific pain points, and what success looks like for them in this product."
  ],
  "market_analysis": [
    "Specific competitor name or market data point — their weakness and your differentiation. Each item is 2 sentences."
  ],
  "features": [
    "Feature name: what it does, why it matters, and the measurable outcome it produces. 2-3 sentences each."
  ],
  "user_stories": [
    "As a <specific role>, I want to <specific action with detail> so that <measurable benefit>. Acceptance criteria: (1) <criterion> (2) <criterion> (3) <criterion>."
  ],
  "functional_requirements": [
    "FR-001: <specific, testable requirement — include threshold value, role, or SLA where applicable>."
  ],
  "non_functional_requirements": [
    "NFR-001: <quality attribute with measurable threshold, e.g. p99 API latency < 200ms under 5000 concurrent users>."
  ],
  "risks_and_mitigations": [
    "Risk-001: specific technical/business risk. Mitigation: concrete control, owner, and trigger."
  ],
  "assumptions_and_out_of_scope": [
    "Assumption-001 / OutOfScope-001: explicit boundary conditions and non-goals."
  ]
}}
""".strip()

# ---------------------------------------------------------------------------
# PASS B: Technical architecture sections
# ---------------------------------------------------------------------------
_SYSTEM_B = f"""
You are a Principal Solutions Architect at a top-tier software company writing
the technical sections of a corporate Product Requirements Document (PRD).

{_QUALITY_RULES}

Additional rules for technical sections:
- tech_stack: one specific technology per layer, with version and rationale.
  Format: "Layer — Technology vX.Y: rationale."
- database_design: include real table/collection names with actual column
  names, types, constraints, and index strategy.
  Format: "table_name: col1 TYPE CONSTRAINT, col2 TYPE, ... Index: col."
- api_design: include HTTP method, path, request body fields, response shape,
  auth requirement, and relevant error codes.
  Format: "METHOD /api/v1/path — body: {{fields}}, response: {{fields}},
           auth: JWT, errors: 401, 422."
- folder_structure: real directory paths and what lives in each.

Respond with STRICT JSON matching exactly this schema:
{{
  "tech_stack": [
    "Layer — Technology vX.Y: one-sentence rationale for choosing it over alternatives."
  ],
  "system_architecture": [
    "Architecture decision or component — rationale and trade-offs considered."
  ],
  "database_design": [
    "table_name: field1 TYPE CONSTRAINT, field2 TYPE DEFAULT val. Relationships: FK. Index: field."
  ],
  "api_design": [
    "METHOD /api/v1/path — body: {{field: type}}, returns: {{field: type}}, auth: JWT Bearer, errors: 401 unauthenticated | 422 validation failed."
  ],
  "security": [
    "Security control — specific implementation detail with library/standard used."
  ],
  "performance": [
    "Performance target — measurable SLA and implementation approach to achieve it."
  ],
  "deployment": [
    "Deployment step or infrastructure decision — specific tooling and configuration."
  ],
  "folder_structure": [
    "path/to/dir/ — what lives here and why it is separated from sibling dirs."
  ],
  "milestones": [
    "Week N-M: milestone name — specific deliverables and definition of done."
  ],
  "mvp_scope": [
    "Feature or capability included in MVP — minimum viable version and what is explicitly deferred to Phase 2."
  ],
  "future_enhancements": [
    "Phase N (Quarter YYYY): enhancement name — business rationale and estimated effort."
  ],
  "implementation_notes": [
    "Implementation detail: architecture decision + why + alternative rejected."
  ],
  "observability_and_reason_codes": [
    "ReasonCode + telemetry design: metric/log/trace mapping and diagnostic flow."
  ]
}}
""".strip()


def _norm_tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9]{4,}", (text or "").lower())
        if tok not in {"with", "from", "this", "that", "have", "your", "their"}
    }


def _copy_ratio(seed_text: str, generated_text: str) -> float:
    src = _norm_tokens(seed_text)
    out = _norm_tokens(generated_text)
    if not src or not out:
        return 0.0
    overlap = len(src.intersection(out))
    return overlap / max(1, len(out))


def _text_word_count(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    return len(re.findall(r"\w+", value))


def _list_size(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _quality_issues(part: Dict[str, Any], pass_name: str, seed_text: str) -> list[str]:
    issues: list[str] = []
    if pass_name == "A":
        required = [
            "overview",
            "problem_statement",
            "target_users",
            "features",
            "functional_requirements",
            "non_functional_requirements",
        ]
        for key in required:
            if key not in part:
                issues.append(f"missing_{key}")
        if _text_word_count(part.get("overview")) < 90:
            issues.append("overview_too_short")
        if _text_word_count(part.get("problem_statement")) < 170:
            issues.append("problem_statement_too_short")
        if _list_size(part.get("features")) < 8:
            issues.append("features_too_few")
        if _list_size(part.get("functional_requirements")) < 10:
            issues.append("functional_requirements_too_few")
        if _list_size(part.get("non_functional_requirements")) < 8:
            issues.append("non_functional_requirements_too_few")
        if _list_size(part.get("risks_and_mitigations")) < 5:
            issues.append("risks_too_few")
    else:
        required = [
            "tech_stack",
            "system_architecture",
            "database_design",
            "api_design",
            "security",
            "performance",
        ]
        for key in required:
            if key not in part:
                issues.append(f"missing_{key}")
        if _list_size(part.get("tech_stack")) < 6:
            issues.append("tech_stack_too_few")
        if _list_size(part.get("api_design")) < 6:
            issues.append("api_design_too_few")
        if _list_size(part.get("database_design")) < 6:
            issues.append("database_design_too_few")
        if _list_size(part.get("milestones")) < 5:
            issues.append("milestones_too_few")
        api_blob = " ".join(part.get("api_design") or [])
        if len(re.findall(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", api_blob)) < 3:
            issues.append("api_not_specific_enough")
        nfr_blob = " ".join(part.get("performance") or []) + " " + " ".join(
            part.get("security") or []
        )
        if len(re.findall(r"\b\d+(?:\.\d+)?\s*(ms|s|sec|seconds|%|rpm|tpm|gb|mb)\b", nfr_blob.lower())) < 3:
            issues.append("missing_measurable_thresholds")

    raw_text = json.dumps(part, ensure_ascii=False)
    if _copy_ratio(seed_text, raw_text) > 0.62:
        issues.append("too_similar_to_seed_input")
    return issues


def _call_with_quality_gate(
    clients: list[Groq],
    *,
    system: str,
    user: str,
    pass_name: str,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    attempt = 1
    current_user = user
    all_issues: list[str] = []
    while attempt <= max_attempts:
        result = _call(clients, system, current_user)
        issues = _quality_issues(result, pass_name, user)
        if not issues:
            if all_issues:
                result["_quality_retry_count"] = attempt - 1
            return result
        all_issues.extend(issues)
        current_user = (
            f"{user}\n\n"
            "RETRY INSTRUCTIONS:\n"
            "- The previous output was rejected by quality checks.\n"
            f"- Failed checks: {', '.join(sorted(set(issues)))}.\n"
            "- Rewrite from scratch.\n"
            "- Do not reuse or paraphrase the seed input lines.\n"
            "- Add concrete details, assumptions, trade-offs, and acceptance criteria.\n"
            "- Keep strict JSON shape.\n"
        )
        attempt += 1
    result["_quality_gate_failed"] = True
    result["_quality_gate_issues"] = sorted(set(all_issues))
    return result


def _build_user_prompt(state: RequirementsState) -> str:
    parts = [f"Product name: {state.get('product_name') or 'Unnamed Product'}"]
    parts.append(f"\nProduct description:\n{state.get('product_description') or 'Not provided.'}")
    if state.get("target_users"):
        parts.append(f"\nTarget users:\n{state['target_users']}")
    if state.get("key_features"):
        parts.append(f"\nKey features requested:\n{state['key_features']}")
    if state.get("competitors"):
        parts.append(f"\nKnown competitors:\n{state['competitors']}")
    if state.get("constraints"):
        parts.append(f"\nConstraints / limitations:\n{state['constraints']}")
    if state.get("kickoff_transcript"):
        parts.append(
            "\nKickoff transcript (meeting history selected by user):\n"
            f"{state['kickoff_transcript'][:10000]}"
        )
    if state.get("competitor_evidence"):
        evidence_lines: list[str] = []
        for row in state.get("competitor_evidence") or []:
            evidence_lines.append(
                "- {name} | {url} | confidence={confidence} | pricing={pricing}".format(
                    name=row.get("name", "Unknown"),
                    url=row.get("source_url", ""),
                    confidence=row.get("confidence", 0),
                    pricing=row.get("pricing_summary", "n/a"),
                )
            )
        if evidence_lines:
            parts.append(
                "\nCompetitor research evidence (real web fetches):\n"
                + "\n".join(evidence_lines[:12])
            )
    return "\n".join(parts)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _try_parse(text: str) -> Dict[str, Any] | None:
    try:
        result = json.loads(_strip_fences(text))
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return None


def _repair_json(client: Groq, broken_text: str) -> Dict[str, Any]:
    """Ask the model to fix its own malformed JSON output."""
    resp = client.chat.completions.create(
        model=_requirements_model(),
        messages=[
            {
                "role": "user",
                "content": (
                    "The following text is almost-valid JSON but has syntax errors. "
                    "Return ONLY the corrected JSON — no prose, no fences:\n\n"
                    + broken_text[:12000]
                ),
            }
        ],
        temperature=0.0,
        max_tokens=8192,
    )
    raw = resp.choices[0].message.content or ""
    if isinstance(raw, list):
        raw = "".join(p.get("text", "") for p in raw if isinstance(p, dict))
    result = _try_parse(raw)
    return result if result is not None else {"raw": broken_text, "repair_failed": True}


def _call(clients: list[Groq], system: str, user: str) -> Dict[str, Any]:
    """Try primary/secondary Groq clients with token fallback and JSON repair."""
    last_exc: Exception | None = None
    model = _requirements_model()
    token_budgets = (8192, 6144, 4096, 3072)
    for client in clients:
        for budget in token_budgets:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.2,
                    max_tokens=budget,
                )
                raw = resp.choices[0].message.content or ""
                if isinstance(raw, list):
                    raw = "".join(p.get("text", "") for p in raw if isinstance(p, dict))

                result = _try_parse(raw)
                if result is None:
                    result = _repair_json(client, raw)
                return result
            except Exception as exc:
                last_exc = exc
                if _is_retriable_provider_error(exc):
                    continue
                raise
    if last_exc:
        raise last_exc
    raise RuntimeError("All Groq clients failed for requirements generation")


def _split_competitors(raw: str | None) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    parts = re.split(r"[\n,;|]+", text)
    clean = []
    for p in parts:
        item = p.strip(" -\t")
        if item:
            clean.append(item)
    return clean[:5]


def _build_competitor_evidence(state: RequirementsState) -> tuple[list[Dict[str, Any]], list[str]]:
    product_name = (state.get("product_name") or "").strip()
    product_description = (state.get("product_description") or "").strip()
    competitors = _split_competitors(state.get("competitors"))
    warnings: list[str] = []
    evidence: list[Dict[str, Any]] = []

    if not competitors:
        query = f"{product_name} competitors pricing {product_description[:120]}"
        search_hits = search_web(query, max_results=8)
        for hit in search_hits[:3]:
            title = str(hit.get("title") or "")
            if title:
                competitors.append(title.split("|")[0].strip())
        competitors = list(dict.fromkeys(competitors))[:3]

    for competitor in competitors[:3]:
        query = f"{competitor} pricing plans features"
        hits = search_web(query, max_results=6)
        if not hits:
            warnings.append(f"search_failed:{competitor}")
            continue
        selected_urls = []
        for hit in hits:
            url = str(hit.get("url") or "")
            if not url:
                continue
            lowered = url.lower()
            score = 0
            if "pricing" in lowered:
                score += 2
            if "features" in lowered:
                score += 1
            if score >= 1 or len(selected_urls) < 1:
                selected_urls.append(url)
            if len(selected_urls) >= 2:
                break

        if not selected_urls:
            warnings.append(f"url_selection_failed:{competitor}")
            continue

        for url in selected_urls:
            page = fetch_page(url)
            profile = extract_competitor_pricing(page, competitor_name=competitor)
            evidence.append(profile)
            if page.get("error"):
                warnings.append(f"fetch_failed:{competitor}:{page.get('error')}")
            if len(evidence) >= 6:
                break
        if len(evidence) >= 6:
            break

    return evidence, warnings


def _generate_prd_node(state: RequirementsState) -> RequirementsState:
    clients = _get_clients()
    competitor_evidence, research_warnings = _build_competitor_evidence(state)
    state = {
        **state,
        "competitor_evidence": competitor_evidence,
        "research_warnings": research_warnings,
    }
    user_prompt = _build_user_prompt(state)

    # --- Pass A: narrative sections ---
    part_a = _call_with_quality_gate(
        clients,
        system=_SYSTEM_A,
        user=user_prompt,
        pass_name="A",
    )

    # --- Pass B: technical sections ---
    # Give the technical pass the PRD context from Pass A so it stays consistent.
    tech_context = (
        f"{user_prompt}\n\n"
        f"Product overview already written:\n{part_a.get('overview', '')}\n\n"
        f"Key features already identified:\n"
        + "\n".join(f"- {f}" for f in (part_a.get("features") or [])[:10])
    )
    part_b = _call_with_quality_gate(
        clients,
        system=_SYSTEM_B,
        user=tech_context,
        pass_name="B",
    )

    # Merge both passes into one PRD dict
    prd = {**part_a, **part_b}

    # Sanity-check: if either pass failed to parse, surface the error
    if "raw" in part_a:
        prd["_pass_a_error"] = "JSON parse failed for narrative sections"
    if "raw" in part_b:
        prd["_pass_b_error"] = "JSON parse failed for technical sections"
    if competitor_evidence:
        prd["competitor_evidence"] = competitor_evidence
        prd["research_sources"] = [
            row.get("source_url")
            for row in competitor_evidence
            if row.get("source_url")
        ]
    if research_warnings:
        prd["research_warnings"] = research_warnings
    prd["doc_sections"] = _build_doc_sections(prd)

    return {**state, "prd": prd}


def _build_doc_sections(prd: Dict[str, Any]) -> list[Dict[str, Any]]:
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else ""

    def _list(value: Any) -> list[str]:
        return [str(v).strip() for v in (value or []) if str(v).strip()] if isinstance(value, list) else []

    sections: list[Dict[str, Any]] = [
        {"id": "executive-summary", "title": "Executive Summary", "type": "paragraphs", "content": [_text(prd.get("executive_summary")), _text(prd.get("overview"))]},
        {"id": "problem-space", "title": "Problem Space", "type": "paragraphs", "content": [_text(prd.get("problem_statement"))]},
        {"id": "target-users", "title": "Target Users", "type": "bullets", "content": _list(prd.get("target_users"))},
        {"id": "market-analysis", "title": "Market Analysis", "type": "bullets", "content": _list(prd.get("market_analysis"))},
        {"id": "key-features", "title": "Key Features", "type": "bullets", "content": _list(prd.get("features"))},
        {"id": "user-stories", "title": "User Stories", "type": "bullets", "content": _list(prd.get("user_stories"))},
        {"id": "functional-requirements", "title": "Functional Requirements", "type": "bullets", "content": _list(prd.get("functional_requirements"))},
        {"id": "non-functional-requirements", "title": "Non-Functional Requirements", "type": "bullets", "content": _list(prd.get("non_functional_requirements"))},
        {"id": "system-architecture", "title": "System Architecture", "type": "bullets", "content": _list(prd.get("system_architecture"))},
        {"id": "tech-stack", "title": "Tech Stack", "type": "bullets", "content": _list(prd.get("tech_stack"))},
        {"id": "database-design", "title": "Data Schema Design", "type": "code_or_bullets", "content": _list(prd.get("database_design"))},
        {"id": "api-design", "title": "API Design", "type": "code_or_bullets", "content": _list(prd.get("api_design"))},
        {"id": "security-performance", "title": "Security and Performance", "type": "bullets", "content": _list(prd.get("security")) + _list(prd.get("performance"))},
        {"id": "deployment", "title": "Deployment Plan", "type": "bullets", "content": _list(prd.get("deployment"))},
        {"id": "risks", "title": "Technical Constraints and Risks", "type": "bullets", "content": _list(prd.get("risks_and_mitigations"))},
        {"id": "roadmap", "title": "Roadmap", "type": "bullets", "content": _list(prd.get("milestones"))},
        {"id": "mvp-scope", "title": "MVP Scope", "type": "bullets", "content": _list(prd.get("mvp_scope"))},
        {"id": "future-enhancements", "title": "Future Enhancements", "type": "bullets", "content": _list(prd.get("future_enhancements"))},
    ]
    return [s for s in sections if any((s.get("content") or []))]


# ---------------------------------------------------------------------------
# Graph wiring — public API is unchanged
# ---------------------------------------------------------------------------
_graph = None


def get_requirements_agent():
    global _graph
    if _graph is None:
        workflow = StateGraph(RequirementsState)
        workflow.add_node("generate_prd", _generate_prd_node)
        workflow.set_entry_point("generate_prd")
        workflow.add_edge("generate_prd", END)
        _graph = workflow.compile()
    return _graph


def run_requirements_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    graph = get_requirements_agent()
    result: RequirementsState = graph.invoke(inputs)
    return result["prd"]  # type: ignore[index]