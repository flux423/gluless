from dataclasses import dataclass, field
from typing import List, Dict, Any
from gluless.models import Contract, Utility, SideEffectType

@dataclass
class LimitDecision:
    effect: str  # "allow", "deny", "approval_required", "indeterminate"
    utility: str
    reason: str
    constraints: List[str] = field(default_factory=list)

class LimitEvaluator:
    """
    Evaluates proposed utility invocations against Contract Limits.
    Enforces secure defaults: mutations are denied by default unless explicitly allowed.
    """
    def __init__(self, contract: Contract):
        self.contract = contract

    def evaluate(self, utility: Utility) -> LimitDecision:
        # Determine if the utility has side effects (is a mutation)
        is_safe = utility.side_effects in (SideEffectType.NONE, SideEffectType.READ)
        is_unknown = utility.side_effects == SideEffectType.UNKNOWN

        # Check explicit denies first
        for limit in self.contract.limits:
            pattern = limit.action_pattern.lower()
            if pattern.startswith("deny "):
                denied_action = pattern[5:].strip()
                # Deny if pattern matches utility ID or side effect type
                if denied_action == "*" or denied_action in utility.id.lower() or denied_action == utility.side_effects.value:
                    return LimitDecision(
                        effect="deny",
                        utility=utility.id,
                        reason=f"Explicitly denied by limit '{limit.id}' ({limit.action_pattern})"
                    )

        # Check explicit allows
        explicitly_allowed = False
        allow_reason = ""
        for limit in self.contract.limits:
            pattern = limit.action_pattern.lower()
            if pattern.startswith("allow "):
                allowed_action = pattern[6:].strip()
                if allowed_action == "*" or allowed_action in utility.id.lower() or allowed_action == utility.side_effects.value:
                    explicitly_allowed = True
                    allow_reason = f"Explicitly allowed by limit '{limit.id}' ({limit.action_pattern})"
                    break

        if explicitly_allowed:
            return LimitDecision(
                effect="allow",
                utility=utility.id,
                reason=allow_reason
            )

        # If it is a safe read operation (and not explicitly denied), allow it by default
        if is_safe and not is_unknown:
            return LimitDecision(
                effect="allow",
                utility=utility.id,
                reason="Safe observation capability permitted by default"
            )

        # Secure default: block any mutation or unknown side effect that wasn't explicitly allowed
        effect_name = "unknown" if is_unknown else utility.side_effects.value
        return LimitDecision(
            effect="deny",
            utility=utility.id,
            reason=f"Implicitly denied: mutation/unknown effect '{effect_name}' requires explicit allow limit"
        )
