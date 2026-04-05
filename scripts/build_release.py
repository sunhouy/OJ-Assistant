#!/usr/bin/env python3
"""Cross-platform release packaging for OJAssistant."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from textwrap import dedent

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "OJAssistant"
ENTRY_SCRIPT = ROOT_DIR / "OJAssistant" / "main.py"
INNO_SETUP_SCRIPT = ROOT_DIR / "innosetup.iss"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
TEMP_PACKAGE_DIR = ROOT_DIR / "package-temp"

EXTENSION_SOURCE_DIR = ROOT_DIR / "OJAssistant" / "chrome" / "chrome"
APP_ICON_SOURCE = ROOT_DIR / "OJAssistant" / "app.png"
GUI_ICON_SOURCE = ROOT_DIR / "OJAssistant" / "gui" / "app.png"
WINDOWS_ICON_SOURCE = ROOT_DIR / "app.ico"


class BuildError(RuntimeError):
    """Raised when packaging cannot continue."""


def run_cmd(cmd: list[str], cwd: Path = ROOT_DIR) -> None:
    printable = " ".join(str(part) for part in cmd)
    print(f"$ {printable}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def safe_version(version: str) -> str:
    cleaned = []
    for ch in version.strip():
        if ch.isalnum() or ch in ".-_":
            cleaned.append(ch)
        else:
            cleaned.append("-")
    return "".join(cleaned) or "local"


def normalized_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64", "x64"}:
        return "x64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine or "unknown"


def pyinstaller_data_arg(src: Path, dst: str) -> str:
    separator = ";" if platform.system() == "Windows" else ":"
    return f"{src}{separator}{dst}"


def ensure_required_files() -> None:
    required = [
        ENTRY_SCRIPT,
        EXTENSION_SOURCE_DIR,
        APP_ICON_SOURCE,
        GUI_ICON_SOURCE,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        missing_str = ", ".join(str(path) for path in missing)
        raise BuildError(f"Missing required files/directories: {missing_str}")


def clean_previous_outputs() -> None:
    for path in [DIST_DIR, BUILD_DIR, ARTIFACTS_DIR, TEMP_PACKAGE_DIR, ROOT_DIR / "Output"]:
        if path.exists():
            shutil.rmtree(path)
    spec_file = ROOT_DIR / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()


def build_binary() -> None:
    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_SCRIPT),
        "--name",
        APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--paths",
        str(ROOT_DIR / "OJAssistant"),
        "--collect-submodules",
        "gui",
        "--collect-submodules",
        "core",
        "--collect-submodules",
        "utils",
        "--add-data",
        pyinstaller_data_arg(EXTENSION_SOURCE_DIR, "chrome/chrome"),
        "--add-data",
        pyinstaller_data_arg(APP_ICON_SOURCE, "app.png"),
        "--add-data",
        pyinstaller_data_arg(GUI_ICON_SOURCE, "gui/app.png"),
    ]

    current_system = platform.system()
    if current_system == "Darwin":
        # macOS installer packaging expects an app bundle.
        pass
    else:
        cmd.append("--onefile")

    if current_system == "Windows" and WINDOWS_ICON_SOURCE.exists():
        cmd.extend(["--icon", str(WINDOWS_ICON_SOURCE)])

    run_cmd(cmd)


def add_directory_to_zip(archive: zipfile.ZipFile, source_dir: Path, archive_prefix: str) -> None:
    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            rel = file_path.relative_to(source_dir).as_posix()
            archive.write(file_path, arcname=f"{archive_prefix}/{rel}")


def copy_common_runtime_files(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP_ICON_SOURCE, target_dir / "app.png")

    extension_target = target_dir / "chrome" / "chrome"
    extension_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(EXTENSION_SOURCE_DIR, extension_target, dirs_exist_ok=True)


def find_iscc_executable() -> Path:
    candidates = [
        Path(r"C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path(r"C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise BuildError("ISCC.exe not found. Install Inno Setup first.")


def package_windows(version: str) -> list[Path]:
    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise BuildError(f"Expected binary not found: {exe_path}")

    copy_common_runtime_files(DIST_DIR)

    arch = normalized_arch()
    safe_ver = safe_version(version)
    portable_zip = ARTIFACTS_DIR / f"{APP_NAME}-{safe_ver}-windows-{arch}-portable.zip"
    installer_name = f"{APP_NAME}-{safe_ver}-windows-{arch}-setup"

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT_DIR / "Output"
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(portable_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(exe_path, arcname=f"{APP_NAME}.exe")
        archive.write(DIST_DIR / "app.png", arcname="app.png")
        add_directory_to_zip(archive, EXTENSION_SOURCE_DIR, "chrome/chrome")

    app_version = version[1:] if version.startswith("v") else version
    iscc = find_iscc_executable()
    run_cmd(
        [
            str(iscc),
            str(INNO_SETUP_SCRIPT),
            f"/DMyAppVersion={app_version}",
            f"/DMyAppExeName={APP_NAME}.exe",
            f"/DMyOutputDir={output_dir}",
            f"/DMyOutputBaseFilename={installer_name}",
        ]
    )

    installer_path = output_dir / f"{installer_name}.exe"
    if not installer_path.exists():
        raise BuildError(f"Expected installer not found: {installer_path}")

    final_installer = ARTIFACTS_DIR / installer_path.name
    shutil.copy2(installer_path, final_installer)

    return [portable_zip, final_installer]


def package_linux(version: str) -> list[Path]:
    binary_path = DIST_DIR / APP_NAME
    if not binary_path.exists():
        raise BuildError(f"Expected binary not found: {binary_path}")

    arch = normalized_arch()
    safe_ver = safe_version(version)
    root_name = f"{APP_NAME}-{safe_ver}-linux-{arch}"
    package_root = TEMP_PACKAGE_DIR / root_name

    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)

    shutil.copy2(binary_path, package_root / APP_NAME)
    os.chmod(package_root / APP_NAME, 0o755)

    copy_common_runtime_files(package_root)

    install_script = package_root / "install.sh"
    uninstall_script = package_root / "uninstall.sh"

    install_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail

            APP_NAME=\"{APP_NAME}\"
            INSTALL_ROOT=\"$HOME/.local/share/$APP_NAME\"
            BIN_DIR=\"$HOME/.local/bin\"
            DESKTOP_DIR=\"$HOME/.local/share/applications\"
            SRC_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"

            mkdir -p \"$INSTALL_ROOT\" \"$BIN_DIR\" \"$DESKTOP_DIR\"
            rm -rf \"$INSTALL_ROOT/chrome\"
            rm -f \"$INSTALL_ROOT/$APP_NAME\"
            cp -r \"$SRC_DIR/$APP_NAME\" \"$INSTALL_ROOT/$APP_NAME\"
            cp -r \"$SRC_DIR/chrome\" \"$INSTALL_ROOT/chrome\"
            cp \"$SRC_DIR/app.png\" \"$INSTALL_ROOT/app.png\"
            ln -sf \"$INSTALL_ROOT/$APP_NAME\" \"$BIN_DIR/$APP_NAME\"

            cat > \"$DESKTOP_DIR/$APP_NAME.desktop\" <<EOF
            [Desktop Entry]
            Name={APP_NAME}
            Exec=$BIN_DIR/$APP_NAME
            Icon=$INSTALL_ROOT/app.png
            Type=Application
            Terminal=false
            Categories=Utility;
            EOF

            echo \"Installed to $INSTALL_ROOT\"
            echo \"Launch with: $APP_NAME\"
            """
        ),
        encoding="utf-8",
    )
    os.chmod(install_script, 0o755)

    uninstall_script.write_text(
        dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail

            APP_NAME=\"{APP_NAME}\"
            INSTALL_ROOT=\"$HOME/.local/share/$APP_NAME\"
            BIN_LINK=\"$HOME/.local/bin/$APP_NAME\"
            DESKTOP_FILE=\"$HOME/.local/share/applications/$APP_NAME.desktop\"

            rm -rf \"$INSTALL_ROOT\"
            rm -f \"$BIN_LINK\" \"$DESKTOP_FILE\"

            echo \"Removed $APP_NAME\"
            """
        ),
        encoding="utf-8",
    )
    os.chmod(uninstall_script, 0o755)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = ARTIFACTS_DIR / f"{root_name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(package_root, arcname=root_name)

    return [tar_path]


def package_macos(version: str) -> list[Path]:
    app_bundle = DIST_DIR / f"{APP_NAME}.app"
    if not app_bundle.exists():
        raise BuildError(f"Expected app bundle not found: {app_bundle}")

    arch = normalized_arch()
    safe_ver = safe_version(version)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    dmg_path = ARTIFACTS_DIR / f"{APP_NAME}-{safe_ver}-macos-{arch}.dmg"
    zip_path = ARTIFACTS_DIR / f"{APP_NAME}-{safe_ver}-macos-{arch}.zip"

    run_cmd(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(app_bundle),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )

    run_cmd(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(app_bundle),
            str(zip_path),
        ]
    )

    return [dmg_path, zip_path]


def package_current_platform(version: str) -> list[Path]:
    current_system = platform.system()
    if current_system == "Windows":
        return package_windows(version)
    if current_system == "Linux":
        return package_linux(version)
    if current_system == "Darwin":
        return package_macos(version)
    raise BuildError(f"Unsupported platform: {current_system}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and package release artifacts.")
    parser.add_argument(
        "--version",
        default="local",
        help="Release version used in artifact names, e.g. v1.2.3",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not remove previous build outputs before packaging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        ensure_required_files()
        if not args.no_clean:
            clean_previous_outputs()
        build_binary()
        artifacts = package_current_platform(args.version)
    except (BuildError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1

    print("Generated artifacts:")
    for artifact in artifacts:
        print(f"- {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
