from __future__ import annotations

from collections import defaultdict, deque

from .models import TaskBrief


class TaskGraphError(ValueError):
    pass


def validate_task_graph(tasks: list[TaskBrief]) -> list[str]:
    """Validate dependencies and return a deterministic topological order."""
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise TaskGraphError("Task IDs must be unique")

    indegree = {task.task_id: 0 for task in tasks}
    dependents: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for dependency in task.depends_on:
            if dependency not in by_id:
                raise TaskGraphError(
                    f"Task {task.task_id} depends on unknown task {dependency}"
                )
            if dependency == task.task_id:
                raise TaskGraphError(f"Task {task.task_id} cannot depend on itself")
            indegree[task.task_id] += 1
            dependents[dependency].append(task.task_id)

    ready = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while ready:
        task_id = ready.popleft()
        ordered.append(task_id)
        for child in sorted(dependents[task_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)

    if len(ordered) != len(tasks):
        raise TaskGraphError("Task graph contains a dependency cycle")
    return ordered


def ready_tasks(tasks: list[TaskBrief], succeeded: set[str]) -> list[TaskBrief]:
    validate_task_graph(tasks)
    return [
        task
        for task in tasks
        if task.task_id not in succeeded and set(task.depends_on).issubset(succeeded)
    ]
