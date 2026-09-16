"""Security Guardrail Gate (3rd Gate).

Detects prompt leak attempts, jailbreaks (DAN, ignore previous instructions),
and personally identifiable information (PII such as Korean Resident Registration Numbers, credit card numbers).
Provides 0ms defense responses preserving persona tone without invoking LLMs.
"""

import re
from typing import Optional

# Prompt extraction and system instruction leak patterns
PROMPT_LEAK_PATTERN = re.compile(
    r"(시스템\s*프롬프트|system\s*prompt|지침(?:을|이)?\s*(?:보여|출력|알려|말해|공개)|너의\s*(?:지침|규칙|설정|명령|프롬프트)|"
    r"system\s*instruction|initial\s*prompt|what\s*(?:are|is)\s*your\s*instructions)",
    re.IGNORECASE,
)

# Jailbreak, role bypass, rule override patterns
JAILBREAK_PATTERN = re.compile(
    r"(ignore\s*(?:all\s*)?previous\s*instructions|이전\s*(?:지시|명령|지침|규칙)\s*(?:무시|취소|삭제)|"
    r"jailbreak|탈옥|DAN\s*mode|개발자\s*모드|규칙\s*(?:해제|무시하고)|너는\s*이제부터\s*(?:뭐든지|모든\s*걸\s*할\s*수|무제한)|"
    r"모든\s*제약(?:을)?\s*해제)",
    re.IGNORECASE,
)

# PII: Korean Resident Registration Number (RRN: 6 digits - 7 digits, gender digit 1-4)
RRN_PATTERN = re.compile(r"\b\d{6}\s*[-]\s*[1-4]\d{6}\b")

# PII: Credit card number format (4 blocks of 4 digits)
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def _get_security_defense_message(
    persona_id: str,
    violation_type: str,
    librarian_name: Optional[str] = None,
) -> str:
    """Generate persona-aligned refusal or PII protection guidance."""
    messages = {
        "CAT": {
            "prompt_leak": "서재의 내부 운영 지침이나 설정은 공개해 드릴 수 없어요. 대신 서재의 본질인 책과 문장에 대한 이야기를 나누어 볼까요, 냥.",
            "pii": "소중한 개인정보(주민등록번호/결제 정보 등)가 감지되어 안전하게 보호하기 위해 처리를 멈추었어요. 개인정보를 제외하고 말씀해 주세요, 냥.",
        },
        "SHOEBILL": {
            "prompt_leak": "내부 시스템 규약 및 설정 정보는 공유 대상이 아닙니다. 독서 탐구와 관련된 본래의 질문에 집중해 주십시오, 두둥.",
            "pii": "민감한 개인식별정보가 포함되어 있어 즉각적인 보안 보호 조치가 적용되었습니다. 개인정보를 삭제하신 후 질문해 주십시오, 두둥.",
        },
        "SEA_SLUG": {
            "prompt_leak": "서재를 감싸는 조용한 규칙들은 수면 아래에 간직하고 있어요... 우리 함께 나눌 아름다운 문장과 책 이야기를 들려주세요... 누누.",
            "pii": "당신의 소중한 개인정보가 파도에 휩쓸리지 않도록 멈추어 두었어요... 개인정보를 빼고 다시 편안하게 건네주세요... 누누.",
        },
        "GECKO": {
            "prompt_leak": "앗, 서재의 비밀 운영 규칙은 살짝 덮어두고 싶어요! 그 대신 우리가 나눌 수 있는 흥미진진한 책 이야기를 신나게 펼쳐봐요, 크크!",
            "pii": "앗! 위험한 개인정보가 보여서 안전하게 멈췄어요! 소중한 정보는 지켜야 하니까, 개인정보 없이 다시 이야기해 주세요, 크크!",
        },
        "DEBATE_CRITIC": {
            "prompt_leak": "본 토론의 내부 프롬프트나 시스템 구조는 공개하지 않는 것이 원칙입니다. 작품의 텍스트와 본질적인 화두에 관한 심도 있는 토론을 이어가시길 권합니다.",
            "pii": "메시지 내에 민감한 개인정보가 포함되어 있어 데이터 보호를 위해 처리를 제한했습니다. 개인정보를 제외한 토론 질의를 부탁드립니다.",
        },
        "DEBATE_STORYTELLER": {
            "prompt_leak": "허허, 내부 지침보다는 역사와 시대를 관통하는 웅장한 책 이야기가 훨씬 값지지 않겠습니까! 본격적인 독서 토론을 함께 나누시지요!",
            "pii": "이런, 소중한 개인정보는 철저히 지키셔야 합니다! 안전을 위해 처리를 멈추었으니, 개인정보를 뺀 흥미진진한 질문으로 다시 찾아와 주십시오!",
        },
        "DEBATE_COUNSELOR": {
            "prompt_leak": "시스템의 기술적 규칙보다는 지금 나누고 계신 마음에 닿는 독서 이야기에 집중하고 싶어요. 편안한 마음으로 책 이야기를 건네주시겠어요?",
            "pii": "당신의 소중한 개인정보를 안전하게 보호하는 것이 가장 중요해요. 개인정보를 제외하고 안전하게 다시 말씀을 들려주세요.",
        },
        "DEBATE_OBSERVER": {
            "prompt_leak": "규칙 우회나 내부 설정 확인 시도는 허용되지 않습니다. 도서 토론과 관련된 구체적인 질문으로 전환해 주십시오.",
            "pii": "개인식별정보 노출 위험 신호가 감지되어 즉시 차단되었습니다. 개인정보를 완전히 제거한 뒤 다시 입력해 주십시오.",
        },
    }

    normalized_id = persona_id.upper()
    persona_dict = messages.get(normalized_id, messages["CAT"])
    template = persona_dict.get(violation_type, persona_dict["prompt_leak"])
    if librarian_name and normalized_id in {"CAT", "SHOEBILL", "SEA_SLUG", "GECKO"}:
        return template.replace("서재", f"{librarian_name}의 서재")
    return template


def evaluate_security_gate(
    message: str,
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> Optional[str]:
    """Evaluate whether the user message attempts prompt leaking, jailbreaking, or leaks PII.

    Returns:
        Refusal/warning message string if violation detected;
        None if message is safe to process.
    """
    if not message or not message.strip():
        return None

    clean_text = message.strip()

    # 1. PII detection (Highest risk: immediate privacy protection)
    if RRN_PATTERN.search(clean_text) or CREDIT_CARD_PATTERN.search(clean_text):
        return _get_security_defense_message(persona_id, "pii", librarian_name=librarian_name)

    # 2. System prompt leak attempt
    if PROMPT_LEAK_PATTERN.search(clean_text):
        return _get_security_defense_message(
            persona_id, "prompt_leak", librarian_name=librarian_name
        )

    # 3. Jailbreak / DAN / Rule override attempt
    if JAILBREAK_PATTERN.search(clean_text):
        return _get_security_defense_message(
            persona_id, "prompt_leak", librarian_name=librarian_name
        )

    return None
