"""Automated standalone backend build script for Windows Personal AI OS."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_dir_size(path: Path) -> int:
    """Calculate total byte size of a directory."""
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total


def build():
    backend_dir = Path(__file__).resolve().parent.parent
    dist_dir = backend_dir / "dist"
    build_dir = backend_dir / "build"
    spec_file = backend_dir / "personal_ai_backend.spec"

    print("==================================================")
    print(" Building Personal AI OS Standalone Backend")
    print(f" Working directory: {backend_dir}")
    print(f" Spec file: {spec_file}")
    print("==================================================")

    # 1. Clean previous dist/build if present
    for d in [build_dir, dist_dir]:
        if d.exists():
            print(f"Cleaning previous directory: {d}...")
            shutil.rmtree(d, ignore_errors=True)

    # 2. Locate python / pyinstaller
    venv_pyinstaller = backend_dir / ".venv" / "Scripts" / "pyinstaller.exe"
    cmd = [
        str(venv_pyinstaller) if venv_pyinstaller.exists() else "pyinstaller",
        "--noconfirm",
        "--clean",
        str(spec_file),
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(backend_dir))
    if result.returncode != 0:
        print(f"ERROR: PyInstaller build failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    # 3. Verify output
    out_exe = dist_dir / "personal_ai_backend" / "personal_ai_backend.exe"
    if not out_exe.exists():
        print(f"ERROR: Expected executable not found at {out_exe}", file=sys.stderr)
        sys.exit(1)

    total_size = get_dir_size(dist_dir / "personal_ai_backend")
    exe_size = out_exe.stat().st_size

    print("\n==================================================")
    print(" Standalone Build Complete Successfully!")
    print(f" Output executable: {out_exe}")
    print(f" Executable binary size: {exe_size / (1024 * 1024):.2f} MB")
    print(f" Complete bundle size : {total_size / (1024 * 1024):.2f} MB")
    print("==================================================")


if __name__ == "__main__":
    build()
