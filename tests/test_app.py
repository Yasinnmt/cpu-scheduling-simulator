"""Tests for the Streamlit input-parsing helpers (no browser needed)."""

import pandas as pd
import pytest

from app import build_config, parse_processes, parse_quantums
from cpu_scheduler.models.config import MLFQConfig
from cpu_scheduler.models.process import Process
from cpu_scheduler.validation.validators import ValidationError


def _table(pid, arrival, burst, priority) -> pd.DataFrame:
    return pd.DataFrame(
        {"pid": pid, "arrival_time": arrival, "burst_time": burst, "priority": priority}
    )


class TestParseProcesses:
    def test_valid_rows(self):
        table = _table(["P1", "P2"], [0, 2], [6, 2], [2, 1])
        assert parse_processes(table) == [Process("P1", 0, 6, 2), Process("P2", 2, 2, 1)]

    def test_missing_priority_defaults_to_zero(self):
        table = _table(["P1"], [0], [3], [None])
        assert parse_processes(table) == [Process("P1", 0, 3, 0)]

    def test_whole_floats_accepted(self):
        table = _table(["P1"], [0.0], [3.0], [1.0])
        assert parse_processes(table) == [Process("P1", 0, 3, 1)]

    def test_pid_whitespace_stripped(self):
        table = _table(["  P1 "], [0], [3], [0])
        assert parse_processes(table) == [Process("P1", 0, 3, 0)]

    def test_empty_pid_rejected(self):
        table = _table([" "], [0], [3], [0])
        with pytest.raises(ValidationError, match="pid"):
            parse_processes(table)

    def test_missing_pid_rejected(self):
        table = _table([None], [0], [3], [0])
        with pytest.raises(ValidationError, match="pid"):
            parse_processes(table)

    def test_fractional_burst_rejected(self):
        table = _table(["P1"], [0], [2.5], [0])
        with pytest.raises(ValidationError, match="whole number"):
            parse_processes(table)

    def test_missing_arrival_rejected(self):
        table = _table(["P1"], [None], [3], [0])
        with pytest.raises(ValidationError, match="arrival_time"):
            parse_processes(table)

    def test_non_numeric_burst_rejected(self):
        table = _table(["P1"], [0], ["abc"], [0])
        with pytest.raises(ValidationError, match="burst_time"):
            parse_processes(table)

    def test_empty_table_returns_empty_list(self):
        assert parse_processes(_table([], [], [], [])) == []


class TestParseQuantums:
    def test_multiple_levels(self):
        assert parse_quantums("2, 4, 8") == (2, 4, 8)

    def test_single_level(self):
        assert parse_quantums(" 3 ") == (3,)

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="at least one"):
            parse_quantums("  , ")

    def test_non_integer_rejected(self):
        with pytest.raises(ValidationError, match="not an integer"):
            parse_quantums("2, x")

    def test_zero_rejected(self):
        with pytest.raises(ValidationError, match=">= 1"):
            parse_quantums("2, 0")


class TestBuildConfig:
    def test_zero_aging_disables(self):
        config = build_config(1, 2, 0, (2, 4), 20)
        assert config.aging_interval is None
        assert config.context_switch_cost == 1
        assert config.time_quantum == 2
        assert config.mlfq == MLFQConfig(quantums=(2, 4), boost_interval=20)

    def test_positive_aging_kept(self):
        config = build_config(0, 3, 5, (2,), 10)
        assert config.aging_interval == 5