from __future__ import annotations

import pytest

from cligui.safety import Severity, inspect, worst


class TestHighSeverity:
    @pytest.mark.parametrize(
        "argv",
        [
            ["rm", "-rf", "/"],
            ["rm", "-rf", "~"],
            ["rm", "--recursive", "--force", "/Users"],
            ["dd", "if=/dev/zero", "of=/dev/disk0"],
            ["mkfs.ext4", "/dev/sda1"],
            ["shutdown", "-h", "now"],
            ["sudo", "rm", "x"],
        ],
    )
    def test_flagged_high(self, argv):
        assert worst(inspect(argv)) is Severity.HIGH

    def test_absolute_path_to_binary_is_still_matched(self):
        assert worst(inspect(["/bin/dd", "if=/dev/zero"])) is Severity.HIGH

    def test_home_directory_target_is_high(self):
        assert worst(inspect(["rm", "-r", "~/"])) is Severity.HIGH


class TestCaution:
    def test_ordinary_recursive_delete_is_caution(self):
        assert worst(inspect(["rm", "-rf", "/tmp/scratch"])) is Severity.CAUTION

    def test_force_flag(self):
        findings = inspect(["git", "push", "--force"])
        assert worst(findings) is Severity.CAUTION
        assert "--force" in findings[0].title

    def test_recursive_chmod(self):
        assert worst(inspect(["chmod", "-R", "777", "/tmp/x"])) is Severity.CAUTION

    def test_duplicate_flags_reported_once(self):
        findings = inspect(["tool", "--force", "--force"])
        assert len(findings) == 1


class TestClean:
    @pytest.mark.parametrize(
        "argv",
        [
            ["ls", "-la"],
            ["git", "log", "--oneline"],
            ["curl", "https://example.com"],
            ["grep", "-r", "pattern", "src"],
            [],
        ],
    )
    def test_no_findings(self, argv):
        assert inspect(argv) == []

    def test_force_inside_a_value_is_not_flagged(self):
        assert inspect(["grep", "--pattern", "--force"]) != []

    def test_findings_are_sorted_worst_first(self):
        findings = inspect(["rm", "-rf", "/", "--force"])
        assert findings[0].severity is Severity.HIGH
