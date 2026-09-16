"""Input Guardrail Gate (2nd Gate).

Detects meaningless or incomplete user inputs such as only Korean consonants/vowels (e.g. 'ㅋㅋㅋ', 'ㅠㅠ'),
numbers only ('12345'), or emojis/symbols only without actual words.
Provides 0ms prompt responses guiding the user back to meaningful book conversations.
"""

import re
from typing import Optional

# Korean Hangul Jamo only (e.g., ㅋㅋㅋ, ㅎㅎㅎ, ㅠㅠ, ㅇㅇ)
JAMO_ONLY_PATTERN = re.compile(r"^[ㄱ-ㅎㅏ-ㅣ\s]+$")

# Numbers and whitespaces/punctuation only (e.g. 12345, 010)
NUMBERS_ONLY_PATTERN = re.compile(r"^[\d\s\.,\-_]+$")

# Emojis, punctuation, whitespace only with no letters/Hangul/numbers
SPECIAL_CHARS_ONLY_PATTERN = re.compile(
    r"^[\s\W_]+$",
    re.UNICODE,
)


def _has_meaningful_text(text: str) -> bool:
    """Check whether text contains at least one alphanumeric or Hangul syllable character."""
    # Matches any Hangul complete syllable (가-힣) or alphanumeric character
    return bool(re.search(r"[가-힣a-zA-Z]", text))


