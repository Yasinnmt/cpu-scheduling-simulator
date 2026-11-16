import pytest

from cpu_scheduler.core.context_switch import ContextSwitchManager


@pytest.mark.parametrize("cost,previous,next_pid,expected", [
    (1, None, "P1", False),
    (1, "P1", "P1", False),
    (1, "P1", "P2", True),
    (0, "P1", "P2", False),
    (3, "P1", "P2", True),
])
def test_needs_switch(cost, previous, next_pid, expected):
    assert ContextSwitchManager(cost).needs_switch(previous, next_pid) is expected