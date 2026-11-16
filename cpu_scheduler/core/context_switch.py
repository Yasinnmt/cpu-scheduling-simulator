"""Context-switch policy: overhead applies only between two different processes.

No switch is charged for idle -> first process, and no switch is charged when
the same process continues after a decision point.
"""


class ContextSwitchManager:
    def __init__(self, cost: int) -> None:
        self.cost = cost

    def needs_switch(self, previous_pid: str | None, next_pid: str) -> bool:
        return self.cost > 0 and previous_pid is not None and previous_pid != next_pid