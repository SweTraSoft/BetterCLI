"""Distribution preflight must reject unsuitable signing material."""

import hashlib
import importlib.util
import plistlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "build_app_store",
    Path(__file__).resolve().parents[1] / "packaging" / "build_app_store.py",
)
assert spec is not None and spec.loader is not None
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)

CERTIFICATE = b"test distribution certificate"
CERTIFICATE_HASH = hashlib.sha1(CERTIFICATE).hexdigest().upper()


@pytest.fixture
def profile():
    return {
        "Platform": ["OSX"],
        "ExpirationDate": datetime.now(timezone.utc) + timedelta(days=30),
        "TeamIdentifier": ["TEAM123"],
        "ApplicationIdentifierPrefix": ["PREFIX123"],
        "DeveloperCertificates": [CERTIFICATE],
        "Entitlements": {
            "com.apple.application-identifier": "PREFIX123.com.swetrasoft.BetterCLI",
            "com.apple.developer.team-identifier": "TEAM123",
        },
    }


def test_distribution_entitlements(profile):
    entitlements = packaging.validate_profile(profile, "com.swetrasoft.BetterCLI", CERTIFICATE_HASH)
    assert entitlements == {
        "com.apple.application-identifier": "PREFIX123.com.swetrasoft.BetterCLI",
        "com.apple.developer.team-identifier": "TEAM123",
        "com.apple.security.app-sandbox": True,
        "com.apple.security.network.client": True,
        "com.apple.security.files.user-selected.read-write": True,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("Platform", ["iOS"], "macOS"),
        ("ExpirationDate", datetime(2000, 1, 1), "expired"),
        ("ExpirationDate", None, "expiration"),
        ("ProvisionedDevices", ["DEVICE"], "distribution profile"),
        ("ProvisionsAllDevices", True, "distribution profile"),
        ("TeamIdentifier", [], "one team"),
        ("DeveloperCertificates", [b"another certificate"], "not included"),
    ],
)
def test_rejects_unsuitable_profile(profile, field, value, message):
    profile[field] = value
    with pytest.raises(ValueError, match=message):
        packaging.validate_profile(profile, "com.swetrasoft.BetterCLI", CERTIFICATE_HASH)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("get-task-allow", True, "debugging"),
        ("com.apple.security.get-task-allow", True, "debugging"),
        ("com.apple.application-identifier", "PREFIX123.*", "explicitly match"),
        ("com.apple.developer.team-identifier", "OTHER", "team entitlement"),
    ],
)
def test_rejects_unsuitable_entitlements(profile, field, value, message):
    profile["Entitlements"][field] = value
    with pytest.raises(ValueError, match=message):
        packaging.validate_profile(profile, "com.swetrasoft.BetterCLI", CERTIFICATE_HASH)


def test_requires_unique_installed_identity():
    name = "Apple Distribution: Test (TEAM123)"
    installed = f'1) {CERTIFICATE_HASH} "{name}"'
    assert packaging.identity_hash(installed, name) == CERTIFICATE_HASH
    assert packaging.identity_hash(f"{installed}\n{installed}", name) == CERTIFICATE_HASH
    with pytest.raises(ValueError, match="found 0"):
        packaging.identity_hash("", name)
    with pytest.raises(ValueError, match="found 2"):
        packaging.identity_hash(f'{installed}\n2) {"A" * 40} "{name}"', name)


def test_signed_package_workflow(profile, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(packaging, "ROOT", tmp_path)
    monkeypatch.setattr(packaging.sys, "platform", "darwin")
    pyinstaller = tmp_path / ".venv" / "bin" / "pyinstaller"
    pyinstaller.parent.mkdir(parents=True)
    pyinstaller.touch()
    profile_path = tmp_path / "distribution.provisionprofile"
    profile["ExpirationDate"] = profile["ExpirationDate"].replace(tzinfo=None)
    profile_path.write_bytes(plistlib.dumps(profile))
    app_name = "Apple Distribution: Test (TEAM123)"
    installer_name = "3rd Party Mac Developer Installer: Test (TEAM123)"
    installer_hash = "A" * 40
    monkeypatch.setattr(
        packaging.sys, "argv",
        [
            "build_app_store.py", "--app-identity", app_name,
            "--installer-identity", installer_name,
            "--profile", str(profile_path), "--build-number", "7",
        ],
    )
    commands = []
    main_entitlements = {}

    def check_output(command, **kwargs):
        if command[:2] == ["security", "find-identity"]:
            return f'1) {CERTIFICATE_HASH} "{app_name}"\n2) {installer_hash} "{installer_name}"'
        if command[:2] == ["security", "cms"]:
            return profile_path.read_bytes()
        assert command[:2] == ["codesign", "--display"]
        assert "--xml" in command
        return plistlib.dumps(main_entitlements)

    def run(command, **kwargs):
        commands.append(command)
        assert kwargs["check"] is True
        if command[0] == str(pyinstaller):
            env = kwargs["env"]
            assert env["BETTERCLI_CODESIGN_IDENTITY"] == CERTIFICATE_HASH
            assert env["BETTERCLI_BUILD_NUMBER"] == "7"
            assert env["BETTERCLI_BUNDLE_ID"] == "com.swetrasoft.BetterCLI"
            assert env["PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR"] == "1"
            (tmp_path / "dist" / "app-store" / "7" / "BetterCLI.app" / "Contents").mkdir(parents=True)
        elif command[:2] == ["codesign", "--force"]:
            main_entitlements.update(plistlib.loads(Path(command[command.index("--entitlements") + 1]).read_bytes()))

    monkeypatch.setattr(packaging.subprocess, "check_output", check_output)
    monkeypatch.setattr(packaging.subprocess, "run", run)
    assert packaging.main() == 0
    app = tmp_path / "dist" / "app-store" / "7" / "BetterCLI.app"
    assert (app / "Contents" / "embedded.provisionprofile").read_bytes() == profile_path.read_bytes()
    assert main_entitlements["com.apple.security.app-sandbox"] is True
    assert "com.apple.security.inherit" not in main_entitlements
    assert commands[2] == ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)]
    assert commands[3] == [
        "productbuild", "--component", str(app), "/Applications",
        "--sign", installer_hash, str(app.parent / "BetterCLI-7.pkg"),
    ]
    assert commands[4][:2] == ["pkgutil", "--check-signature"]
    assert "Not yet Apple-validated" in capsys.readouterr().out
    with pytest.raises(SystemExit) as error:
        packaging.main()
    assert error.value.code == 2
    assert len(commands) == 5
