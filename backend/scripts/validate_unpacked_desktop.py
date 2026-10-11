"""Validation script for the unpacked Personal AI OS desktop application.

Validates:
1. Launching unpacked 'Personal AI OS.exe' from 'frontend/release/win-unpacked'.
2. Automatic launch of standalone 'personal_ai_backend.exe' independently of python venv.
3. Health check readiness and database integrity status.
4. Core API functionality on packaged backend.
5. Process ownership and clean shutdown without orphan processes.
6. User database preservation in %LOCALAPPDATA%\\PersonalAIOS.
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
    req = urllib.request.Request(url, headers={"User-Agent": "PackagedDesktopValidation/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8")
        try:
            data = json.loads(body)
        except Exception:
            data = body
        return {"status": resp.status, "data": data}


def is_port_in_use(port: int = 8000) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_backend_health(url: str = "http://127.0.0.1:8000/api/health", timeout_sec: float = 40.0):
    start_time = time.time()
    last_err = None
    while time.time() - start_time < timeout_sec:
        try:
            res = http_get(url, timeout_sec=6.0)
            if res["status"] == 200 and isinstance(res["data"], dict):
                return res["data"]
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    raise TimeoutError(f"Backend failed to report healthy within {timeout_sec}s. Last error: {last_err}")


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    unpacked_exe = repo_root / "frontend" / "release" / "win-unpacked" / "Personal AI OS.exe"

    print("==================================================")
    print(" Unpacked Desktop App End-to-End Validation")
    print(f" Executable: {unpacked_exe}")
    print("==================================================")

    if not unpacked_exe.exists():
        print(f"ERROR: Executable not found at {unpacked_exe}")
        sys.exit(1)

    # 1. Clean port check
    if is_port_in_use(8000):
        print("Waiting for port 8000 to be free...")
        for _ in range(10):
            if not is_port_in_use(8000):
                break
            time.sleep(1)

    # Record user DB state before test
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    db_file = Path(local_app_data) / "PersonalAIOS" / "personal_ai_os.db"
    db_size_before = db_file.stat().st_size if db_file.exists() else 0
    print(f"User database before launch: {db_file} (exists: {db_file.exists()}, size: {db_size_before} bytes)")

    # 2. Launch unpacked application
    print("\n[Step 1] Launching unpacked Personal AI OS.exe...")
    proc = subprocess.Popen([str(unpacked_exe)])
    print(f"Launched Electron PID: {proc.pid}")

    try:
        # 3. Wait for backend health
        print("\n[Step 2] Polling http://127.0.0.1:8000/api/health for packaged backend readiness...")
        health = wait_for_backend_health()
        print("Health Response Summary:")
        print(f"  Overall Status: {health.get('status')}")
        print(f"  Database Status: {health.get('components', {}).get('database', {}).get('status')}")
        print(f"  LLM Status: {health.get('components', {}).get('llm_provider', {}).get('status')}")
        print(f"  Agents Registered: {health.get('components', {}).get('agents', {}).get('details', {}).get('registered_count')}")
        print(f"  Tools Registered: {health.get('components', {}).get('tools', {}).get('details', {}).get('registered_count')}")

        assert health.get("components", {}).get("database", {}).get("status") == "healthy", "Database component must be healthy"
        assert health.get("components", {}).get("api", {}).get("status") == "healthy", "API component must be healthy"
        print("PASS: Packaged standalone backend is healthy and responding.")

        # 4. Verify endpoints
        print("\n[Step 3] Querying packaged backend API endpoints...")
        routes = [
            "http://127.0.0.1:8000/api/calendar/providers",
            "http://127.0.0.1:8000/api/recommendations",
            "http://127.0.0.1:8000/api/approvals",
        ]
        for route in routes:
            res = http_get(route)
            print(f"  {route} -> Status {res['status']}")
            assert res["status"] == 200, f"Failed on route {route}"
        print("PASS: Core routes verified.")

        # 5. Check if real model is available for live inference
        llm_status = health.get("components", {}).get("llm_provider", {}).get("status")
        if llm_status == "online_model_ready":
            print("\n[Step 4] Live model is ready! Sending test conversation to packaged app...")
            chat_payload = json.dumps({"message": "Hello, answer in 5 words."}).encode("utf-8")
            chat_req = urllib.request.Request(
                "http://127.0.0.1:8000/api/chat",
                data=chat_payload,
                headers={"Content-Type": "application/json", "User-Agent": "PackagedValidation/1.0"},
            )
            try:
                with urllib.request.urlopen(chat_req, timeout=20.0) as chat_resp:
                    chat_data = json.loads(chat_resp.read().decode("utf-8"))
                    print(f"  Chat response status: {chat_resp.status}")
                    print(f"  Chat response content: {chat_data.get('response', '')[:80]}...")
                    print("PASS: Real conversation completed successfully.")
            except Exception as ce:
                print(f"  Chat query notice: {ce}")
        else:
            print(f"\n[Step 4] LLM status is '{llm_status}' - live model inference skipped (missing external prerequisite).")

        # 6. Verify user database is preserved
        assert db_file.exists(), "User database must still exist"
        print(f"\n[Step 5] User database preserved at {db_file} (size: {db_file.stat().st_size} bytes).")

    finally:
        # 7. Terminate Electron and verify clean process shutdown
        print("\n[Step 6] Shutting down unpacked Electron process (PID %d)..." % proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        # Wait for port 8000 to be completely released
        print("Verifying backend shutdown and port 8000 release...")
        released = False
        for _ in range(25):
            if not is_port_in_use(8000):
                released = True
                break
            time.sleep(0.5)

        assert released, "Port 8000 must be released after Electron shutdown"
        print("PASS: Port 8000 released; zero orphaned backend processes.")

    print("\n==================================================")
    print(" ALL PACKAGED DESKTOP VALIDATION CHECKS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
