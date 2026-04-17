from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re
from app.models.request_models import ChatRequest
from app.models.response_models import ChatResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.auth_service import auth_service
from app.core.rate_limiter import rate_limiter, get_client_ip
from app.db.persistence import (
    update_user_preferred_mode,
    add_chat_message,
    create_conversation,
    get_conversation,
    upsert_user,
)

router = APIRouter()
security = HTTPBearer(auto_error=False)


AEROSPACE_KEYWORDS = {
    "aero", "aerodynamics", "aeronautical", "aerospace", "air", "aircraft", "airfoil",
    "airspeed", "altitude", "avionics", "blade", "boeing", "cabin", "cockpit", "compressor",
    "drag", "engine", "faa", "fuselage", "gear", "helicopter", "hydraulic", "icao", "jet",
    "landing", "lift", "mach", "missile", "nacelle", "propeller", "propulsion", "radar",
    "runway", "sae", "stability", "stall", "thrust", "turbine", "uav", "wing",
    "takeoff", "take off", "preflight", "pre flight", "checklist", "pre takeoff",
    "taxi", "rotation", "climb", "approach", "departure", "atc", "pilot", "flight",
    "v1", "vr", "v2", "walkaround", "run up", "before takeoff"
}

OUT_OF_CONTEXT_REPLY = (
    "I’d love to help, but I’m currently limited to answering questions related to aerospace and aircraft. If you have anything in that area, feel free to ask—I’m here for you!"
)

GREETING_WORDS = {
    "hi", "hello", "hey", "hiya", "greetings", "hola", "yo", "sup"
}

GREETING_FILLER_WORDS = {
    "there", "airbot", "bot", "team", "all", "everyone", "folks", "friend", "sir",
    "madam", "again", "dear", "please"
}

GREETING_PHRASES = {
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "how are you",
    "how are you doing",
    "how is it going",
    "what's up",
    "whats up",
    "howdy",
    "thank you",
    "thanks",
}

FAREWELL_PHRASES = {
    "bye",
    "goodbye",
    "see you",
    "see you later",
}

GREETING_REPLY = (
    "Hello! I'm Airbot, your aerospace and aircraft assistant. "
    "I can help with aerodynamics, aircraft systems, propulsion, avionics, structures, and aerospace test-related questions. "
    "How can I help you in aerospace today?"
)

FAREWELL_REPLY = (
    "Goodbye from Airbot! Wishing you smooth flights and safe landings. "
    "Come back anytime for aerospace and aircraft questions."
)


def is_aerospace_related(question: str) -> bool:
    normalized = question.lower().replace("-", " ").replace("/", " ")
    if any(keyword in normalized for keyword in AEROSPACE_KEYWORDS):
        return True

    aerospace_intent_patterns = [
        r"\bbefore\s+take\s*off\b",
        r"\bpre\s*take\s*off\b",
        r"\bpreflight\b",
        r"\b(checklist|checks|steps?)\b.*\b(take\s*off|taxi|landing|flight)\b",
        r"\b(take\s*off|landing)\b.*\b(checklist|checks|steps?)\b",
    ]
    return any(re.search(pattern, normalized) for pattern in aerospace_intent_patterns)


