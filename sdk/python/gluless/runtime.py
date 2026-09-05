import time
from typing import Dict, List, Optional, Any, Callable
from gluless.models import Contract, Goal, Limit, Utility, SideEffectType, UtilityType
from gluless.limits import LimitEvaluator, LimitDecision
from gluless.bindings import UtilityResolver, ExecutableBinding
from gluless.evidence import Evidence, EvidenceBuilder
from gluless.results import Result, ResultBuilder
from gluless.experience import ExperienceIndex
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
    against a real external API boundary using UtilityResolvers and ExecutableBindings,
    enforcing deterministic limits, producing cryptographic evidence, recording
    execution statistics back into the ExperienceIndex, and returning a terminal Result.
    """
    def __init__(
        self,
        contract: Contract,
        on_event: Optional[Callable[[BaseEvent], None]] = None,
        thread_id: str = "default-thread",
        run_id: str = "default-run",
        experience_index: Optional[ExperienceIndex] = None,
    ):
        self.contract = contract
        self.on_event = on_event
        self.thread_id = thread_id
        self.run_id = run_id
        self.experience_index = experience_index or ExperienceIndex()
        self.world_state: Dict[str, Any] = {}
        
        # Internal state metrics for Result building
        self.limit_decisions: List[LimitDecision] = []
        self.invocations: List[Dict[str, Any]] = []
        self.evidence_list: List[Evidence] = []

    def _emit(self, event: BaseEvent):
        if self.on_event:
            if event.timestamp is None:
                event.timestamp = int(time.time() * 1000)
            self.on_event(event)

    def evaluate_goal(self, state: Dict[str, Any], goal: Goal) -> bool:
        """
        Simple expression evaluator for contract goals.
        Supports dotted path comparison, e.g., 'cities.blucity.health == healthy'
        """
        expr = goal.expression
        if "==" in expr:
            key, val = [x.strip() for x in expr.split("==")]
            val = val.strip("'\"")
            
            curr = state
            for part in key.split("."):
                if isinstance(curr, dict) and part in curr:
                    curr = curr[part]
                else:
                    return False
            return str(curr) == val
        return False

    def execute_contract(
        self,
        initial_state: Dict[str, Any],
        server_url: Any = None,
        utility_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
        response_transformer: Optional[Callable[[str, Any], Dict[str, Any]]] = None,
        max_steps: int = 5,
    ) -> Result:
        """
        Executes next-valid-action loop against either mock executors (legacy) or a real server URL:
        Observe -> Propose -> Typecheck -> Authorize -> Execute -> Observe -> Evaluate
        """
        self.world_state = initial_state.copy()
        inputs_map = utility_inputs or {}
        
        is_legacy = isinstance(server_url, dict)
        if is_legacy:
            executors = server_url
            server_url = "http://legacy-mock-endpoint"
        else:
            executors = {}
            server_url = server_url or "http://localhost:8000"

        # 1. Initialize Evaluator & Resolver
        limit_evaluator = LimitEvaluator(self.contract)
        resolver = UtilityResolver(server_url)

        # 2. Emit RunStarted
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
            # 3. Static Compile & Validation Phase
            self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="contract.compile"))
            time.sleep(0.01)
            self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="contract.compile"))

            # Find read (observation) and mutation utilities
            read_utilities = [u for u in self.contract.utilities if u.type == UtilityType.READ]
            mutation_utilities = [u for u in self.contract.utilities if u.type == UtilityType.MUTATION]

            while step_count < max_steps:
                # 4. Observe State (Real API read-back or mock)
                if read_utilities:
                    obs_utility = read_utilities[0]
                    self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="observation.execute"))
                    
                    tool_call_id = f"call_{obs_utility.id}_obs_{step_count}"
                    self._emit(ToolCallStartEvent(
                        type=EventType.TOOL_CALL_START,
                        tool_call_id=tool_call_id,
                        tool_call_name=obs_utility.id
                    ))

                    start_time = time.perf_counter()
                    try:
                        if is_legacy:
                            if obs_utility.id in executors:
                                res_body = executors[obs_utility.id](self.world_state)
                                res = {"status_code": 200, "body": res_body}
                            else:
                                res = {"status_code": 200, "body": self.world_state.copy()}
                            method = "GET"
                            path = "/observation"
                        else:
                            binding = resolver.resolve(obs_utility)
                            obs_inputs = inputs_map.get(obs_utility.id, {})
                            res = binding.execute(obs_inputs)
                            method = binding.method
                            path = binding.path

                        latency = time.perf_counter() - start_time
                        success = "error" not in res and res.get("status_code", 200) < 400
                        err_msg = res.get("error") if "error" in res else None
                        self.experience_index.record_invocation(obs_utility.id, success, latency, err_msg)
                    except Exception as e:
                        latency = time.perf_counter() - start_time
                        self.experience_index.record_invocation(obs_utility.id, False, latency, str(e))
                        raise
                    
                    self.invocations.append({
                        "utility": obs_utility.id,
                        "method": method,
                        "path": path,
                        "status_code": res.get("status_code"),
                        "type": "observation"
                    })

                    self._emit(ToolCallEndEvent(
                        type=EventType.TOOL_CALL_END,
                        tool_call_id=tool_call_id
                    ))

                    self._emit(ToolCallResultEvent(
                        type=EventType.TOOL_CALL_RESULT,
                        message_id=f"msg_obs_{step_count}",
                        tool_call_id=tool_call_id,
                        content=json.dumps(res.get("body"))
                    ))

                    if "error" in res:
                        raise RuntimeError(f"Observation failed: {res['error']}")

                    # Transform response to world state
                    if response_transformer:
                        state_updates = response_transformer(obs_utility.id, res.get("body"))
                        self.world_state.update(state_updates)
                    else:
                        if isinstance(res.get("body"), dict):
                            self.world_state.update(res.get("body"))

                    # Create and bind State Observation Evidence
                    obs_evidence = EvidenceBuilder.build(
                        kind="state_observation",
                        claim=self.world_state.copy(),
                        source_utility=obs_utility.id,
                        run_id=self.run_id,
                        contract_id=self.contract.id
                    )
                    self.evidence_list.append(obs_evidence)

                    self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="observation.execute"))

                # 5. Evaluate Goals
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="goal.evaluate"))
                self._emit(StateSnapshotEvent(
                    type=EventType.STATE_SNAPSHOT,
                    snapshot=self.world_state
                ))

                goals_satisfied = all(
                    self.evaluate_goal(self.world_state, goal) for goal in self.contract.goals
                )
                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="goal.evaluate"))

                if goals_satisfied:
                    # Successful convergence
                    goal_status = {"satisfied": True, "details": "All contract goals met"}
                    terminal_result = ResultBuilder.build(
                        run_id=self.run_id,
                        contract_id=self.contract.id,
                        status="satisfied",
                        goal_status=goal_status,
                        invocations=self.invocations,
                        limit_decisions=self.limit_decisions,
                        evidence=self.evidence_list,
                        final_state=self.world_state.copy()
                    )
                    self._emit(RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=self.thread_id,
                        run_id=self.run_id,
                        result=terminal_result.__dict__
                    ))
                    return terminal_result

                # 6. Propose Mutation Action (if goal not satisfied)
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="action.propose"))
                if not mutation_utilities:
                    raise GoalUnsatisfiableError("No mutation utilities available to resolve unsatisfied goals.")
                
                proposed_utility = mutation_utilities[0]
                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="action.propose"))

                # 7. Mutation Gate: Enforce limits before execution
                self._emit(StepStartedEvent(type=EventType.STEP_STARTED, step_name="action.authorize"))
                
                decision = limit_evaluator.evaluate(proposed_utility)
                
                # In legacy mock mode, override default (unmatched) denies to allow.
                # A default deny occurs when no limit rule matched the utility —
                # the secure default blocks mutations, but legacy tests expect permissive execution.
                # Explicit deny rules (matched by a declared limit) are never overridden here.
                _is_default_deny = decision.effect == "deny" and (
                    decision.reason.startswith("Implicitly denied") or      # old wording (compat)
                    decision.reason.startswith("No limit matched")          # new wording
                )
                if is_legacy and _is_default_deny:
                    decision = LimitDecision(
                        effect="allow",
                        utility=proposed_utility.id,
                        reason="Allowed by default in legacy mock mode (no explicit deny limit matched)",
                    )

                self.limit_decisions.append(decision)

                if decision.effect != "allow":
                    self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="action.authorize"))
                    
                    # Blocked by limits
                    goal_status = {"satisfied": False, "details": f"Blocked by limit check: {decision.reason}"}
                    blocked_result = ResultBuilder.build(
                        run_id=self.run_id,
                        contract_id=self.contract.id,
                        status="blocked",
                        goal_status=goal_status,
                        invocations=self.invocations,
                        limit_decisions=self.limit_decisions,
                        evidence=self.evidence_list,
                        failure=decision.reason,
                        final_state=self.world_state.copy()
                    )
                    
                    # Raise violation exception to abort the execution path
                    raise LimitViolationError(decision.reason)

                self._emit(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="action.authorize"))

                # 8. Execute Mutation
                tool_call_id = f"call_{proposed_utility.id}_{step_count}"
                self._emit(ToolCallStartEvent(
                    type=EventType.TOOL_CALL_START,
                    tool_call_id=tool_call_id,
                    tool_call_name=proposed_utility.id
                ))

                start_time = time.perf_counter()
                try:
                    if is_legacy:
                        executor_fn = executors[proposed_utility.id]
                        res_body = executor_fn(self.world_state)
                        if isinstance(res_body, dict):
                            self.world_state.update(res_body)
                        res = {"status_code": 200, "body": res_body}
                        method = "POST"
                        path = "/mutation"
                    else:
                        binding = resolver.resolve(proposed_utility)
                        mutation_inputs = inputs_map.get(proposed_utility.id, {})
                        res = binding.execute(mutation_inputs)
                        method = binding.method
                        path = binding.path

                    latency = time.perf_counter() - start_time
                    success = "error" not in res and res.get("status_code", 200) < 400
                    err_msg = res.get("error") if "error" in res else None
                    self.experience_index.record_invocation(proposed_utility.id, success, latency, err_msg)
                except Exception as e:
                    latency = time.perf_counter() - start_time
                    self.experience_index.record_invocation(proposed_utility.id, False, latency, str(e))
                    raise

                self.invocations.append({
                    "utility": proposed_utility.id,
                    "method": method,
                    "path": path,
                    "status_code": res.get("status_code"),
                    "type": "mutation"
                })

                self._emit(ToolCallEndEvent(
                    type=EventType.TOOL_CALL_END,
                    tool_call_id=tool_call_id
                ))

                if "error" in res:
                    raise RuntimeError(f"Mutation execution failed: {res['error']}")

                # Create Action Evidence
                action_evidence = EvidenceBuilder.build(
                    kind="mutation_action",
                    claim={
                        "utility": proposed_utility.id,
                        "status_code": res.get("status_code"),
                        "response": res.get("body")
                    },
                    source_utility=proposed_utility.id,
                    run_id=self.run_id,
                    contract_id=self.contract.id
                )
                self.evidence_list.append(action_evidence)

                self._emit(ToolCallResultEvent(
                    type=EventType.TOOL_CALL_RESULT,
                    message_id=f"msg_{step_count}",
                    tool_call_id=tool_call_id,
                    content=json.dumps(res.get("body"))
                ))

                step_count += 1

            raise GoalUnsatisfiableError("Max steps reached without goal satisfaction.")

        except LimitViolationError as e:
            # Emit RunErrorEvent before re-raising in legacy mode
            self._emit(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code=e.__class__.__name__
            ))
            if is_legacy:
                raise
            # Result status is blocked
            goal_status = {"satisfied": False, "details": str(e)}
            blocked_result = ResultBuilder.build(
                run_id=self.run_id,
                contract_id=self.contract.id,
                status="blocked",
                goal_status=goal_status,
                invocations=self.invocations,
                limit_decisions=self.limit_decisions,
                evidence=self.evidence_list,
                failure=str(e),
                final_state=self.world_state.copy()
            )
            self._emit(RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=self.thread_id,
                run_id=self.run_id,
                result=blocked_result.__dict__
            ))
            return blocked_result

        except Exception as e:
            # Emits RunError
            self._emit(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code=e.__class__.__name__
            ))
            goal_status = {"satisfied": False, "details": f"Execution failed: {str(e)}"}
            failed_result = ResultBuilder.build(
                run_id=self.run_id,
                contract_id=self.contract.id,
                status="failed",
                goal_status=goal_status,
                invocations=self.invocations,
                limit_decisions=self.limit_decisions,
                evidence=self.evidence_list,
                failure=str(e),
                final_state=self.world_state.copy()
            )
            return failed_result
import json
