import time
from typing import Dict, List, Optional, Any, Callable
from gluless.models import Contract, Goal, Limit, Utility, SideEffectType
from ag_ui.core import (
    BaseEvent,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StepStartedEvent,
    StepFinishedEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    StateSnapshotEvent,
    RunAgentInput,
)

class LimitViolationError(Exception):
    pass

class GoalUnsatisfiableError(Exception):
    pass

class GluLessRuntime:
    """
    GluLess Runtime executes contract verification and execution graphs
    under declared Limits and capability selections, projecting lifecycle
    and tool execution events to the AG-UI protocol format.
    """
    def __init__(
        self,
        contract: Contract,
        on_event: Optional[Callable[[BaseEvent], None]] = None,
        thread_id: str = "default-thread",
        run_id: str = "default-run",
    ):
        self.contract = contract
        self.on_event = on_event
        self.thread_id = thread_id
        self.run_id = run_id
        self.world_state: Dict[str, Any] = {}

    def _emit(self, event: BaseEvent):
        if self.on_event:
            # Set timestamp if not set
            if event.timestamp is None:
                event.timestamp = int(time.time() * 1000)
            self.on_event(event)

    def evaluate_goal(self, state: Dict[str, Any], goal: Goal) -> bool:
        """
        Simple expression evaluator for the MVP slice.
        Supports checking equality of fields, e.g., 'service.health == healthy'
        """
        expr = goal.expression
        if "==" in expr:
            key, val = [x.strip() for x in expr.split("==")]
            val = val.strip("'\"")
            # Navigate nested key if dot-separated
            curr = state
            for part in key.split("."):
                if isinstance(curr, dict) and part in curr:
                    curr = curr[part]
                else:
                    return False
            return str(curr) == val
        return False

    def check_limits(self, utility: Utility) -> None:
        """
        Static and dynamic limit policy check.
        E.g., if a limit is 'deny infrastructure.destroy', we reject any utility
        whose side effects match 'infrastructure' or name contains 'destroy'.
        """
        for limit in self.contract.limits:
            pattern = limit.action_pattern.lower()
            if pattern.startswith("deny "):
                denied_action = pattern[5:].strip()
                # Check match against utility side effects or ID
                if denied_action == "*" or denied_action in utility.id.lower() or denied_action == utility.side_effects.value:
                    raise LimitViolationError(
                        f"Execution of utility '{utility.id}' denied by limit '{limit.id}' ({limit.action_pattern})"
                    )

    def execute_contract(
        self,
        initial_state: Dict[str, Any],
        executors: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]],
        max_steps: int = 10,
    ) -> Dict[str, Any]:
        """
        Executes next-valid-action loop:
        Observe -> Propose -> Typecheck -> Authorize -> Execute -> Observe -> Evaluate
        """
        self.world_state = initial_state.copy()
        
        # 1. Emit RunStarted
        self._emit(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=self.thread_id,
            run_id=self.run_id,
            input=RunAgentInput(
                thread_id=self.thread_id,
                run_id=self.run_id,
                messages=[],
                tools=[],
                context=[],
                forwarded_props={}
            )
        ))

        step_count = 0
        try:
            # 2. Compile / static validation phase
            self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="contract.compile"))
            time.sleep(0.01)
            self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="contract.compile"))

            while step_count < max_steps:
                # 3. Observe state & check goal satisfaction
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="goal.evaluate"))
                
                # Emit state snapshot for the client
                self._emit(StateSnapshotEvent(
                    type=EventType.STATE_SNAPSHOT,
                    snapshot=self.world_state
                ))

                goals_satisfied = all(
                    self.evaluate_goal(self.world_state, goal) for goal in self.contract.goals
                )
                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="goal.evaluate"))

                if goals_satisfied:
                    # Satisfied!
                    result_payload = {
                        "status": "success",
                        "final_state": self.world_state,
                        "steps_taken": step_count
                    }
                    self._emit(RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=self.thread_id,
                        run_id=self.run_id,
                        result=result_payload
                    ))
                    return result_payload

                # 4. Propose Next Valid Action
                # Find a utility that is relevant and not executed.
                # For this MVP slice, we look for a utility whose namespace/resource matches the goal target.
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="action.propose"))
                proposed_utility: Optional[Utility] = None
                for utility in self.contract.utilities:
                    # Simple heuristic: pick the first mutation or state-changing utility
                    # that matches the target domain (e.g. service.health -> service or deployment)
                    proposed_utility = utility
                    break
                
                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="action.propose"))

                if not proposed_utility:
                    raise GoalUnsatisfiableError("No candidate utilities found to satisfy goal.")

                # 5. Typecheck & Authorize (Check Limits)
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="action.authorize"))
                self.check_limits(proposed_utility)
                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="action.authorize"))

                # 6. Execute (via matched tool call lifecycle)
                tool_call_id = f"call_{proposed_utility.id}_{step_count}"
                self._emit(ToolCallStartEvent(
                    type=EventType.TOOL_CALL_START,
                    tool_call_id=tool_call_id,
                    tool_call_name=proposed_utility.id
                ))

                # Run executor
                if proposed_utility.id not in executors:
                    raise ValueError(f"No executor registered for utility id: {proposed_utility.id}")
                
                executor_fn = executors[proposed_utility.id]
                new_state_changes = executor_fn(self.world_state)
                
                # Update world state
                self.world_state.update(new_state_changes)

                self._emit(ToolCallEndEvent(
                    type=EventType.TOOL_CALL_END,
                    tool_call_id=tool_call_id
                ))
                
                self._emit(ToolCallResultEvent(
                    type=EventType.TOOL_CALL_RESULT,
                    message_id=f"msg_{step_count}",
                    tool_call_id=tool_call_id,
                    content="Success"
                ))

                step_count += 1

            raise GoalUnsatisfiableError("Max steps reached without goal satisfaction.")

        except Exception as e:
            # Emit RunError
            self._emit(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code=e.__class__.__name__
            ))
            raise e
