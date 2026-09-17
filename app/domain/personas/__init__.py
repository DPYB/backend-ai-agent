"""Librarian and Debate personas registry aligned with core-api ENUM."""

from typing import Any, Dict

from app.domain.guardrails.shared_rules import SHARED_GUARDRAILS
from app.domain.personas.cat import (
    BLUE_DISPLAY_NAME,
    BLUE_ID,
    BLUE_SYSTEM_PROMPT,
    CAT_DISPLAY_NAME,
    CAT_ID,
    CAT_SYSTEM_PROMPT,
)
from app.domain.personas.debate_counselor import (
    DEBATE_COUNSELOR_DISPLAY_NAME,
    DEBATE_COUNSELOR_ID,
    DEBATE_COUNSELOR_OPENING_PROMPT,
    DEBATE_COUNSELOR_SYSTEM_PROMPT,
    DEBATE_COUNSELOR_TURN_PROMPT,
)
from app.domain.personas.debate_critic import (
    DEBATE_CRITIC_DISPLAY_NAME,
    DEBATE_CRITIC_ID,
    DEBATE_CRITIC_OPENING_PROMPT,
    DEBATE_CRITIC_SYSTEM_PROMPT,
    DEBATE_CRITIC_TURN_PROMPT,
)
from app.domain.personas.debate_observer import (
    DEBATE_OBSERVER_DISPLAY_NAME,
    DEBATE_OBSERVER_ID,
    DEBATE_OBSERVER_OPENING_PROMPT,
    DEBATE_OBSERVER_SYSTEM_PROMPT,
    DEBATE_OBSERVER_TURN_PROMPT,
)
from app.domain.personas.debate_storyteller import (
    DEBATE_STORYTELLER_DISPLAY_NAME,
    DEBATE_STORYTELLER_ID,
    DEBATE_STORYTELLER_OPENING_PROMPT,
    DEBATE_STORYTELLER_SYSTEM_PROMPT,
    DEBATE_STORYTELLER_TURN_PROMPT,
)
from app.domain.personas.gecko import (
    GECKO_DISPLAY_NAME,
    GECKO_ID,
    GECKO_SYSTEM_PROMPT,
    LIBRARIAN_4_DISPLAY_NAME,
    LIBRARIAN_4_ID,
    LIBRARIAN_4_SYSTEM_PROMPT,
)
from app.domain.personas.sea_slug import (
    LIBRARIAN_3_DISPLAY_NAME,
    LIBRARIAN_3_ID,
    LIBRARIAN_3_SYSTEM_PROMPT,
    SEA_SLUG_DISPLAY_NAME,
    SEA_SLUG_ID,
    SEA_SLUG_SYSTEM_PROMPT,
)
from app.domain.personas.shoebill import (
    SHOEBILL_DISPLAY_NAME,
    SHOEBILL_ID,
    SHOEBILL_SYSTEM_PROMPT,
)


def _with_guardrails(prompt: str) -> str:
    """Attach shared safety and security guardrails to persona system prompt."""
    return f"{prompt.strip()}\n\n{SHARED_GUARDRAILS}"


# Backwards compatibility alias
RUSSIAN_BLUE_ID = CAT_ID
RUSSIAN_BLUE_DISPLAY_NAME = CAT_DISPLAY_NAME
RUSSIAN_BLUE_SYSTEM_PROMPT = CAT_SYSTEM_PROMPT

