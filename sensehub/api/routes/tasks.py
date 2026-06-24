from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.cognition.brain import BrainPipelineError
from sensehub.cognition.dispatch import process_user_input
from sensehub.db import tasks as task_repo
from sensehub.execution.kill_switch import activate
from sensehub.licensing.tier import feature_enabled
from sensehub.models.schemas import TaskCreate, TaskResponse
from sensehub.orchestration.multi_agent import run_multi_agent_task
from sensehub.orchestration.runner import cancel_task, confirm_and_run, run_task

router = APIRouter(tags=["tasks"])


def _start_task_with_plan(
    background_tasks: BackgroundTasks,
    text: str,
    plan,
    *,
    prefix: str = "",
) -> TaskResponse:
    intent = f"{prefix}{text}" if prefix else text
    task_id = task_repo.create_task(intent)
    background_tasks.add_task(run_task, task_id, intent, plan=plan)
    task = task_repo.get_task(task_id)
    assert task
    return task


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="指令不能为空")
    try:
        result = await process_user_input(text, source="text")
    except BrainPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    action = result.get("action")
    if action in ("answer", "status", "cancel"):
        raise HTTPException(
            status_code=422,
            detail={
                "action": action,
                "message": result.get("message", ""),
                "reply": result.get("reply"),
                "hint": "这是问答/状态查询，不会创建执行任务；请使用综合控制台或语音通道",
            },
        )
    if action == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "大脑处理失败"))
    plan = result.get("plan")
    if not plan:
        raise HTTPException(status_code=400, detail="规划脑未生成计划")
    return _start_task_with_plan(background_tasks, text, plan)


@router.post("/tasks/multi-agent", response_model=TaskResponse)
async def create_multi_agent_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user),
):
    if not feature_enabled("multi_agent"):
        raise HTTPException(status_code=403, detail="多 Agent 协调需要 Max 档位")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="指令不能为空")
    try:
        result = await process_user_input(text, source="text")
    except BrainPipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    action = result.get("action")
    if action != "execute":
        raise HTTPException(
            status_code=422,
            detail={
                "action": action,
                "reply": result.get("reply"),
                "message": result.get("message"),
            },
        )
    plan = result.get("plan")
    if not plan:
        raise HTTPException(status_code=400, detail="规划脑未生成计划")

    task_id = task_repo.create_task(f"[多Agent] {text}")
    background_tasks.add_task(run_multi_agent_task, task_id, text, plan=plan, agents=result.get("agents"))
    task = task_repo.get_task(task_id)
    assert task
    return task


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(_: str = Depends(get_current_user)):
    return task_repo.list_tasks()


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, _: str = Depends(get_current_user)):
    task = task_repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/tasks/{task_id}/confirm", response_model=TaskResponse)
async def confirm_task(task_id: str, _: str = Depends(get_current_user)):
    try:
        return await confirm_and_run(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel(task_id: str, _: str = Depends(get_current_user)):
    task = cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/kill-switch")
async def kill_switch(_: str = Depends(get_current_user)):
    activate()
    return {"status": "killed", "message": "已停止所有自动化操作"}


@router.post("/kill-switch/reset")
async def kill_switch_reset(_: str = Depends(get_current_user)):
    from sensehub.execution.kill_switch import reset

    reset()
    return {"status": "ok", "message": "Kill Switch 已重置"}
