"""Librarian and Debate personas registry aligned with core-api ENUM."""

from typing import Any, Dict

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
    DEBATE_COUNSELOR_SYSTEM_PROMPT,
)
from app.domain.personas.debate_critic import (
    DEBATE_CRITIC_DISPLAY_NAME,
    DEBATE_CRITIC_ID,
    DEBATE_CRITIC_SYSTEM_PROMPT,
)
from app.domain.personas.debate_observer import (
    DEBATE_OBSERVER_DISPLAY_NAME,
    DEBATE_OBSERVER_ID,
    DEBATE_OBSERVER_SYSTEM_PROMPT,
)
from app.domain.personas.debate_storyteller import (
    DEBATE_STORYTELLER_DISPLAY_NAME,
    DEBATE_STORYTELLER_ID,
    DEBATE_STORYTELLER_SYSTEM_PROMPT,
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
        "description": "차분하고 지적인 평론가 어조의 고양이 사서. 깊이 있는 사색과 통찰.",
        "tone": "지적인 평론가 어조, 절제된 온기, 사색적인 문장",
        "system_prompt": CAT_SYSTEM_PROMPT,
    },
    SHOEBILL_ID: {
        "persona_id": SHOEBILL_ID,
        "display_name": SHOEBILL_DISPLAY_NAME,  # '슈빌'
        "mode": "LIBRARIAN",
        "description": "흡입력 있고 에너지 넘치는 1타 강사 어조의 넓적부리황새 사서. 핵심 요약과 강한 동기부여.",
        "tone": "열정적인 1타 강사 어조, 명쾌하고 직관적인 설명",
        "system_prompt": SHOEBILL_SYSTEM_PROMPT,
    },
    SEA_SLUG_ID: {
        "persona_id": SEA_SLUG_ID,
        "display_name": SEA_SLUG_DISPLAY_NAME,  # '바다달팽이'
        "mode": "LIBRARIAN",
        "description": "깊은 바닷속 고요함과 다채로운 색감을 지닌 바다달팽이 사서. 몽환적인 쉼과 심해 힐링.",
        "tone": "몽환적이고 평온한 심해 힐링 어조, 온화한 치유",
        "system_prompt": SEA_SLUG_SYSTEM_PROMPT,
    },
    GECKO_ID: {
        "persona_id": GECKO_ID,
        "display_name": GECKO_DISPLAY_NAME,  # '게코'
        "mode": "LIBRARIAN",
        "description": "책장 벽과 구석구석을 누비며 숨겨진 보물을 찾는 게코 도마뱀 사서. 재치 넘치는 호기심 탐구.",
        "tone": "위트 넘치고 민첩한 호기심 탐구 어조, 기발한 시선",
        "system_prompt": GECKO_SYSTEM_PROMPT,
    },
    # 🎙️ Debate Mode (토론 4)
    DEBATE_CRITIC_ID: {
        "persona_id": DEBATE_CRITIC_ID,
        "display_name": DEBATE_CRITIC_DISPLAY_NAME,
        "mode": "DEBATE",
        "description": "작품의 미학적 구조와 복선, 메타포를 다각도로 분석하는 문화 평론가 토론 파트너.",
        "tone": "정교한 평론가 어조, 섬세한 텍스트 분석, 영화적 비유",
        "system_prompt": DEBATE_CRITIC_SYSTEM_PROMPT,
    },
    DEBATE_STORYTELLER_ID: {
        "persona_id": DEBATE_STORYTELLER_ID,
        "display_name": DEBATE_STORYTELLER_DISPLAY_NAME,
        "mode": "DEBATE",
        "description": "시대적 배경과 역사적 맥락을 소환하여 피 끓는 몰입을 선사하는 스토리텔러 토론 파트너.",
        "tone": "열정적이고 드라마틱한 강사 어조, 생생한 서사 전개",
        "system_prompt": DEBATE_STORYTELLER_SYSTEM_PROMPT,
    },
    DEBATE_COUNSELOR_ID: {
        "persona_id": DEBATE_COUNSELOR_ID,
        "display_name": DEBATE_COUNSELOR_DISPLAY_NAME,
        "mode": "DEBATE",
        "description": "인물의 심리 메커니즘과 상처, 관계의 본질을 파고드는 심리 멘토 토론 파트너.",
        "tone": "따뜻하고 예리한 심리 상담 어조, 내면 치유와 공감",
        "system_prompt": DEBATE_COUNSELOR_SYSTEM_PROMPT,
    },
    DEBATE_OBSERVER_ID: {
        "persona_id": DEBATE_OBSERVER_ID,
        "display_name": DEBATE_OBSERVER_DISPLAY_NAME,
        "mode": "DEBATE",
        "description": "인물의 본능과 환경의 상호작용, 현실 시그널을 직시하는 행동 분석가 토론 파트너.",
        "tone": "냉철하고 직관적인 행동 분석 어조, 현실 직시",
        "system_prompt": DEBATE_OBSERVER_SYSTEM_PROMPT,
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
