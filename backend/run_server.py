"""Executable entry point for the standalone Personal AI OS backend server.

Supports PyInstaller frozen binary execution with multiprocessing.freeze_support(),
CLI argument parsing, and uvicorn server execution.
"""

import argparse
import multiprocessing
import os
import sys


def main():
    # Required for Windows executables using multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Personal AI OS Standalone Backend Server")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host address to bind")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")), help="Port to bind")
    parser.add_argument("--data-dir", default=None, help="Custom writable application data directory")
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "info"), help="Logging verbosity level")
    args = parser.parse_args()

    if args.data_dir:
        os.environ["PERSONAL_AI_DATA_DIR"] = os.path.abspath(args.data_dir)

    # Import uvicorn and app after setting any environment variables
    import uvicorn
    from app.main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
