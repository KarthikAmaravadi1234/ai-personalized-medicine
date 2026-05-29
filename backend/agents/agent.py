"""The health agent.

``RuleBasedAgent`` is the offline default: it performs real tool-calling over the
patient's data and the knowledge base with no LLM, so it runs and tests offline.
``OpenAIAgent`` reuses the same grounding + guardrails but lets GPT phrase the answer.
``get_agent`` selects the LLM agent when a key and the ``openai`` package are available,
and falls back to the rule-based agent otherwise.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.agents import tools
from backend.agents.guardrails import apply_guardrails
from backend.agents.prompts import SYSTEM_PROMPT
from backend.agents.tools import GatheredContext, ToolCall, bmi_category
from backend.rag.retriever import Retriever
from backend.rag.store import SearchHit

logger = logging.getLogger(__name__)


class PatientNotFoundError(Exception):
    """Raised when the requested patient does not exist."""


@dataclass
class Citation:
    source: str
    chunk_index: int
    excerpt: str
    score: float


@dataclass
class AgentResponse:
    patient_id: int
    answer: str
    citations: list[Citation] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    guardrail_notes: list[str] = field(default_factory=list)


# Keyword -> knowledge query hints, used to decide when to consult the knowledge base.
_TOPIC_HINTS = {
    "ldl": "LDL cholesterol",
    "hdl": "HDL cholesterol",
    "cholesterol": "cholesterol",
    "triglyceride": "triglycerides",
    "glucose": "fasting glucose diabetes",
    "sugar": "fasting glucose diabetes",
    "a1c": "HbA1c diabetes",
    "hba1c": "HbA1c diabetes",
    "diabet": "type 2 diabetes",
    "blood pressure": "high blood pressure hypertension",
    "hypertens": "high blood pressure hypertension",
    "bmi": "body mass index weight",
    "weight": "body mass index weight",
}

# Knowledge hits below this similarity are treated as irrelevant and not cited.
_KNOWLEDGE_MIN_SCORE = 0.1

# Phrases that signal the user wants an explanation/advice, not just a value.
_EXPLAIN_TRIGGERS = (
    "mean", "meaning", "why", "explain", "cause", "how do", "how can", "how to",
    "tell me about", "what should", "lower", "raise", "reduce", "improve", "manage",
)

# Word-boundary patterns for demographic fields (avoid substrings like "age" in "manage").
_DEMO_PATTERNS: dict[str, re.Pattern[str]] = {
    "age": re.compile(r"\b(age|how old|years old)\b"),
    "sex": re.compile(r"\b(sex|gender)\b"),
    "height": re.compile(r"\b(height|how tall|tall)\b"),
    "weight": re.compile(r"\b(weight|weigh|weighs)\b"),
}

# Question keyword -> fragment that should appear in the matching lab's test name.
_LAB_KEYWORDS = {
    "ldl": "ldl",
    "hdl": "hdl",
    "triglyceride": "triglyceride",
    "a1c": "a1c",
    "hba1c": "a1c",
    "glucose": "glucose",
    "sugar": "glucose",
    "cholesterol": "cholesterol",
}


class RuleBasedAgent:
    def __init__(self, db: Session, retriever: Retriever) -> None:
        self.db = db
        self.retriever = retriever

    def _gather(self, patient_id: int, message: str) -> GatheredContext:
        patient = tools.get_patient(self.db, patient_id)
        if patient is None:
            raise PatientNotFoundError(f"Patient {patient_id} not found")

        ctx = GatheredContext(patient=patient)
        lowered = message.lower()

        wants_labs = any(w in lowered for w in ("lab", "ldl", "hdl", "cholesterol", "glucose", "a1c", "hba1c", "triglyceride"))
        wants_vitals = any(w in lowered for w in ("vital", "blood pressure", "heart rate", "pulse", "sleep", "steps"))
        wants_bmi = any(w in lowered for w in ("bmi", "weight", "body mass"))
        wants_risk = any(w in lowered for w in ("risk", "diabet", "chance", "likelihood", "likely"))
        wants_demographics = any(p.search(lowered) for p in _DEMO_PATTERNS.values())
        # Default to showing labs only for a generic question ("how am I doing?"),
        # never when the user asked about a demographic field like age.
        if not (wants_labs or wants_vitals or wants_bmi or wants_risk or wants_demographics):
            wants_labs = True

        if wants_labs:
            ctx.labs = tools.get_patient_labs(self.db, patient_id)
            ctx.tool_calls.append(
                ToolCall("get_patient_labs", {"patient_id": patient_id}, f"{len(ctx.labs)} lab results")
            )
        if wants_vitals:
            ctx.vitals = tools.get_patient_vitals(self.db, patient_id)
            ctx.tool_calls.append(
                ToolCall("get_patient_vitals", {"patient_id": patient_id}, f"{len(ctx.vitals)} vital records")
            )
        if wants_bmi:
            ctx.bmi = tools.calculate_bmi(patient.height_cm, patient.weight_kg)
            ctx.tool_calls.append(
                ToolCall(
                    "calculate_bmi",
                    {"height_cm": patient.height_cm, "weight_kg": patient.weight_kg},
                    f"BMI={ctx.bmi}",
                )
            )

        if wants_risk:
            # Lazy import avoids a circular import (ml.features imports agent tools).
            from backend.ml.predict import score_patient

            _, prediction = score_patient(self.db, patient)
            ctx.risk = prediction
            ctx.tool_calls.append(
                ToolCall(
                    "get_risk_score",
                    {"patient_id": patient_id, "condition": "type_2_diabetes"},
                    f"{prediction.risk_level} ({prediction.probability})",
                )
            )

        query = self._knowledge_query(lowered, ctx, wants_risk=wants_risk)
        if query:
            hits = tools.search_knowledge(self.retriever, query, top_k=3)
            # Drop weakly-related hits so the agent never cites an off-topic document.
            ctx.knowledge_hits = [h for h in hits if h.score >= _KNOWLEDGE_MIN_SCORE]
            ctx.tool_calls.append(
                ToolCall("search_knowledge", {"query": query}, f"{len(ctx.knowledge_hits)} hits")
            )

        # Semantic retrieval over this patient's own records, so free-form questions
        # surface the most relevant facts even when keyword gating did not load them.
        ctx.patient_hits = self._search_patient_record(patient_id, patient, message, ctx)
        ctx.tool_calls.append(
            ToolCall(
                "search_patient_record",
                {"patient_id": patient_id},
                f"{len(ctx.patient_hits)} patient facts",
            )
        )
        return ctx

    def _search_patient_record(
        self, patient_id: int, patient, message: str, ctx: GatheredContext
    ) -> list[SearchHit]:
        """Build a fresh, patient-scoped vector index and return the closest facts."""
        from backend.rag.patient_docs import build_patient_documents

        # Use whatever the keyword pass already loaded; otherwise fetch the full record
        # so the patient index is complete regardless of the question's wording.
        labs = ctx.labs or tools.get_patient_labs(self.db, patient_id)
        vitals = ctx.vitals or tools.get_patient_vitals(self.db, patient_id)
        bmi = ctx.bmi if ctx.bmi is not None else tools.calculate_bmi(
            patient.height_cm, patient.weight_kg
        )
        docs = build_patient_documents(patient, labs, vitals, bmi, ctx.risk)
        return self.retriever.search_documents(message, docs, top_k=3)

    @staticmethod
    def _knowledge_query(lowered: str, ctx: GatheredContext, *, wants_risk: bool = False) -> str:
        hints = [hint for key, hint in _TOPIC_HINTS.items() if key in lowered]
        if wants_risk:
            hints.append("type 2 diabetes")
        # Drop a hint when a more specific one already contains it (e.g. keep
        # "LDL cholesterol" and drop the generic "cholesterol") so the query is not
        # diluted toward broader documents.
        hints = [
            h for h in dict.fromkeys(hints)
            if not any(other != h and h in other for other in hints)
        ]
        if hints:
            return "; ".join(hints)
        # Fall back to topics implied by abnormal labs so answers stay grounded.
        abnormal = [lab.test_name for lab in ctx.labs if lab.flag != "normal"]
        return "; ".join(abnormal) if abnormal else ""

    @staticmethod
    def _detect_intent(lowered: str) -> str:
        """Classify the question so the answer targets exactly what was asked."""
        if any(t in lowered for t in _EXPLAIN_TRIGGERS):
            return "explain"
        if any(p.search(lowered) for p in _DEMO_PATTERNS.values()):
            return "demographics"
        if "bmi" in lowered or "body mass" in lowered:
            return "bmi"
        if any(k in lowered for k in _LAB_KEYWORDS) or "lab" in lowered:
            return "specific_lab"
        if any(w in lowered for w in ("blood pressure", "bp", "heart rate", "pulse", "sleep", "steps", "vital")):
            return "vitals"
        if any(w in lowered for w in ("risk", "diabet", "chance", "likelihood", "likely")):
            return "risk"
        return "general"

    def _compose(self, ctx: GatheredContext, message: str) -> tuple[str, list[Citation]]:
        lowered = message.lower()
        intent = self._detect_intent(lowered)

        if intent == "demographics":
            answer = self._answer_demographics(lowered, ctx)
            if answer:
                return answer, []
        elif intent == "bmi":
            if ctx.bmi is not None:
                return f"Your BMI is approximately {ctx.bmi} ({bmi_category(ctx.bmi)}).", []
        elif intent == "specific_lab":
            answer = self._answer_specific_lab(lowered, ctx)
            if answer:
                return answer, []
        elif intent == "vitals":
            answer = self._answer_vitals(lowered, ctx)
            if answer:
                return answer, []
        elif intent == "risk":
            if ctx.risk is not None:
                return self._risk_sentence(ctx.risk), []
        elif intent == "explain":
            return self._answer_explain(message, lowered, ctx)

        # Generic question, or a targeted answer we couldn't build: full summary.
        return self._full_summary(ctx)

    def _answer_demographics(self, lowered: str, ctx: GatheredContext) -> str | None:
        p = ctx.patient
        bits: list[str] = []
        if _DEMO_PATTERNS["age"].search(lowered) and p.age is not None:
            bits.append(f"You are {p.age} years old.")
        if _DEMO_PATTERNS["sex"].search(lowered):
            sex = getattr(p.sex, "value", p.sex)
            if sex and sex != "unknown":
                bits.append(f"Your recorded sex is {sex}.")
        if _DEMO_PATTERNS["height"].search(lowered) and p.height_cm:
            bits.append(f"Your recorded height is {p.height_cm} cm.")
        if _DEMO_PATTERNS["weight"].search(lowered) and p.weight_kg:
            bits.append(f"Your recorded weight is {p.weight_kg} kg.")
        return " ".join(bits) if bits else None

    def _answer_specific_lab(self, lowered: str, ctx: GatheredContext) -> str | None:
        if not ctx.labs:
            return None
        fragments = {frag for kw, frag in _LAB_KEYWORDS.items() if kw in lowered}
        if not fragments:
            return None
        matched = [
            lab for lab in ctx.labs
            if any(frag in lab.test_name.lower() for frag in fragments)
        ]
        if not matched:
            return None
        return " ".join(
            f"Your {lab.test_name} is {lab.value}{lab.unit or ''}, {_range_phrase(lab)}."
            for lab in matched
        )

    def _answer_vitals(self, lowered: str, ctx: GatheredContext) -> str | None:
        if not ctx.vitals:
            return None
        v = ctx.vitals[-1]
        if ("blood pressure" in lowered or "bp" in lowered) and v.systolic_bp and v.diastolic_bp:
            return f"Your most recent blood pressure is {v.systolic_bp}/{v.diastolic_bp} mmHg."
        if any(w in lowered for w in ("heart rate", "pulse", "bpm")) and v.heart_rate:
            return f"Your most recent heart rate is {v.heart_rate} bpm."
        if "sleep" in lowered and v.sleep_hours is not None:
            return f"You recently slept {v.sleep_hours} hours."
        if "steps" in lowered and v.steps is not None:
            return f"Your recent step count is {v.steps}."
        bits: list[str] = []
        if v.systolic_bp and v.diastolic_bp:
            bits.append(f"blood pressure {v.systolic_bp}/{v.diastolic_bp} mmHg")
        if v.heart_rate:
            bits.append(f"heart rate {v.heart_rate} bpm")
        return ("Your most recent vitals: " + ", ".join(bits) + ".") if bits else None

    @staticmethod
    def _risk_sentence(risk) -> str:
        drivers = ", ".join(c.feature for c in risk.contributions[:2])
        pct = round(risk.probability * 100)
        return (
            f"A baseline model estimates your type 2 diabetes risk as {risk.risk_level} "
            f"(about {pct}%), driven mainly by {drivers}. This is a statistical estimate "
            f"from an educational model, not a diagnosis."
        )

    def _answer_explain(
        self, message: str, lowered: str, ctx: GatheredContext
    ) -> tuple[str, list[Citation]]:
        parts: list[str] = []
        # Anchor the explanation in the user's own value when a metric is referenced.
        value = self._answer_specific_lab(lowered, ctx) or self._answer_vitals(lowered, ctx)
        if value:
            parts.append(value)

        citations: list[Citation] = []
        if ctx.knowledge_hits:
            citations = [_to_citation(h) for h in ctx.knowledge_hits]
            sources = ", ".join(sorted({c.source for c in citations}))
            best = _best_sentence(ctx.knowledge_hits[0].text, message, self.retriever.embedder)
            parts.append(f"From the knowledge base ({sources}): {best}")
        elif not parts:
            parts.append(
                "I couldn't find a relevant explanation in the knowledge base for that."
            )
        return " ".join(parts), citations

    def _full_summary(self, ctx: GatheredContext) -> tuple[str, list[Citation]]:
        parts: list[str] = []
        name = ctx.patient.name or f"patient {ctx.patient.id}"
        parts.append(f"Here is what your data shows, {name}:")

        if ctx.labs:
            abnormal = [lab for lab in ctx.labs if lab.flag != "normal"]
            if abnormal:
                summarized = ", ".join(
                    f"{lab.test_name} {lab.value}{lab.unit or ''} ({lab.flag})" for lab in abnormal
                )
                parts.append(f"Labs outside the typical range: {summarized}.")
            else:
                parts.append("Your recorded labs are within typical reference ranges.")

        if ctx.vitals:
            v = ctx.vitals[-1]
            vital_bits = []
            if v.systolic_bp and v.diastolic_bp:
                vital_bits.append(f"blood pressure {v.systolic_bp}/{v.diastolic_bp} mmHg")
            if v.heart_rate:
                vital_bits.append(f"heart rate {v.heart_rate} bpm")
            if v.sleep_hours is not None:
                vital_bits.append(f"sleep {v.sleep_hours} h")
            if vital_bits:
                parts.append("Recent vitals: " + ", ".join(vital_bits) + ".")

        if ctx.bmi is not None:
            parts.append(f"Your BMI is approximately {ctx.bmi} ({bmi_category(ctx.bmi)}).")

        if ctx.risk is not None:
            parts.append(self._risk_sentence(ctx.risk))

        if ctx.patient_hits:
            parts.append(f"Most relevant to your question: {_excerpt(ctx.patient_hits[0].text)}")

        citations: list[Citation] = []
        if ctx.knowledge_hits:
            citations = [_to_citation(h) for h in ctx.knowledge_hits]
            sources = ", ".join(sorted({c.source for c in citations}))
            parts.append(f"From the knowledge base ({sources}): {_excerpt(ctx.knowledge_hits[0].text)}")

        return " ".join(parts), citations

    def _context_block(self, ctx: GatheredContext) -> str:
        """A compact, factual summary of gathered data for an LLM prompt."""
        lines: list[str] = []
        p = ctx.patient
        sex = getattr(p.sex, "value", p.sex) or "unknown"
        lines.append(
            f"Patient: name={p.name or 'unknown'}, sex={sex}, "
            f"age={p.age}, height_cm={p.height_cm}, weight_kg={p.weight_kg}"
        )
        if ctx.labs:
            lines.append("Labs:")
            for lab in ctx.labs:
                lines.append(
                    f"  - {lab.test_name}: {lab.value}{lab.unit or ''} ({lab.flag})"
                )
        if ctx.vitals:
            v = ctx.vitals[-1]
            lines.append(
                f"Latest vitals: bp={v.systolic_bp}/{v.diastolic_bp} mmHg, hr={v.heart_rate}, "
                f"sleep_hours={v.sleep_hours}"
            )
        if ctx.bmi is not None:
            lines.append(f"BMI: {ctx.bmi} ({bmi_category(ctx.bmi)})")
        if ctx.risk is not None:
            drivers = ", ".join(c.feature for c in ctx.risk.contributions[:3])
            lines.append(
                f"Model diabetes-risk estimate: {ctx.risk.risk_level} "
                f"(p={ctx.risk.probability}); top drivers: {drivers}"
            )
        if ctx.patient_hits:
            lines.append("Most relevant patient facts (semantic match):")
            for h in ctx.patient_hits:
                lines.append(f"  - [{h.source}] {_excerpt(h.text)}")
        if ctx.knowledge_hits:
            lines.append("Knowledge sources (cite these):")
            for h in ctx.knowledge_hits:
                lines.append(f"  - [{h.source}] {_excerpt(h.text)}")
        return "\n".join(lines)

    def chat(self, patient_id: int, message: str) -> AgentResponse:
        ctx = self._gather(patient_id, message)
        answer, citations = self._compose(ctx, message)
        guarded = apply_guardrails(answer, has_citations=bool(citations))
        return AgentResponse(
            patient_id=patient_id,
            answer=guarded.text,
            citations=citations,
            tool_calls=ctx.tool_calls,
            guardrail_notes=guarded.notes,
        )


class OpenAIAgent(RuleBasedAgent):
    """Uses the same tools/grounding as the rule-based agent, but GPT writes the answer.

    Falls back to the rule-based composition if the API call fails for any reason.
    """

    def __init__(self, db: Session, retriever: Retriever, *, api_key: str, model: str) -> None:
        super().__init__(db=db, retriever=retriever)
        from openai import OpenAI

        self.model = model
        # Fail fast (one retry) so a quota/auth error degrades to local quickly.
        self._client = OpenAI(api_key=api_key, max_retries=1)

    def chat(self, patient_id: int, message: str) -> AgentResponse:
        ctx = self._gather(patient_id, message)
        citations = [_to_citation(h) for h in ctx.knowledge_hits]

        try:
            user_prompt = (
                f"Patient data and sources:\n{self._context_block(ctx)}\n\n"
                f"User question: {message}\n\n"
                "Answer using only the data and sources above. Cite knowledge sources by "
                "their bracketed filename. Keep it concise."
            )
            completion = self._client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            answer = completion.choices[0].message.content or ""
            ctx.tool_calls.append(
                ToolCall("llm_generate", {"model": self.model}, "openai chat completion")
            )
        except Exception as exc:  # graceful fallback to the offline composition
            from backend.llm import get_circuit, is_quota_or_auth_error

            if is_quota_or_auth_error(exc):
                # Quota/auth/rate problem: stop calling OpenAI for a while.
                get_circuit().trip(str(exc))
            logger.warning("OpenAI call failed, falling back to rule-based agent: %s", exc)
            answer, citations = self._compose(ctx, message)

        guarded = apply_guardrails(answer, has_citations=bool(citations))
        return AgentResponse(
            patient_id=patient_id,
            answer=guarded.text,
            citations=citations,
            tool_calls=ctx.tool_calls,
            guardrail_notes=guarded.notes,
        )


def _to_citation(hit: SearchHit) -> Citation:
    return Citation(
        source=hit.source,
        chunk_index=hit.chunk_index,
        excerpt=_excerpt(hit.text),
        score=round(hit.score, 4),
    )


def _excerpt(text: str, max_chars: int = 240) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "\u2026"


def _range_phrase(lab) -> str:
    if lab.flag == "high":
        return "above the typical reference range"
    if lab.flag == "low":
        return "below the typical reference range"
    return "within the typical reference range"


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _best_sentence(text: str, query: str, embedder) -> str:
    """Return the single sentence in ``text`` most relevant to ``query``.

    Keeps knowledge excerpts crisp (the responsive sentence, not a 120-word chunk).
    Uses the active embedder for similarity; falls back to the whole excerpt on any
    issue so a phrasing detail never breaks a response.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return _excerpt(text)
    try:
        vectors = embedder.embed([*sentences, query])
        query_vec = vectors[-1]
        scored = max(
            range(len(sentences)),
            key=lambda i: sum(a * b for a, b in zip(vectors[i], query_vec)),
        )
        return _excerpt(sentences[scored])
    except Exception:  # noqa: BLE001 - never let excerpt selection fail a response
        return _excerpt(text)


def get_agent(db: Session, retriever: Retriever) -> RuleBasedAgent:
    """Return the configured agent.

    Uses ``OpenAIAgent`` when a key is set and the ``openai`` package is importable;
    otherwise falls back to the offline rule-based agent.
    """
    from backend.config import get_settings
    from backend.llm import get_circuit

    settings = get_settings()
    # Skip OpenAI entirely while the circuit is tripped (recent quota/auth failure).
    if settings.openai_api_key and get_circuit().is_available():
        try:
            return OpenAIAgent(
                db=db,
                retriever=retriever,
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
        except Exception as exc:  # noqa: BLE001 - any setup failure -> safe fallback
            logger.warning("Falling back to rule-based agent: %s", exc)
    return RuleBasedAgent(db=db, retriever=retriever)
