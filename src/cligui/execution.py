"""Runs the assembled command through QProcess with live output and cancel.

The program and its arguments are always passed separately so no shell is ever
involved in execution.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from cligui.discovery.runner import clean_text

#: Grace period before a cancelled process is killed outright.
KILL_AFTER_MS = 3000


class CommandRunner(QObject):
    started = Signal(str)
    output = Signal(str)
    failed = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._cancelled = False

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def start(self, argv: list[str], cwd: str | None = None) -> None:
        if self.running:
            raise RuntimeError("a command is already running")
        if not argv:
            raise ValueError("nothing to run")

        self._cancelled = False
        process = QProcess(self)
        process.setProgram(argv[0])
        process.setArguments(argv[1:])
        process.setProcessChannelMode(QProcess.MergedChannels)
        if cwd:
            process.setWorkingDirectory(cwd)

        env = QProcessEnvironment.systemEnvironment()
        # Keep child output unbuffered and plain so it streams readably.
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("TERM", "dumb")
        env.insert("NO_COLOR", "1")
        env.insert("PAGER", "cat")
        process.setProcessEnvironment(env)

        process.readyReadStandardOutput.connect(self._drain)
        process.errorOccurred.connect(self._on_error)
        process.finished.connect(self._on_finished)

        self._process = process
        process.start()
        self.started.emit(argv[0])

    def cancel(self) -> None:
        if not self.running or self._process is None:
            return
        self._cancelled = True
        self._process.terminate()
        if not self._process.waitForFinished(KILL_AFTER_MS):
            self._process.kill()

    def _drain(self) -> None:
        if self._process is None:
            return
        raw = bytes(self._process.readAllStandardOutput()).decode("utf-8", "replace")
        if raw:
            self.output.emit(clean_text(raw))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if self._cancelled and error is QProcess.Crashed:
            return
        messages = {
            QProcess.FailedToStart: "The command could not be started.",
            QProcess.Crashed: "The command crashed.",
            QProcess.Timedout: "The command timed out.",
            QProcess.WriteError: "Could not write to the command.",
            QProcess.ReadError: "Could not read from the command.",
        }
        self.failed.emit(messages.get(error, "The command failed for an unknown reason."))
        # Qt never emits finished() when a process fails to start, so close the
        # cycle here or the UI would stay stuck in the "running" state.
        if error is QProcess.FailedToStart:
            self._process = None
            self.finished.emit(127)

    def _on_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        self._drain()
        self._process = None
        if self._cancelled:
            self.finished.emit(-1)
        elif status is QProcess.CrashExit:
            self.finished.emit(code if code else 1)
        else:
            self.finished.emit(code)
