"""Crew assembly for multi-platform content planning."""

from __future__ import annotations

from crewai import Crew, Process

from .agents import get_all_agents
from .tasks import get_all_tasks


class ContentPlanningCrew:
    def __init__(
        self,
        product: str,
        audience: str,
        goal: str,
        platforms: str,
        style: str,
        selling_points: str = "",
        material_source: str = "用户不提供素材，由 AI 生成素材建议",
        video_type: str = "图文快闪",
        video_duration: str = "30 秒",
        material_notes: str = "",
        material_assets: str = "",
        revision_feedback: str = "",
        verbose: bool = True,
    ):
        self.inputs = {
            "product": product,
            "audience": audience,
            "goal": goal,
            "platforms": platforms,
            "style": style,
            "selling_points": selling_points,
            "material_source": material_source,
            "video_type": video_type,
            "video_duration": video_duration,
            "material_notes": material_notes,
            "material_assets": material_assets,
            "revision_feedback": revision_feedback,
        }
        self.verbose = verbose
        self._agents = None
        self._tasks = None
        self._crew = None

    @property
    def agents(self):
        if self._agents is None:
            self._agents = get_all_agents()
        return self._agents

    @property
    def tasks(self):
        if self._tasks is None:
            self._tasks = get_all_tasks(self.agents, **self.inputs)
        return self._tasks

    @property
    def crew(self):
        if self._crew is None:
            self._crew = Crew(
                agents=list(self.agents.values()),
                tasks=self.tasks,
                process=Process.sequential,
                verbose=self.verbose,
            )
        return self._crew

    def run(self) -> str:
        return str(self.crew.kickoff())

    def get_task_outputs(self) -> dict[str, str]:
        names = ["strategy", "copy", "platform", "review", "video"]
        return {
            name: str(task.output)
            for name, task in zip(names, self.tasks)
            if task.output
        }


def create_crew(**kwargs) -> ContentPlanningCrew:
    return ContentPlanningCrew(**kwargs)
