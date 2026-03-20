from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re
from app.models.request_models import ChatRequest
from app.models.response_models import ChatResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.auth_service import auth_service
from app.core.rate_limiter import rate_limiter, get_client_ip
from app.db.persistence import update_user_preferred_mode, add_chat_message

router = APIRouter()
security = HTTPBearer(auto_error=False)


AEROSPACE_KEYWORDS = {
    "aero", "aerodynamics", "aeronautical", "aerospace", "air", "aircraft", "airfoil",
    "airspeed", "altitude", "avionics", "blade", "boeing", "cabin", "cockpit", "compressor",
    "drag", "engine", "faa", "fuselage", "gear", "helicopter", "hydraulic", "icao", "jet",
    "landing", "lift", "mach", "missile", "nacelle", "propeller", "propulsion", "radar",
    "runway", "sae", "stability", "stall", "thrust", "turbine", "uav", "wing"
}

OUT_OF_CONTEXT_REPLY = (
    "I’d love to help, but I’m currently limited to answering questions related to aerospace and aircraft. If you have anything in that area, feel free to ask—I’m here for you!"
)

GREETING_WORDS = {
    "hi", "hello", "hey", "hiya", "greetings", "hola", "yo", "sup"
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
    return any(keyword in normalized for keyword in AEROSPACE_KEYWORDS)


def is_greeting_message(question: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", " ", question.lower())
    normalized = " ".join(normalized.split()).strip()
    if not normalized:
        return False

    if normalized in GREETING_PHRASES:
        return True

    words = [word for word in normalized.split() if word]
    if not words or len(words) > 4:
        return False

    return all(word in GREETING_WORDS for word in words)


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

    if credentials is not None:
        token_data = auth_service.verify_token(credentials.credentials)

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

    if request.mode == "general_chat" and is_greeting_message(request.question):
        answer = GREETING_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "user", request.mode, request.question)
            add_chat_message(token_data.email, "assistant", request.mode, answer)

        return ChatResponse(answer=answer)

    if request.mode == "general_chat" and is_farewell_message(request.question):
        answer = FAREWELL_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "user", request.mode, request.question)
            add_chat_message(token_data.email, "assistant", request.mode, answer)

        return ChatResponse(answer=answer)

    if request.mode == "general_chat" and not is_aerospace_related(request.question):
        answer = OUT_OF_CONTEXT_REPLY

        if token_data and token_data.email:
            update_user_preferred_mode(token_data.email, request.mode)
            add_chat_message(token_data.email, "user", request.mode, request.question)
            add_chat_message(token_data.email, "assistant", request.mode, answer)

        return ChatResponse(answer=answer)

    retrieved_context = rag_service.retrieve_context(request.question)

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
        add_chat_message(token_data.email, "user", request.mode, request.question)
        add_chat_message(token_data.email, "assistant", request.mode, answer)

    return ChatResponse(answer=answer)
