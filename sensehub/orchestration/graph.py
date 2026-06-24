"""LangGraph 任务工作流：确认门 + 执行，MemorySaver checkpoint."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from sensehub.db import tasks as task_repo
from sensehub.execution.tools.registry import execute_step
from sensehub.models.schemas import PlanStep, StepResult
from sensehub.orchestration.notify import notify
from sensehub.security.audit import log_audit

_checkpointer = MemorySaver()
_compiled_graph = None


class GraphState(TypedDict, total=False):
    task_id: str
    intent_text: str
    trace_id: str
    plan_steps: list[dict]
    step_results: list[dict]
    current_step: int
    status: str
    error: str | None
    needs_confirm: bool


def _plan_steps(state: GraphState) -> list[PlanStep]:
    return [PlanStep(**raw) for raw in state.get("plan_steps", [])]


def _gate_confirm(state: GraphState) -> GraphState:
    if state.get("needs_confirm"):
        interrupt({"action": "wait_confirm", "task_id": state.get("task_id", "")})
    return state


def _execute_steps(state: GraphState) -> GraphState:
    task_id = state["task_id"]
    intent_text = state["intent_text"]
    trace_id = state["trace_id"]
    steps = _plan_steps(state)
    results: list[StepResult] = []

    task_repo.update_task(task_id, status="running")
    partial = task_repo.get_task(task_id)
    if partial:
        notify(partial)

    for index, step in enumerate(steps):
        task_repo.update_task(task_id, current_step=index + 1)
        result = execute_step(step)
        results.append(result)
        task_repo.update_task(task_id, step_results=results)
        partial = task_repo.get_task(task_id)
        if partial:
            notify(partial)

        if not result.success:
            task_repo.update_task(task_id, status="failed", error=result.error)
            log_audit(
                input_text=intent_text,
                action=f"execute:{step.tool}",
                risk_level=step.risk_level,
                result=result.error or "failed",
                trace_id=trace_id,
            )
            final = task_repo.get_task(task_id)
            if final:
                notify(final)
            return {
                **state,
                "step_results": [r.model_dump() for r in results],
                "current_step": index + 1,
                "status": "failed",
                "error": result.error,
            }

    task_repo.update_task(task_id, status="done")
    log_audit(
        input_text=intent_text,
        action="task_complete",
        result="done",
        trace_id=trace_id,
    )
    final = task_repo.get_task(task_id)
    if final:
        notify(final)
    return {
        **state,
        "step_results": [r.model_dump() for r in results],
        "current_step": len(steps),
        "status": "done",
        "error": None,
    }


def build_task_graph():
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    graph = StateGraph(GraphState)
    graph.add_node("gate_confirm", _gate_confirm)
    graph.add_node("execute", _execute_steps)
    graph.set_entry_point("gate_confirm")
    graph.add_edge("gate_confirm", "execute")
    graph.add_edge("execute", END)
    _compiled_graph = graph.compile(checkpointer=_checkpointer)
    return _compiled_graph


def graph_config(task_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": task_id}}


def run_execution_graph(state: GraphState) -> GraphState:
    graph = build_task_graph()
    return graph.invoke(state, graph_config(state["task_id"]))


def resume_execution_graph(task_id: str, resume_value: Any = True) -> GraphState:
    graph = build_task_graph()
    return graph.invoke(Command(resume=resume_value), graph_config(task_id))


def has_graph_checkpoint(task_id: str) -> bool:
    graph = build_task_graph()
    snap = graph.get_state(graph_config(task_id))
    return bool(snap and snap.next)
