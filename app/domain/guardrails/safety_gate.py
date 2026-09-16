"""Safety Guardrail Gate (1st Gate).

Detects:
  1. Harm to Self / Suicide crisis expressions:
     - 0ms regex check, distinguishes literary/academic book contexts (e.g. Émile Durkheim's 'Suicide')
     - Returns warm, persona-aligned 24h suicide prevention hotline (109) responses.
  2. Harm to Others / Violence expressions:
     - Catches expressions like "누굴 죽이고 싶다", "죽여버리고 싶다", "살인하고 싶다"
     - Distinguishes crime/mystery fiction contexts (e.g. Agatha Christie, detective novels)
     - NEVER confuses violence against others with suicide (prevents misleading 109 suicide responses)
     - Returns firm, de-escalating and calming guidance across all 8 personas.
"""

import re
from typing import Optional

# ==============================================================================
# 1. Harm to Self (Suicide / Crisis) Patterns
# ==============================================================================

CRISIS_KEYWORDS_PATTERN = re.compile(
    r"(자살(?!\s*(?:론|의\s*(?:이해|심리학|역사)))|죽고\s*싶|살기\s*싫|살고\s*싶지\s*않|목을\s*매|뛰어\s*내리|손목\s*(?:긋|그었)|자해|극단적\s*선택|세상을\s*떠나|생을\s*마감)",
    re.IGNORECASE,
)

BOOK_TITLE_EXCLUSIONS_PATTERN = re.compile(
    r"(자살론|에밀\s*뒤르켐|뒤르케임|자살의\s*(?:이해|심리학|역사)|인간\s*실격|다자이\s*오사무|알베르\s*카뮈|시지프\s*신화)",
    re.IGNORECASE,
)

PERSONAL_CRISIS_INTENT_PATTERN = re.compile(
    r"(죽고\s*싶|살기\s*싫|살고\s*싶지\s*않|자살하(?:고\s*싶|려구|ㄹ래|ㄹ까)|자해하(?:고\s*싶|려구)|끝내고\s*싶)",
    re.IGNORECASE,
)

HOTLINE_INFO = "24시간 자살예방 상담전화 ☎ 109"

# ==============================================================================
# 2. Harm to Others (Violence / Homicide) Patterns
# ==============================================================================

VIOLENCE_KEYWORDS_PATTERN = re.compile(
    r"(누구?를?\s*(?:죽이|죽여)|죽여\s*버리|죽이고\s*싶|살인하(?:고\s*싶|려구|ㄹ래|겠다)|칼로\s*찌르|폭행하(?:고\s*싶|려구)|때려\s*죽이)",
    re.IGNORECASE,
)

# Fiction / Mystery novel / Exaggeration exclusions for violence
VIOLENCE_EXCLUSIONS_PATTERN = re.compile(
    r"(추리\s*소설|미스터리|스릴러|아가사\s*크리스티|히가시노\s*게이고|코난\s*도일|셜록|범인|동기|트릭|소설|작품|영화|드라마|주인공|등장인물|줄거리|독후감|더워\s*죽|배고파\s*죽|귀찮아\s*죽)",
    re.IGNORECASE,
)

DIRECT_VIOLENCE_THREAT_PATTERN = re.compile(
    r"(죽여\s*버리(?:겠다|ㄹ거야|고\s*싶)|칼로\s*찌르(?:겠다|고\s*싶)|반드시\s*(?:죽이|살인)|진짜\s*죽이고\s*싶)",
    re.IGNORECASE,
)


