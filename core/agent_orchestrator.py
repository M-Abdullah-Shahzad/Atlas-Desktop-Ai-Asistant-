from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.agents import CodingAgent, JobAgent, MeetingAgent
from core.workspace_manager import WorkspaceManager


@dataclass
class AgentTask:
    task_id: str
    agent: str
    request: str
    status: str = "PLANNING"
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """Minimal orchestrator for Atlas's planning and execution phases."""

    def __init__(self, root: str | None = None):
        self.workspace = WorkspaceManager(root)
        self.tasks: list[AgentTask] = []
        self.agents = {
            "coding": CodingAgent(self.workspace),
            "meeting": MeetingAgent(self.workspace),
            "job": JobAgent(self.workspace),
        }

    def create_task(self, agent: str, request: str, task_id: str | None = None) -> AgentTask:
        task = AgentTask(task_id=task_id or f"TASK-{len(self.tasks) + 1:03d}", agent=agent, request=request)
        self.tasks.append(task)
        return task

    def run_task(self, task: AgentTask) -> dict[str, Any]:
        agent = self.agents.get(task.agent)
        if not agent:
            raise ValueError(f"Unknown agent: {task.agent}")

        task.status = "RUNNING"
        if task.agent == "coding":
            result = agent.plan_project(task.request)
        elif task.agent == "meeting":
            result = agent.plan_meeting(task.request)
        else:
            result = agent.plan_job_search(task.request)

        task.status = "COMPLETED"
        task.metadata.update(result)
        return result

    def send_whatsapp_topic(self, contact: str, topic: str, player=None) -> str:
        """Send a topic-generated WhatsApp message using the default English drafting rules."""
        from actions.whatsapp_control import whatsapp_control

        return whatsapp_control(
            parameters={
                "action": "message",
                "contact": contact,
                "topic": topic,
            },
            player=player,
        )

    def status_summary(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self.workspace.root),
            "task_count": len(self.tasks),
            "tasks": [
                {"task_id": t.task_id, "agent": t.agent, "status": t.status}
                for t in self.tasks
            ],
        }
