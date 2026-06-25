"""综合控制台 API."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.cognition.brain import BrainPipelineError
from sensehub.cognition.dispatch import (
    enrich_agents_with_task,
    process_code_assist,
    process_studio_chat,
    process_user_input,
    synthesize_task_reply,
)
from sensehub.db import tasks as task_repo
from sensehub.licensing.tier import feature_enabled
from sensehub.models.schemas import CodeAssistCreate, ExecutionPlan, TaskCreate
from sensehub.orchestration.autonomous import run_autonomous_task
from sensehub.orchestration.multi_agent import run_multi_agent_task
from sensehub.orchestration.runner import run_task
from sensehub.perception.virtual_session import VirtualScreenSession
from sensehub.security.audit import log_audit

router = APIRouter(tags=["hub"])


def _start_execute_task(
    background_tasks: BackgroundTasks,
    text: str,
    plan: ExecutionPlan,
    *,
    agents: list[dict] | None = None,
    brain_message: str = "",
) -> dict:
    """大脑已规划 → 后台执行（Max 用 multi_agent，其余用 run_task）."""
    task_id = task_repo.create_task(text)
    if feature_enabled("multi_agent"):
        background_tasks.add_task(run_multi_agent_task, task_id, text, plan=plan)
        message = "已提交多脑协作执行（程序化工具优先，VLM 兜底）"
    else:
        background_tasks.add_task(run_task, task_id, text, plan=plan)
        message = "已提交大脑规划执行"
    task = task_repo.get_task(task_id)
    assert task
    return {
        "handled": True,
        "action": "task",
        "message": brain_message or message,
        "task_id": task_id,
        "task": task.model_dump(),
        "plan": plan.model_dump(),
        "agents": agents or [],
    }


def _create_wait_confirm_response(
    text: str,
    plan: ExecutionPlan,
    *,
    agents: list[dict] | None = None,
    brain_message: str = "",
) -> dict:
    """L2 待确认：仅登记计划，不后台偷跑（用户点确认后再执行）."""
    task_id = task_repo.create_task(text)
    message = brain_message or plan.summary or "该操作需你确认后才会继续执行"
    task_repo.update_task(
        task_id,
        status="wait_confirm",
        summary=message,
        plan_steps=plan.steps,
    )
    task = task_repo.get_task(task_id)
    assert task
    return {
        "handled": True,
        "action": "task",
        "message": message,
        "task_id": task_id,
        "task": task.model_dump(),
        "plan": plan.model_dump(),
        "agents": agents or [],
    }


@router.post("/studio/chat")
async def studio_chat(body: TaskCreate, username: str = Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="内容不能为空")
    from sensehub.db import users as user_store

    user = user_store.get_user(username.strip().lower())
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    user_id = str(user["user_id"])
    try:
        result = await process_studio_chat(
            text,
            history=[h.model_dump() for h in body.history],
            session_id=body.session_id,
            user_id=user_id,
            model_id=body.model_id,
        )
    except BrainPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "handled": True,
        "action": "answer",
        "reply": result.get("reply", ""),
        "session_id": result.get("session_id") or body.session_id,
        "model_id": result.get("model_id"),
        "model_used": result.get("model_used"),
        "harness_trace": result.get("harness_trace"),
    }


@router.post("/code/assist")
async def code_assist(body: CodeAssistCreate, username: str = Depends(get_current_user)):
    from sensehub.db import wallet as wallet_store

    if not wallet_store.is_plugin_enabled(username, "code"):
        raise HTTPException(status_code=403, detail="请先在控制台启用 Code Agent 插件")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="内容不能为空")
    try:
        result = await process_code_assist(
            text,
            project_root=body.project_root,
            project_files=body.project_files,
            file_path=body.file_path,
            file_content=body.file_content,
            context_files=body.context_files,
            history=[h.model_dump() for h in body.history],
            model_id=body.model_id,
            mode=body.mode,
        )
    except BrainPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "handled": True,
        "action": "answer",
        "reply": result.get("reply", ""),
        "edits": result.get("edits") or [],
        "mode": result.get("mode"),
        "model_id": result.get("model_id"),
    }


@router.post("/hub/command")
async def hub_command(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    username: str = Depends(get_current_user),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="指令不能为空")

    from sensehub.db import users as user_store

    user = user_store.get_user(username.strip().lower())
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    user_id = str(user["user_id"])

    try:
        result = await process_user_input(
            text,
            source="text",
            history=[h.model_dump() for h in body.history],
            session_id=body.session_id,
            user_id=user_id,
        )
    except BrainPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    action = result.get("action")
    if action in ("answer", "status", "cancel"):
        log_audit(input_text=text, action=f"brain_{action}", result=result.get("reply", "")[:200])
        return {
            "handled": True,
            "action": action,
            "reply": result.get("reply"),
            "message": result.get("message", ""),
            "agents": result.get("agents", []),
        }

    if action == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "处理失败"))

    plan = result.get("plan")
    if not plan:
        raise HTTPException(status_code=400, detail="未能生成执行计划")
    if isinstance(plan, dict):
        plan = ExecutionPlan(**plan)

    if result.get("executed"):
        reply = str(result.get("reply") or "")
        task_id = task_repo.create_task(text)
        step_results = result.get("step_results") or []
        task_repo.update_task(
            task_id,
            status="done",
            summary=reply,
            plan_steps=plan.steps,
            current_step=len(plan.steps),
            step_results=step_results,
        )
        task = task_repo.get_task(task_id)
        if not task:
            raise HTTPException(status_code=500, detail="任务状态丢失")
        agents = enrich_agents_with_task(list(result.get("agents") or []), plan, task)
        log_audit(input_text=text, action="brain_execute", result=reply[:200])
        return {
            "handled": True,
            "action": "execute",
            "reply": reply,
            "message": reply,
            "task_id": task_id,
            "task": task.model_dump(),
            "plan": plan.model_dump(),
            "agents": agents,
            "session_id": result.get("session_id") or body.session_id,
        }

    needs_confirm = any(s.requires_confirm for s in plan.steps)
    if needs_confirm:
        log_audit(input_text=text, action="brain_execute", result=result.get("message", "")[:200])
        return _create_wait_confirm_response(
            text,
            plan,
            agents=result.get("agents"),
            brain_message=str(result.get("message") or result.get("reply") or ""),
        )

    task_id = task_repo.create_task(text)
    agents = list(result.get("agents") or [])
    if feature_enabled("multi_agent"):
        task = await run_multi_agent_task(task_id, text, plan=plan, agents=agents)
    else:
        task = await run_task(task_id, text, plan=plan)
    if not task:
        raise HTTPException(status_code=500, detail="任务执行后状态丢失")

    agents = enrich_agents_with_task(agents, plan, task)
    try:
        reply = await synthesize_task_reply(
            text, plan, task, agents=agents, history=[h.model_dump() for h in body.history]
        )
    except Exception:
        from sensehub.cognition.session_context import fallback_reply_from_task

        reply = fallback_reply_from_task(plan, task)
    log_audit(input_text=text, action="brain_execute", result=reply[:200])

    return {
        "handled": True,
        "action": "execute" if task.status == "done" else task.status,
        "reply": reply,
        "message": reply,
        "task_id": task_id,
        "task": task.model_dump(),
        "plan": plan.model_dump(),
        "agents": agents,
        "session_id": result.get("session_id") or body.session_id,
    }


@router.post("/hub/autonomous")
async def hub_autonomous(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="目标不能为空")
    if not feature_enabled("multi_agent"):
        raise HTTPException(status_code=403, detail="自主 Agent 需要 Max 档位")

    task_id = task_repo.create_task(f"[自主] {text}")
    background_tasks.add_task(run_autonomous_task, task_id, text)
    task = task_repo.get_task(task_id)
    assert task
    return {
        "handled": True,
        "action": "autonomous",
        "message": "自主 Agent 已启动（多脑规划 + 逐步执行）",
        "task_id": task_id,
        "task": task.model_dump(),
    }


@router.get("/virtual-screen/session")
async def virtual_session_status(_: str = Depends(get_current_user)):
    return VirtualScreenSession.status()


@router.post("/virtual-screen/session/start")
async def virtual_session_start(_: str = Depends(get_current_user)):
    try:
        return VirtualScreenSession.start()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/virtual-screen/session/stop")
async def virtual_session_stop(_: str = Depends(get_current_user)):
    return VirtualScreenSession.stop()


@router.post("/virtual-screen/keyboard/toggle")
async def virtual_keyboard_toggle(enabled: bool = True, _: str = Depends(get_current_user)):
    return VirtualScreenSession.toggle_keyboard(enabled)


@router.post("/virtual-screen/keyboard/key")
async def virtual_keyboard_key(body: dict, _: str = Depends(get_current_user)):
    key = str(body.get("key", ""))
    if not key:
        raise HTTPException(status_code=400, detail="缺少 key")
    if key == "Backspace":
        VirtualScreenSession.press_key("backspace")
    elif key == "Enter":
        VirtualScreenSession.press_key("enter")
    elif key == "Space":
        VirtualScreenSession.type_text(" ")
    else:
        VirtualScreenSession.type_text(key)
    return {"ok": True}