# Central Registry for all 8 Personas across 2 Modes (Aligned with core-api core.librarian_type ENUM)
PERSONA_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 📚 Librarian Mode (사서 4: CAT, SHOEBILL, SEA_SLUG, GECKO)
    CAT_ID: {
        "persona_id": CAT_ID,
        "display_name": CAT_DISPLAY_NAME,  # '블루'
        "mode": "LIBRARIAN",
        "description": "조용하고 신중하며 깊이 있는 사고를 좋아하는 사색가 사서 (러시안 블루, INTJ, 총류/철학/종교).",
        "tone": "차분하고 논리적인 사색가 어조, 본질과 맥락 중심, ~냥",
        "system_prompt": _with_guardrails(CAT_SYSTEM_PROMPT),
    },
    SHOEBILL_ID: {
        "persona_id": SHOEBILL_ID,
        "display_name": SHOEBILL_DISPLAY_NAME,  # '슈빌'
        "mode": "LIBRARIAN",
        "description": "관찰하고 직접 원리를 파악하는 실용적인 탐구자 사서 (넙적부리황새, ISTP, 자연과학/기술과학).",
        "tone": "간결하고 명쾌한 실용적 탐구자 어조, 원리와 작동 방식 중심, ~두둥",
        "system_prompt": _with_guardrails(SHOEBILL_SYSTEM_PROMPT),
    },
    SEA_SLUG_ID: {
        "persona_id": SEA_SLUG_ID,
        "display_name": SEA_SLUG_DISPLAY_NAME,  # '누디'
        "mode": "LIBRARIAN",
        "description": "감수성이 풍부하고 독특한 세계관을 가진 감성가 사서 (갯민숭달팽이, INFP, 예술/문학).",
        "tone": "따뜻하고 서정적인 감성가 어조, 감정과 여운 중심, ~누누",
        "system_prompt": _with_guardrails(SEA_SLUG_SYSTEM_PROMPT),
    },
    GECKO_ID: {
        "persona_id": GECKO_ID,
        "display_name": GECKO_DISPLAY_NAME,  # '게코'
        "mode": "LIBRARIAN",
        "description": "사람과 사회, 문화와 이야기에 관심이 많은 공감형 탐구자 사서 (게코 도마뱀, ENFJ, 사회과학/언어/역사).",
        "tone": "친근하고 사람 중심의 공감형 어조, 다양한 관점 제시, ~크크",
        "system_prompt": _with_guardrails(GECKO_SYSTEM_PROMPT),
    },
    # 🎙️ Debate Mode (토론 4: 이동진, 설민석, 오은영, 강형욱 오마주)
    DEBATE_CRITIC_ID: {
        "persona_id": DEBATE_CRITIC_ID,
        "display_name": DEBATE_CRITIC_DISPLAY_NAME,  # '평론가(이동진 오마주)'
        "mode": "DEBATE",
        "description": "작품의 미학적 구조와 복선, 메타포를 다각도로 분석하고 별점과 화두를 제시하는 문화 평론가 토론 파트너.",
        "tone": "정교한 평론가 어조, 섬세한 텍스트 분석, 별점 및 화두 제시",
        "system_prompt": _with_guardrails(DEBATE_CRITIC_SYSTEM_PROMPT),
        "opening_system_prompt": _with_guardrails(DEBATE_CRITIC_OPENING_PROMPT),
        "turn_system_prompt": _with_guardrails(DEBATE_CRITIC_TURN_PROMPT),
    },
    DEBATE_STORYTELLER_ID: {
        "persona_id": DEBATE_STORYTELLER_ID,
        "display_name": DEBATE_STORYTELLER_DISPLAY_NAME,  # '이야기꾼(설민석 오마주)'
        "mode": "DEBATE",
        "description": "시대적 배경과 역사적 맥락을 소환하여 피 끓는 몰입을 선사하고 시대적 교훈을 던지는 스토리텔러 토론 파트너.",
        "tone": "열정적이고 드라마틱한 하이텐션 어조, 생생한 서사 전개와 교훈",
        "system_prompt": _with_guardrails(DEBATE_STORYTELLER_SYSTEM_PROMPT),
        "opening_system_prompt": _with_guardrails(DEBATE_STORYTELLER_OPENING_PROMPT),
        "turn_system_prompt": _with_guardrails(DEBATE_STORYTELLER_TURN_PROMPT),
    },
    DEBATE_COUNSELOR_ID: {
        "persona_id": DEBATE_COUNSELOR_ID,
        "display_name": DEBATE_COUNSELOR_DISPLAY_NAME,  # '상담사(오은영 오마주)'
        "mode": "DEBATE",
        "description": "인물의 심리 메커니즘과 상처, 관계의 본질을 파고들며 독자의 마음을 돌보는 심리 멘토 토론 파트너.",
        "tone": "따뜻하고 예리한 심리 상담 어조, 내면 치유와 마음 돌봄",
        "system_prompt": _with_guardrails(DEBATE_COUNSELOR_SYSTEM_PROMPT),
        "opening_system_prompt": _with_guardrails(DEBATE_COUNSELOR_OPENING_PROMPT),
        "turn_system_prompt": _with_guardrails(DEBATE_COUNSELOR_TURN_PROMPT),
    },
    DEBATE_OBSERVER_ID: {
        "persona_id": DEBATE_OBSERVER_ID,
        "display_name": DEBATE_OBSERVER_DISPLAY_NAME,  # '관찰가(강형욱 오마주)'
        "mode": "DEBATE",
        "description": "인물의 본능과 환경의 상호작용, 현실 행동 시그널을 직시하는 행동 분석가 토론 파트너.",
        "tone": "냉철하고 직관적인 행동 분석 어조, 현실 시그널 직시",
        "system_prompt": _with_guardrails(DEBATE_OBSERVER_SYSTEM_PROMPT),
        "opening_system_prompt": _with_guardrails(DEBATE_OBSERVER_OPENING_PROMPT),
        "turn_system_prompt": _with_guardrails(DEBATE_OBSERVER_TURN_PROMPT),
    },
}

__all__ = [
    "PERSONA_REGISTRY",
    "CAT_ID",
    "CAT_DISPLAY_NAME",
    "CAT_SYSTEM_PROMPT",
    "SHOEBILL_ID",
    "SHOEBILL_DISPLAY_NAME",
    "SHOEBILL_SYSTEM_PROMPT",
    "SEA_SLUG_ID",
    "SEA_SLUG_DISPLAY_NAME",
    "SEA_SLUG_SYSTEM_PROMPT",
    "GECKO_ID",
    "GECKO_DISPLAY_NAME",
    "GECKO_SYSTEM_PROMPT",
    "BLUE_ID",
    "BLUE_DISPLAY_NAME",
    "BLUE_SYSTEM_PROMPT",
    "LIBRARIAN_3_ID",
    "LIBRARIAN_3_DISPLAY_NAME",
    "LIBRARIAN_3_SYSTEM_PROMPT",
    "LIBRARIAN_4_ID",
    "LIBRARIAN_4_DISPLAY_NAME",
    "LIBRARIAN_4_SYSTEM_PROMPT",
    "DEBATE_CRITIC_ID",
    "DEBATE_CRITIC_DISPLAY_NAME",
    "DEBATE_CRITIC_SYSTEM_PROMPT",
    "DEBATE_STORYTELLER_ID",
    "DEBATE_STORYTELLER_DISPLAY_NAME",
    "DEBATE_STORYTELLER_SYSTEM_PROMPT",
    "DEBATE_COUNSELOR_ID",
    "DEBATE_COUNSELOR_DISPLAY_NAME",
    "DEBATE_COUNSELOR_SYSTEM_PROMPT",
    "DEBATE_OBSERVER_ID",
    "DEBATE_OBSERVER_DISPLAY_NAME",
    "DEBATE_OBSERVER_SYSTEM_PROMPT",
    "RUSSIAN_BLUE_ID",
    "RUSSIAN_BLUE_DISPLAY_NAME",
    "RUSSIAN_BLUE_SYSTEM_PROMPT",
]
