from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from cligui import execution
from cligui.discovery.runner import DiscoveryError


@pytest.fixture
def application():
    return QApplication.instance() or QApplication([])


def test_execution_uses_resolved_program_without_changing_arguments(application, monkeypatch):
    calls = []

    def resolve(name):
        calls.append(name)
        return Path("/usr/bin/printf")

    monkeypatch.setattr(execution, "resolve_binary", resolve)
    runner = execution.CommandRunner()
    output = QSignalSpy(runner.output)
    finished = QSignalSpy(runner.finished)
    started = QSignalSpy(runner.started)
    argv = ["git", "%s", "argument with spaces"]

    runner.start(argv)

    assert runner._process.program() == "/usr/bin/printf"
    assert runner._process.arguments() == ["%s", "argument with spaces"]
    assert finished.wait(5000)
    assert finished.at(0) == [0]
    assert "".join(output.at(index)[0] for index in range(output.count())) == "argument with spaces"
    assert started.at(0) == ["/usr/bin/printf"]
    assert calls == ["git"]
    assert argv == ["git", "%s", "argument with spaces"]


def test_resolution_failure_does_not_start_process(application, monkeypatch):
    def fail(_name):
        raise DiscoveryError("No active developer directory")

    monkeypatch.setattr(execution, "resolve_binary", fail)
    runner = execution.CommandRunner()
    started = QSignalSpy(runner.started)

    with pytest.raises(RuntimeError, match="No active developer directory"):
        runner.start(["make"])

    assert not runner.running
    assert runner._process is None
    assert started.count() == 0