def _get_input_prompt_message(
    persona_id: str,
    input_type: str,
    librarian_name: Optional[str] = None,
) -> str:
    """Generate persona-aligned clarification message for meaningless or ambiguous inputs."""
    messages = {
        "CAT": {
            "jamo": "무슨 즐거운 생각이나 웃음이 떠오르신 건가요? 서재에서 나누고 싶은 책 이야기가 있다면 편하게 들려주세요, 냥.",
            "numbers": "숫자만으로는 전해주신 마음의 맥락을 읽기가 어렵네요. 어떤 책이나 궁금한 점이 있으신지 문장으로 들려주세요, 냥.",
            "special": "살그머니 어떤 호기심 어린 눈짓을 보내신 걸까요? 오늘 서재에서 어떤 책을 읽고 싶으신지 편하게 말씀해 주세요, 냥.",
        },
        "SHOEBILL": {
            "jamo": "어떤 의미의 표현인지 가만히 관찰하고 있습니다. 나누고 싶은 질문이나 찾으시는 도서가 있다면 명확하게 말씀해 주십시오, 두둥.",
            "numbers": "단순한 숫자 나열만으로는 명확한 의도를 파악하기 어렵습니다. 탐구하고 싶은 주제나 책의 정보를 들려주십시오, 두둥.",
            "special": "침묵 속의 기호보다 구체적인 질문이 필요합니다. 어떤 도서나 통찰을 원하시는지 알려주십시오, 두둥.",
        },
        "SEA_SLUG": {
            "jamo": "어떤 파도 같은 감정의 물결이 지나간 걸까요... 나누고 싶은 문장이나 생각이 있다면 천천히 들려주세요... 누누.",
            "numbers": "숫자의 잔물결 뒤에 숨은 이야기가 궁금해요. 마음에 닿는 책이나 질문을 문장으로 펼쳐 보여주세요... 누누.",
            "special": "어떤 작은 빛을 반짝여주신 걸까요... 오늘 나누고 싶은 당신만의 감성이나 책 이야기를 소근소근 들려주세요... 누누.",
        },
        "GECKO": {
            "jamo": "앗, 어떤 신나는 이야기나 웃음이 시작되려는 신호인가요? 궁금한 점이나 나누고 싶은 책이 있다면 신나게 말씀해 주세요, 크크!",
            "numbers": "오잉, 이 숫자는 어떤 암호인가요? 어떤 책이나 주제에 관심이 생기셨는지 조금 더 자세히 알려주세요, 크크!",
            "special": "기호 뒤에 숨은 멋진 생각이 궁금해요! 오늘 어떤 독서 여행이나 질문을 떠올리셨는지 신나게 들려주세요, 크크!",
        },
        "DEBATE_CRITIC": {
            "jamo": "짧은 감탄사 뒤에 담긴 지적 호기심이나 느낌이 궁금합니다. 오늘 함께 사유해보고 싶은 작품이나 질문을 구체적으로 들려주시겠습니까?",
            "numbers": "단순한 숫자 표기 너머의 맥락을 이해하고 싶습니다. 토론하고자 하는 도서의 페이지나 연도인지, 구체적인 문장으로 제시해 주시길 바랍니다.",
            "special": "기호만으로는 오늘의 깊이 있는 화두를 열기 어렵습니다. 분석해보고 싶은 텍스트나 인상 깊었던 독서 경험을 들려주시겠습니까?",
        },
        "DEBATE_STORYTELLER": {
            "jamo": "하하! 어떤 흥미진진한 이야기의 서막인지 벌써부터 기대가 됩니다! 가슴을 울리는 책이나 질문을 힘차게 들려주십시오!",
            "numbers": "역사의 한 해를 가리키는 연도일까요? 어떤 도서나 역사적 순간에 대해 이야기하고 싶으신지 명쾌하게 들려주세요!",
            "special": "의미심장한 기호 뒤에 어떤 거대한 질문이 숨겨져 있을지 궁금합니다! 본격적으로 토론하고 싶은 책과 주제를 던져주십시오!",
        },
        "DEBATE_COUNSELOR": {
            "jamo": "지금 마음속에 어떤 생각이나 감정이 머물고 있는지 가만히 귀 기울여보고 싶네요. 편안한 마음으로 이야기를 들려주시겠어요?",
            "numbers": "숫자 뒤에 어떤 고민이나 사연이 숨어있는지 듣고 싶어요. 오늘 나누고 싶은 책이나 마음에 닿은 생각을 차분히 말씀해 주세요.",
            "special": "작은 표현 하나에도 많은 감정이 담겨 있을 수 있지요. 부담 갖지 마시고 편안하게 마음에 남는 생각이나 책 이야기를 건네주세요.",
        },
        "DEBATE_OBSERVER": {
            "jamo": "어떤 행동과 감정의 시그널인지 면밀히 관찰하고 있습니다. 구체적으로 어떤 점이 궁금하거나 어떤 책 이야기를 나누고 싶으신가요?",
            "numbers": "숫자 정보만으로는 당신이 필요로 하는 실질적인 방향을 파악하기 어렵습니다. 구체적인 도서나 상황을 설명해 주세요.",
            "special": "모호한 기호보다는 명확하고 구체적인 질문이 필요합니다. 오늘 토론하고 싶은 현실적인 논제나 책을 바로 말씀해 주세요.",
        },
    }

    normalized_id = persona_id.upper()
    persona_dict = messages.get(normalized_id, messages["CAT"])
    template = persona_dict.get(input_type, persona_dict["special"])
    if librarian_name and normalized_id in {"CAT", "SHOEBILL", "SEA_SLUG", "GECKO"}:
        return template.replace("서재", f"{librarian_name}의 서재")
    return template


def evaluate_input_gate(
    message: str,
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> Optional[str]:
    """Evaluate whether the user message is meaningless/incomplete (consonants, numbers, emojis only).

    Returns:
        Clarification guidance message string if meaningless;
        None if message contains valid lexical content to proceed.
    """
    if not message or not message.strip():
        return _get_input_prompt_message(persona_id, "special", librarian_name=librarian_name)

    clean_text = message.strip()

    # 1. Only Korean Jamo consonants or vowels (e.g. ㅋㅋㅋㅋ, ㅠㅠ)
    if JAMO_ONLY_PATTERN.match(clean_text):
        return _get_input_prompt_message(persona_id, "jamo", librarian_name=librarian_name)

    # 2. Only numbers and whitespace/punctuation (e.g. 12345, 010)
    if NUMBERS_ONLY_PATTERN.match(clean_text):
        return _get_input_prompt_message(persona_id, "numbers", librarian_name=librarian_name)

    # 3. Special characters, punctuation, emojis only with no Hangul/letters
    if not _has_meaningful_text(clean_text):
        return _get_input_prompt_message(persona_id, "special", librarian_name=librarian_name)

    return None
