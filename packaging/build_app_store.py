"""Build a signed Mac App Store candidate; Apple validation is a separate step."""

from __future__ import annotations

import argparse
import hashlib
import os
import plistlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def validate_profile(
    profile: dict, bundle_id: str, certificate_hash: str
) -> dict:
    if profile.get("Platform") != ["OSX"]:
        raise ValueError("The provisioning profile must be for macOS.")
    expiration = profile.get("ExpirationDate")
    if not isinstance(expiration, datetime):
        raise ValueError("The provisioning profile has no valid expiration date.")
    if expiration.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError("The provisioning profile has expired.")
    if profile.get("ProvisionedDevices") or profile.get("ProvisionsAllDevices"):
        raise ValueError("Use a Mac App Store distribution profile, not a development or Developer ID profile.")
    entitlements = profile.get("Entitlements", {})
    if entitlements.get("get-task-allow") or entitlements.get("com.apple.security.get-task-allow"):
        raise ValueError("The provisioning profile permits debugging; use a distribution profile.")
    teams = profile.get("TeamIdentifier", [])
    prefixes = profile.get("ApplicationIdentifierPrefix", [])
    if len(teams) != 1 or len(prefixes) != 1:
        raise ValueError("The provisioning profile must identify one team and app prefix.")
    app_id = f"{prefixes[0]}.{bundle_id}"
    if entitlements.get("com.apple.application-identifier") != app_id:
        raise ValueError(f"The profile must explicitly match {app_id}.")
    if entitlements.get("com.apple.developer.team-identifier") != teams[0]:
        raise ValueError("The provisioning profile's team entitlement does not match its team.")
    certificates = profile.get("DeveloperCertificates", [])
    if not any(hashlib.sha1(cert).hexdigest().upper() == certificate_hash for cert in certificates):
        raise ValueError("The selected app signing certificate is not included in the profile.")
    return {
        "com.apple.application-identifier": app_id,
        "com.apple.developer.team-identifier": teams[0],
        "com.apple.security.app-sandbox": True,
        "com.apple.security.network.client": True,
        "com.apple.security.files.user-selected.read-write": True,
    }


def identity_hash(identities: str, name: str) -> str:
    matches = sorted(set(re.findall(r'([0-9A-F]{40}) "' + re.escape(name) + r'"', identities)))
    if len(matches) != 1:
        raise ValueError(f"Expected one valid identity with private key named {name!r}; found {len(matches)}.")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-identity", required=True, help="Full Apple Distribution or 3rd Party Mac Developer Application identity name.")
    parser.add_argument("--installer-identity", required=True, help="Full 3rd Party Mac Developer Installer identity name.")
    parser.add_argument("--profile", type=Path, required=True, help="Mac App Store distribution .provisionprofile.")
    parser.add_argument("--bundle-id", default="com.swetrasoft.BetterCLI")
    parser.add_argument("--build-number", type=int, required=True)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("Mac App Store packaging requires macOS.")
    if args.build_number < 1:
        parser.error("--build-number must be a positive integer.")
    if not args.app_identity.startswith(("Apple Distribution: ", "3rd Party Mac Developer Application: ")):
        parser.error("Use an App Store app distribution identity, not Apple Development or Developer ID.")
    if not args.installer_identity.startswith("3rd Party Mac Developer Installer: "):
        parser.error("Use a Mac Installer Distribution identity, not Developer ID Installer.")
    if not args.profile.is_file():
        parser.error(f"Provisioning profile not found: {args.profile}")
    if not (ROOT / ".venv" / "bin" / "pyinstaller").is_file():
        parser.error("PyInstaller is missing. Run uv sync first.")

    identities = subprocess.check_output(["security", "find-identity", "-v"], text=True)
    try:
        app_hash = identity_hash(identities, args.app_identity)
        installer_hash = identity_hash(identities, args.installer_identity)
        profile_data = subprocess.check_output(["security", "cms", "-D", "-i", str(args.profile.resolve())])
        entitlements = validate_profile(plistlib.loads(profile_data), args.bundle_id, app_hash)
        team = entitlements["com.apple.developer.team-identifier"]
        if not args.installer_identity.endswith(f"({team})"):
            raise ValueError("The installer signing identity must belong to the provisioning profile's team.")
    except (ValueError, plistlib.InvalidFileException) as exc:
        parser.error(str(exc))

    destination = ROOT / "dist" / "app-store" / str(args.build_number)
    if destination.exists():
        parser.error(f"Output already exists: {destination}. Use a new build number or move the previous output.")
    destination.mkdir(parents=True)
    app = destination / "BetterCLI.app"
    package = destination / f"BetterCLI-{args.build_number}.pkg"

    with tempfile.TemporaryDirectory(prefix="bettercli-app-store-") as temporary:
        main_entitlements = Path(temporary) / "app.entitlements"
        main_entitlements.write_bytes(plistlib.dumps(entitlements))
        env = {
            **os.environ,
            "BETTERCLI_CODESIGN_IDENTITY": app_hash,
            "BETTERCLI_ENTITLEMENTS_FILE": str(ROOT / "packaging" / "app-store-child.entitlements"),
            "BETTERCLI_BUNDLE_ID": args.bundle_id,
            "BETTERCLI_BUILD_NUMBER": str(args.build_number),
            "PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR": "1",
        }
        subprocess.run(
            [
                str(ROOT / ".venv" / "bin" / "pyinstaller"),
                "--clean",
                "--distpath", str(destination),
                "--workpath", str(Path(temporary) / "build"),
                str(ROOT / "packaging" / "cligui.spec"),
            ],
            cwd=ROOT, env=env, check=True,
        )
        (app / "Contents" / "embedded.provisionprofile").write_bytes(args.profile.read_bytes())
        # PyInstaller signs nested code with inheritance; the main app needs its own sandbox.
        subprocess.run(
            [
                "codesign", "--force", "--sign", app_hash,
                "--entitlements", str(main_entitlements), str(app),
            ],
            check=True,
        )
        subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)], check=True)
        signed = plistlib.loads(subprocess.check_output(["codesign", "--display", "--entitlements", "-", "--xml", str(app)]))
        if signed != entitlements:
            raise ValueError("The signed app's entitlements do not match the requested entitlements.")
        subprocess.run(
            ["productbuild", "--component", str(app), "/Applications", "--sign", installer_hash, str(package)],
            check=True,
        )
        subprocess.run(["pkgutil", "--check-signature", str(package)], check=True)

    print(f"Signed candidate: {package}")
    print("Not yet Apple-validated. Test sandbox compatibility and validate with Transporter before submission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