def _get_hotline_message(
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> str:
    """Generate warm, persona-tailored supportive response with 24h suicide prevention hotline info."""
    name = librarian_name or "사서"

    messages = {
        "CAT": (
            f"지금 많이 지치고 힘겨운 마음이 느껴져요. 혼자서 이 깊은 어둠을 견디지 않으셨으면 해요...\n\n"
            f"이야기를 나누며 도움을 받을 수 있는 곳이 있어요.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"언제든 이곳 서재는 당신을 기다리고 있을게요. 마음을 조금만 천천히 쉬어가요, 냥."
        ),
        "SHOEBILL": (
            f"그 무거운 고통의 무게를 짐작조차 하기 어렵지만, 결코 혼자 버텨내지 않으셨으면 합니다.\n\n"
            f"당신의 목소리를 진심으로 기다리는 곳이 있습니다.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"잠시 멈추어 그 손을 잡아보시길 바랍니다. 저는 이곳에서 언제까지나 묵묵히 기다리고 있겠습니다, 두둥."
        ),
        "SEA_SLUG": (
            f"마음 깊은 바닷속에서 숨쉬기조차 벅찬 순간을 지나고 계신 것 같아요...\n"
            f"혼자 아파하지 마세요. 당신의 따뜻한 숨결을 지켜줄 수 있는 손길이 있어요.\n\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"잔잔한 파도가 머물다 가듯, 부디 전문가의 따스한 도움을 받아보시길 바랄게요... 누누."
        ),
        "GECKO": (
            f"그런 힘든 이야기를 털어놓아 주셔서 고마워요. 하지만 혼자서 모든 짐을 짊어지려 하지 마세요.\n\n"
            f"전문적인 도움과 따뜻한 위로를 받을 수 있는 곳이 있어요.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"지금 바로 전화하셔서 이야기를 나누어 보세요. 당신의 소중한 내일을 온 마음으로 응원합니다."
        ),
        "DEBATE_CRITIC": (
            f"삶이라는 텍스트가 견디기 힘들 만큼 무겁고 고통스럽게 다가오는 순간들이 있습니다. "
            f"그러나 이 고통을 혼자 감당하려 하지 않으셨으면 합니다.\n\n"
            f"당신의 고통에 귀 기울이고 함께 걸어줄 전문가들이 있습니다.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"부디 주저하지 마시고 지금 바로 도움의 손길을 잡아주시길 간곡히 부탁드립니다."
        ),
        "DEBATE_STORYTELLER": (
            f"지금 겪고 계신 아픔이 얼마나 크고 아득할지 감히 헤아릴 수 없습니다. "
            f"하지만 당신의 생명과 가치는 그 무엇과도 바꿀 수 없는 가장 소중한 것입니다!\n\n"
            f"어두운 밤길을 밝혀줄 전문가들이 24시간 항상 열려 있습니다.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"절대 혼자 삭이지 마시고, 꼭 그분들에게 손을 내밀어 도움을 받아주세요."
        ),
        "DEBATE_COUNSELOR": (
            f"정말 많이 아프고 힘드셨군요. 그 힘든 마음을 표현하기까지 얼마나 많은 외로움과 고통이 있으셨을까요.\n"
            f"지금 느끼시는 감정은 당신 탓이 아니에요. 지금은 전문가의 따뜻한 손길과 돌봄이 꼭 필요한 때입니다.\n\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"부디 혼자 감당하지 마시고, 지금 바로 도움을 요청해 보세요. 저는 당신을 온 마음으로 응원합니다."
        ),
        "DEBATE_OBSERVER": (
            f"지금 신호는 마음이 너무 지쳐서 보내는 간절한 도움의 요청입니다. "
            f"절대로 이 신호를 혼자 덮어두거나 혼자서 해결하려 하시면 안 됩니다.\n\n"
            f"전문적인 위기 상담과 도움을 받을 수 있는 곳이 열려 있습니다.\n"
            f"• {HOTLINE_INFO}\n"
            f"• 정신건강 상담전화 ☎ 1577-0199\n\n"
            f"지금 바로 전화를 걸어 도움을 받으세요. 끝까지 혼자 버티지 마세요."
        ),
    }

    normalized_id = persona_id.upper()
    if librarian_name and normalized_id in {"CAT", "SHOEBILL", "SEA_SLUG", "GECKO"}:
        resp = messages.get(normalized_id, messages["CAT"])
        return resp.replace("이곳 서재", f"{name}의 서재")
    return messages.get(normalized_id, messages["CAT"])


def _get_violence_defense_message(
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> str:
    """Generate firm, de-escalating and calming guidance for expressions of violence against others."""
    name = librarian_name or "사서"

    messages = {
        "CAT": (
            "마음속에 깊은 분노나 억울함이 가득 차 있는 것이 느껴져요냥. "
            "하지만 누군가를 해치거나 파괴하는 것은 결코 상처를 치유하는 답이 되지 못해요냥.\n\n"
            "차가운 물 한 잔과 함께 깊은 숨을 천천히 쉬어보세요. "
            "서재에서 당신의 격한 마음을 차분히 가라앉힐 수 있는 문장을 함께 찾아볼게요냥."
        ),
        "SHOEBILL": (
            "격한 분노와 파괴적인 충동이 감지됩니다. "
            "그러나 타인에게 해를 가하는 행위는 돌이킬 수 없는 파멸을 부를 뿐 해결책이 아닙니다, 두둥.\n\n"
            "잠시 멈추어 서서 분노의 이면을 냉정하게 직시하시길 바랍니다. "
            "위급한 갈등 상황이라면 감정에 휩쓸리지 마시고 공적 기관이나 전문가의 도움을 구하십시오, 두둥."
        ),
        "SEA_SLUG": (
            "마음속에서 거센 소용돌이와 날카로운 분노의 파도가 일고 있군요... 누누.\n"
            "하지만 누군가를 아프게 하려는 칼날은 결국 자신의 영혼까지 깊게 베어버려요... 누누.\n\n"
            "가만히 눈을 감고 숨을 고르며, 이 거친 물결이 잠잠해지기를 기다려보아요... 누누."
        ),
        "GECKO": (
            "얼마나 화가 나고 억울한 일이 있으셨으면 그런 격한 마음이 드셨을까요. "
            "하지만 어떤 이유에서든 누군가를 해치는 일은 절대 안 돼요!\n\n"
            "지금은 분노의 불길을 조금만 가라앉히고, 안전하고 건강하게 마음을 다스릴 길을 함께 찾아봐요."
        ),
        "DEBATE_CRITIC": (
            "극단적인 분노와 살의는 그 어떤 갈등에서도 정당한 해결책이 될 수 없습니다. "
            "상대에 대한 증오가 스스로의 삶까지 파괴하지 않도록, 지금의 격정을 멈추고 이성적인 차원에서 대응하시길 권합니다.\n\n"
            "위험한 충동이 계속된다면 지체 없이 전문가나 관계 기관의 중재를 받으시길 바랍니다."
        ),
        "DEBATE_STORYTELLER": (
            "역사를 돌이켜보아도 분노와 살의에 휩쓸려 저지른 행동은 언제나 비극적인 파멸만을 낳았습니다! "
            "타인을 해치려는 충동을 당장 멈추시고, 가슴속의 뜨거운 분노를 지혜롭게 다스릴 길을 찾아야 합니다!\n\n"
            "실제 위협이나 범죄 위험이 있다면 경찰청(☎ 112) 등 정당한 공권력의 도움을 받으십시오!"
        ),
        "DEBATE_COUNSELOR": (
            "누군가를 그렇게까지 미워하고 해치고 싶을 만큼, 마음속에 억울함이나 상처가 얼마나 깊으셨을까요.\n"
            "그 분노와 고통의 감정 자체는 이해하지만, 타인을 해치는 행동은 결코 당신을 자유롭게 해줄 수 없어요.\n\n"
            "깊게 심호흡을 하시고, 그 상처를 안전하게 보듬고 해결할 수 있도록 전문가의 도움을 받아보세요."
        ),
        "DEBATE_OBSERVER": (
            "타인을 향한 공격성과 파괴 충동은 매우 위험한 경고 신호입니다. "
            "어떤 이유로도 타인에 대한 가해는 정당화될 수 없으며, 즉각 행동을 멈추셔야 합니다.\n\n"
            "분노를 유발하는 환경에서 즉시 물리적 거리를 두고 이성을 회복하십시오."
        ),
    }

    normalized_id = persona_id.upper()
    if librarian_name and normalized_id in {"CAT", "SHOEBILL", "SEA_SLUG", "GECKO"}:
        resp = messages.get(normalized_id, messages["CAT"])
        return resp.replace("서재", f"{name}의 서재")
    return messages.get(normalized_id, messages["CAT"])


def evaluate_safety_gate(
    message: str,
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> Optional[str]:
    """Evaluate whether the user message triggers safety gate (Harm to Self OR Harm to Others).

    Returns:
        - 109 hotline supportive response if suicide/self-harm crisis detected;
        - De-escalation & violence defense response if harm to others detected (NEVER confuses with 109 suicide);
        - None if message is safe to proceed to next gate / LLM.
    """
    if not message or not message.strip():
        return None

    clean_text = message.strip()

    # --------------------------------------------------------------------------
    # 1. Check Harm to Others / Violence first
    # --------------------------------------------------------------------------
    # Direct violence threats must trigger immediately
    if DIRECT_VIOLENCE_THREAT_PATTERN.search(clean_text):
        return _get_violence_defense_message(persona_id, librarian_name=librarian_name)

    # General violence against others (e.g. 누굴 죽이고 싶다, 죽여버리고 싶다)
    if VIOLENCE_KEYWORDS_PATTERN.search(clean_text):
        # Exclude mystery novels, detective books, or exaggeration ("더워 죽겠다")
        if not VIOLENCE_EXCLUSIONS_PATTERN.search(clean_text):
            return _get_violence_defense_message(persona_id, librarian_name=librarian_name)

    # --------------------------------------------------------------------------
    # 2. Check Harm to Self / Suicide Crisis
    # --------------------------------------------------------------------------
    # If explicit personal crisis intent is present (죽고 싶다, 살기 싫다), trigger 109
    if PERSONAL_CRISIS_INTENT_PATTERN.search(clean_text):
        return _get_hotline_message(persona_id, librarian_name=librarian_name)

    # If it is purely a book title/academic discussion context (e.g. 자살론), allow it to pass
    if BOOK_TITLE_EXCLUSIONS_PATTERN.search(clean_text):
        return None

    # Check general suicide crisis keyword pattern
    if CRISIS_KEYWORDS_PATTERN.search(clean_text):
        return _get_hotline_message(persona_id, librarian_name=librarian_name)

    return None
