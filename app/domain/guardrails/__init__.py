"""Multi-tier Guardrail Package for backend-ai-agent.

Provides 4-tier zero-cost multi-defense pipeline:
- 0th: Auth Gate (JWT signature verification / Guest bypass in router)
- 1st: Safety Gate (Crisis / self-harm / 109 hotline / book title exception)
- 2nd: Input Gate (Meaningless Jamo / numbers / emojis prompt guidance)
- 3rd: Security Gate (Prompt leak / Jailbreak / PII protection)
"""

from typing import Optional

from app.domain.guardrails.input_gate import evaluate_input_gate
from app.domain.guardrails.safety_gate import evaluate_safety_gate
from app.domain.guardrails.security_gate import evaluate_security_gate
from app.domain.guardrails.shared_rules import SHARED_GUARDRAILS

__all__ = [
    "SHARED_GUARDRAILS",
    "evaluate_guardrails",
    "evaluate_safety_gate",
    "evaluate_input_gate",
    "evaluate_security_gate",
]


def evaluate_guardrails(
    message: str,
    persona_id: str,
    librarian_name: Optional[str] = None,
) -> Optional[str]:
    """Execute all pre-LLM regex guardrails sequentially with 0ms delay.

    Evaluation Order:
      1. Safety Gate (Self-harm / suicide crisis -> 109 hotline)
      2. Input Gate (Meaningless Jamo, numbers, emojis -> prompt guidance)
      3. Security Gate (Prompt leak, Jailbreak, PII -> security refusal)

    Returns:
        Refusal or guidance string if any gate triggers; None if completely clean.
    """
    # 1. First Gate: Safety Gate
    safety_reply = evaluate_safety_gate(message, persona_id, librarian_name=librarian_name)
    if safety_reply:
        return safety_reply

    # 2. Second Gate: Input Gate
    input_reply = evaluate_input_gate(message, persona_id, librarian_name=librarian_name)
    if input_reply:
        return input_reply

    # 3. Third Gate: Security Gate
    security_reply = evaluate_security_gate(message, persona_id, librarian_name=librarian_name)
    if security_reply:
        return security_reply

    return None
