from dataclasses import dataclass, field
from typing import List, Optional
from gluless.models import Contract, Utility, SideEffectType

@dataclass
class LimitDecision:
    effect: str  # "allow" | "deny" | "approval_required" | "indeterminate"
    utility: str
    reason: str
    limit_id: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


class LimitEvaluator:
    """
    Evaluate a utility invocation against Contract Limits.

    Evaluation model
    ----------------
    Limits are processed in **declaration order**.  Each matching rule
    updates the current decision; the **last** matching rule wins.

    This is the correct model for the canonical "deny *, allow X" pattern:

        deny *                     → tentative DENY (matches everything)
        allow GasCity.cities.list  → overrides → ALLOW

    Result for GasCity.cities.list:  ALLOW
    Result for GasCity.city.create:  DENY  (only `deny *` matched)
    Result for GasCity.sessions.nudge: DENY (only `deny *` matched)

    Secure default
    --------------
    If no limit matches at all:
      - READ / no-side-effect utilities → ALLOW  (observing state is safe)
      - MUTATION / UNKNOWN              → DENY   (writing requires explicit consent)
    """

    def __init__(self, contract: Contract):
        self.contract = contract

    def _matches(self, pattern_action: str, utility: Utility) -> bool:
        """Return True when pattern_action applies to this utility."""
        p = pattern_action.lower().strip()
        if p == "*":
            return True
        uid = utility.id.lower()
        if p == uid or p in uid:
            return True
        if p == utility.side_effects.value:
            return True
        if p == utility.type.value:
            return True
        return False

    def evaluate(self, utility: Utility) -> LimitDecision:
        is_safe    = utility.side_effects in (SideEffectType.NONE, SideEffectType.READ)
        is_unknown = utility.side_effects == SideEffectType.UNKNOWN

        # Process limits in declaration order — last match wins.
        current_effect:   str                = ""
        current_reason:   str                = ""
        current_limit_id: Optional[str]      = None

        for limit in self.contract.limits:
            pattern = limit.action_pattern.strip().lower()

            if pattern.startswith("deny "):
                action = pattern[5:].strip()
                if self._matches(action, utility):
                    current_effect   = "deny"
                    current_reason   = f"Denied by limit '{limit.id}' ({limit.action_pattern})"
                    current_limit_id = limit.id

            elif pattern.startswith("allow "):
                action = pattern[6:].strip()
                if self._matches(action, utility):
                    current_effect   = "allow"
                    current_reason   = f"Allowed by limit '{limit.id}' ({limit.action_pattern})"
                    current_limit_id = limit.id

        if current_effect:
            return LimitDecision(
                effect=current_effect,
                utility=utility.id,
                reason=current_reason,
                limit_id=current_limit_id,
            )

        # No limit matched — apply secure defaults
        if is_safe and not is_unknown:
            return LimitDecision(
                effect="allow",
                utility=utility.id,
                reason="No limit matched; safe read-only capability permitted by default",
            )

        effect_name = "unknown" if is_unknown else utility.side_effects.value
        return LimitDecision(
            effect="deny",
            utility=utility.id,
            reason=f"No limit matched; mutation/unknown effect '{effect_name}' denied by default",
        )