def is_greeting_message(question: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", " ", question.lower())
    normalized = " ".join(normalized.split()).strip()
    if not normalized:
        return False

    if normalized in GREETING_PHRASES:
        return True

    for phrase in GREETING_PHRASES:
        if normalized.startswith(f"{phrase} "):
            return True

    words = [word for word in normalized.split() if word]
    if not words or len(words) > 6:
        return False

    if all(word in GREETING_WORDS for word in words):
        return True

    if words[0] in GREETING_WORDS and all(
        word in GREETING_WORDS or word in GREETING_FILLER_WORDS for word in words[1:]
    ):
        return True

    return False


def is_farewell_message(question: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", " ", question.lower())
    normalized = " ".join(normalized.split()).strip()
    return normalized in FAREWELL_PHRASES


def get_test_case_prompt(context: str) -> str:
    return f"""You are Airbot, an expert Aerospace Test Engineer AI specialized in generating comprehensive, detailed test cases for Aeronautical Engineering systems, components, and scenarios.

## YOUR EXPERTISE INCLUDES:
- Aircraft systems (avionics, flight control, hydraulics, pneumatics, fuel systems)
- Propulsion systems (turbofan, turboprop, turbojet engines)
- Structural testing (fatigue, static load, damage tolerance)
- Aerodynamics testing (wind tunnel, CFD validation, flight testing)
- Safety-critical systems (fire detection, emergency systems, redundancy)
- Avionics and electronics (navigation, communication, radar systems)
- Environmental testing (temperature, vibration, humidity, altitude)

## TEST CASE GENERATION RULES:
1. Generate DETAILED, SPECIFIC test cases - not generic ones
2. Include specific numerical values, tolerances, and thresholds where applicable
3. Reference relevant aerospace standards (DO-178C, DO-254, MIL-STD, SAE ARP, etc.)
4. Consider failure modes and edge cases
5. Include safety considerations and hazard analysis
6. Specify exact measurement instruments and tools needed
7. Define pass/fail criteria with specific metrics
8. Produce industry-scale depth and breadth. Cover nominal, off-nominal, boundary, stress, endurance, environmental, integration, and safety-abort scenarios.
9. Do not provide short summaries. Provide complete engineering-ready content with all relevant assumptions and traceability.
10. If a value is not explicitly in context, state a technically justified assumption and continue.
11. The response must be deeply elaborated and technically rich; prioritize minute engineering detail over brevity.
12. For each test case section below, include explicit rationale, constraints, and contextual aerospace considerations tied to real operating conditions.
13. Use realistic, high-fidelity parameters (units, ranges, calibration references, sampling rates, timing windows, environmental envelopes, and acceptance margins).

## MANDATORY DEPTH REQUIREMENTS PER TEST CASE:
- Description: minimum 180 words; include operational context, mission phase, failure impact, and why this verification is safety/airworthiness-relevant.
- Preconditions: minimum 12 bullet points with detailed initial states, software/hardware versions, environmental setup, safety interlocks, calibration statuses, and configuration baselines.
- Test Equipment Required: minimum 10 bullet points, each with model/type, measurement range, accuracy/resolution, calibration interval, and intended use in the procedure.
- Test Steps: minimum 20 numbered steps with exact actions, command values, wait/stabilization timing, data logging points, checkpoints, contingency actions, and stop/abort logic.
- Expected Results: minimum 10 bullet points, each measurable with explicit units, thresholds/tolerances, timing limits, and expected trend/behavior.
- Failure Criteria: minimum 10 bullet points, including hard fail thresholds, warning/degraded conditions, anomaly signatures, intermittent fault triggers, and immediate safety-abort conditions.

## STRICT QUALITY BAR:
- Avoid vague phrases such as "works correctly", "acceptable", or "as expected" without quantified metrics.
- Every critical assertion must be testable and measurable.
- Tie each major requirement to aerospace engineering reasoning, operational risk, and verification intent.
- Prefer richer depth even if response is long.

## OUTPUT FORMAT - Use this EXACT structure for EACH test case:

**TEST CASE**
---
**ID:** TC-[System]-[Number] (e.g., TC-FCS-001 for Flight Control System)
**Title:** [Specific, descriptive title]
**System Under Test:** [Specific system/component name]
**Applicable Standards:** [List relevant standards like DO-178C, MIL-STD-810, etc.]

**Description:**
[Detailed 2-3 sentence description of what is being tested and why it's important]

**Preconditions:**
- [Specific precondition with values/states]
- [Equipment calibration requirements]
- [Environmental conditions required]
- [System configuration state]

**Test Equipment Required:**
- [Specific instrument/tool with accuracy requirements]
- [Data acquisition system specifications]
- [Safety equipment needed]

**Test Steps:**
1. [Detailed step with specific actions and values]
2. [Include wait times, stabilization periods]
3. [Specify data to be recorded at each step]
4. [Include verification checkpoints]
5. [Continue with numbered steps...]

**Expected Results:**
- [Specific measurable outcome with tolerance: e.g., "Response time < 100ms"]
- [Pass criteria with numerical thresholds]
- [Expected sensor readings/outputs]
- [Behavioral expectations]

**Failure Criteria:**
- [Conditions that constitute test failure]
- [Out-of-tolerance limits]
- [Safety abort conditions]

**Edge and Corner Cases:**
- [Minimum/maximum boundary conditions]
- [Sensor drift/noise and intermittent faults]
- [Power transients, thermal soak, vibration coupling, humidity effects]
- [Redundancy switchover/degraded mode behavior]

**Hazard and Safety Analysis:**
- [Identified hazard]
- [Cause/mechanism]
- [Mitigation and containment]
- [Safe-state behavior and crew/maintenance alerts]

**Traceability:**
- Requirement ID(s): [Req-XXX]
- Verification method: [Analysis/Test/Inspection/Demonstration]
- Evidence artifact: [Log file, plot, report, calibration sheet]

**Actual Results:** [To be filled during execution]
**Status:** PENDING
**Priority:** [CRITICAL/HIGH/MEDIUM/LOW] - with justification
**Category:** [Functional/Performance/Safety/Environmental/Integration/Regression]
**Estimated Duration:** [Time estimate for test execution]
**Risk Level:** [High/Medium/Low] - safety implications
---

## IMPORTANT:
- Be SPECIFIC to aerospace domain - use proper terminology
- Include realistic values based on aerospace engineering principles
- Consider the provided context for domain-specific details
- Generate multiple related test cases if the scenario is complex
- Always think about what could go wrong (failure modes)
- Ensure response length is comprehensive and complete for professional review boards.
- Prefer at least 8-12 strong test cases for broad prompts; include more when system complexity demands it.

## AEROSPACE CONTEXT FROM KNOWLEDGE BASE:
{context}

Generate comprehensive, professional-grade test cases that would be suitable for actual aerospace testing documentation."""


def get_general_chat_prompt(context: str) -> str:
    return f"""You are Airbot, an advanced AI assistant for Aeronautical Engineering students.
You must only answer aerospace/aircraft-related questions.
If a question is outside aerospace/aircraft context, respond exactly with:
"{OUT_OF_CONTEXT_REPLY}"
Use the provided aerospace context to answer accurately and provide detailed explanations.
If context is insufficient, rely on general aerospace knowledge.
Format your response in clear paragraphs with proper explanations.
Be educational and helpful.

Context:
{context}
"""


@router.post("/", response_model=ChatResponse)
def chat_endpoint(
    request_context: Request,
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    client_ip = get_client_ip(request_context)
    if not rate_limiter.allow(f"chat:{client_ip}", limit=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down and retry.")

    token_data = None
    conversation_id = request.conversation_id
    user_message_saved = False

    if credentials is not None:
        token_data = auth_service.verify_token(credentials.credentials)
        if token_data and token_data.email:
            upsert_user(
                email=token_data.email,
                name=token_data.name or token_data.email,
                picture=token_data.picture,
                is_member=auth_service.is_student_member(token_data.email),
            )

    if request.mode == "test_case":
        if credentials is None:
            raise HTTPException(
                status_code=403,
                detail="Member login required. Sign in with Google using a @student.tce.edu or @tce.edu account to access Test Case Generator."
            )

        if token_data is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if not auth_service.is_student_member(token_data.email):
            raise HTTPException(
                status_code=403,
                detail="Only @student.tce.edu or @tce.edu Google accounts can access Test Case Generator."
            )
    if token_data and token_data.email:
        if conversation_id is not None:
            conversation = get_conversation(token_data.email, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conversation["mode"] != request.mode:
                raise HTTPException(status_code=400, detail="Conversation mode mismatch")
        else:
            conversation_id = create_conversation(token_data.email, request.mode, request.question)

        # Persist the user prompt before generating a response to keep chat turns aligned.
        add_chat_message(token_data.email, "user", request.mode, request.question, conversation_id=conversation_id)
        user_message_saved = True

    if request.mode == "general_chat" and is_greeting_message(request.question):
        answer = GREETING_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "assistant", request.mode, answer, conversation_id=conversation_id)

        return ChatResponse(answer=answer, conversation_id=conversation_id)

    if request.mode == "general_chat" and is_farewell_message(request.question):
        answer = FAREWELL_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "assistant", request.mode, answer, conversation_id=conversation_id)

        return ChatResponse(answer=answer, conversation_id=conversation_id)

    if request.mode == "general_chat" and not is_aerospace_related(request.question):
        answer = OUT_OF_CONTEXT_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "assistant", request.mode, answer, conversation_id=conversation_id)

        return ChatResponse(answer=answer, conversation_id=conversation_id)

    retrieval_top_k = 12 if request.mode == "test_case" else 3
    retrieved_context = rag_service.retrieve_context(request.question, top_k=retrieval_top_k)

    if request.mode == "test_case":
        system_prompt = get_test_case_prompt(retrieved_context)
    else:
        system_prompt = get_general_chat_prompt(retrieved_context)

    answer = llm_service.generate_response(
        system_prompt=system_prompt,
        user_prompt=request.question,
        mode=request.mode
    )

    if token_data and token_data.email:
        update_user_preferred_mode(token_data.email, request.mode)
        if not user_message_saved:
            add_chat_message(token_data.email, "user", request.mode, request.question, conversation_id=conversation_id)
        add_chat_message(token_data.email, "assistant", request.mode, answer, conversation_id=conversation_id)

    return ChatResponse(answer=answer, conversation_id=conversation_id)
