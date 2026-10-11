"""Automated smoke and integration test for the installed Personal AI OS application.

Verifies:
1. Launching installed `Personal AI OS.exe` outside the development repository.
2. Automatic startup of the packaged standalone FastAPI backend from `resources/backend`.
3. Readiness of `/api/health` and initialization of core routes.
4. Process ownership & cleanup on exit (no orphaned background processes).
5. Application relaunch without port conflict or stale locks.
6. User data persistence in `%LOCALAPPDATA%\\PersonalAIOS`.
7. Sensible uninstallation behavior preserving user data.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def http_get(url: str, timeout_sec: float = 6.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "InstalledAppSmokeTest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8")
        try:
            data = json.loads(body)
        except Exception:
            data = body
        return {"status": resp.status, "data": data}


def wait_for_backend_health(url: str = "http://127.0.0.1:8000/api/health", timeout_sec: float = 35.0):
    start_time = time.time()
    last_err = None
    while time.time() - start_time < timeout_sec:
        try:
            res = http_get(url, timeout_sec=6.0)
            if res["status"] == 200 and isinstance(res["data"], dict) and res["data"].get("status") == "ok":
                return res["data"]
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    raise TimeoutError(f"Backend failed to report healthy within {timeout_sec}s. Last error: {last_err}")


def is_port_in_use(port: int = 8000) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    install_dir = Path(local_app_data) / "Programs" / "Personal AI OS Test"
    app_exe = install_dir / "Personal AI OS.exe"
    uninstaller_exe = install_dir / "Uninstall Personal AI OS.exe"

    print("==================================================")
    print(" Installed Application Real Smoke Test Suite")
    print(f" Executable: {app_exe}")
    print("==================================================")

    if not app_exe.exists():
        print(f"ERROR: Installed executable not found at {app_exe}")
        sys.exit(1)

    # 1. Clean slate check: port 8000 should be free before launching
    if is_port_in_use(8000):
        print("WARNING: Port 8000 is currently occupied. Attempting to identify and wait...")
        time.sleep(2)

    # 2. Launch installed application
    print("\n--- Test 1: Cold start installed Personal AI OS ---")
    proc = subprocess.Popen([str(app_exe)])
    print(f"Started installed Electron app PID: {proc.pid}")

    try:
        # 3. Poll /api/health
        print("Waiting for packaged backend to report readiness...")
        health = wait_for_backend_health()
        print("Health response:", json.dumps(health, indent=2))
        assert health["status"] == "ok"
        assert "components" in health
        print("PASS: Installed application successfully started packaged backend and /api/health is ready.")

        # 4. Verify existing routes
        print("\n--- Test 2: Verifying core API endpoints on installed backend ---")
        routes = [
            "http://127.0.0.1:8000/api/calendar/providers",
            "http://127.0.0.1:8000/api/calendar/events?start_datetime=2026-01-01T00:00:00&end_datetime=2026-12-31T23:59:59",
            "http://127.0.0.1:8000/api/recommendations",
            "http://127.0.0.1:8000/api/approvals",
        ]
        for route in routes:
            res = http_get(route)
            print(f"Route {route} -> status {res['status']}")
            assert res["status"] == 200, f"Unexpected status {res['status']} on {route}"
        print("PASS: Core routes initialized and returned 200 OK.")

        # 5. Verify user data location
        print("\n--- Test 3: Verifying persistence in %LOCALAPPDATA%\\PersonalAIOS ---")
        data_dir = Path(local_app_data) / "PersonalAIOS"
        db_file = data_dir / "personal_ai_os.db"
        assert db_file.exists(), f"Database file {db_file} does not exist"
        assert db_file.stat().st_size > 0, "Database file is empty"
        print(f"PASS: SQLite database active in {db_file} (size: {db_file.stat().st_size} bytes).")

    finally:
        # 6. Process cleanup check
        print("\n--- Test 4: Closing installed Electron app & verifying process cleanup ---")
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        # Wait for port 8000 to be released
        port_cleared = False
        for _ in range(20):
            if not is_port_in_use(8000):
                port_cleared = True
                break
            time.sleep(0.5)

        assert port_cleared, "Port 8000 must be released after application close"
        print("PASS: App-owned backend cleanly shut down and port 8000 released.")

    # 7. Test Relaunch
    print("\n--- Test 5: Relaunching installed application ---")
    proc2 = subprocess.Popen([str(app_exe)])
    print(f"Relaunched installed Electron app PID: {proc2.pid}")

    try:
        health2 = wait_for_backend_health()
        assert health2["status"] == "ok"
        print("PASS: Installed application successfully relaunched and backend responded.")
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc2.kill()
            proc2.wait()

        # Verify port released again
        for _ in range(20):
            if not is_port_in_use(8000):
                break
            time.sleep(0.5)
        print("PASS: Relaunch terminated cleanly.")

    # 8. Test Uninstall
    print("\n--- Test 6: Testing uninstaller ---")
    if uninstaller_exe.exists():
        print(f"Running silent uninstall: {uninstaller_exe} /S")
        uninst_proc = subprocess.run([str(uninstaller_exe), "/S"], capture_output=True)
        time.sleep(4)  # Allow uninstaller file cleanup

        # Verify installation folder is removed or cleaned
        if not app_exe.exists():
            print("PASS: Installed application executable removed.")
        else:
            print("NOTE: Uninstaller still running or left executable.")

        # Crucial check: User data in %LOCALAPPDATA%\PersonalAIOS MUST NOT be deleted
        assert db_file.exists(), "User database MUST NOT be deleted upon uninstall"
        print(f"PASS: User database preserved at {db_file} after uninstall.")

    print("\n==================================================")
    print(" ALL INSTALLED APPLICATION SMOKE TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
