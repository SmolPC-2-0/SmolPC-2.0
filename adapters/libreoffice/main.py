#!/usr/bin/env python3
import os
import sys
import subprocess
import socket
import time
import platform
import signal
import atexit

# Global variables to track child processes
office_process = None
helper_process = None


def cleanup_processes():
    """Clean up all child processes when the main process exits"""
    global office_process, helper_process

    print("Cleaning up processes...", file=sys.stderr)

    if helper_process and helper_process.poll() is None:
        print("Terminating helper process...", file=sys.stderr)
        helper_process.terminate()
        try:
            helper_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            helper_process.kill()

    if office_process and office_process.poll() is None:
        print("Terminating office process...", file=sys.stderr)
        office_process.terminate()
        try:
            office_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            office_process.kill()


def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals"""
    print("\nReceived interrupt signal. Shutting down...", file=sys.stderr)
    cleanup_processes()
    sys.exit(0)


def get_office_path():
    """Get the Collabora Office or LibreOffice executable path based on the operating system"""
    system = platform.system().lower()
    if system == "windows":
        # Windows paths
        possible_paths = [
            r"C:\Program Files\Collabora Office\program\soffice.exe",
            r"C:\Program Files (x86)\Collabora Office\program\soffice.exe",
            r"C:\Program Files\LibreOffice\program\soffice.exe",  # Fallback to LibreOffice
        ]
    elif system == "linux":
        # Linux paths - Collabora Office is typically installed in these locations
        possible_paths = [
            "/usr/bin/coolwsd",  # Collabora Online WebSocket Daemon
            "/usr/bin/collaboraoffice",  # Collabora Office main executable
            "/opt/collaboraoffice/program/soffice",
            "/usr/lib/collaboraoffice/program/soffice",
            # # Fallback to standard LibreOffice paths
            # '/usr/bin/soffice',
            # '/usr/lib/libreoffice/program/soffice',
            # '/opt/libreoffice/program/soffice'
        ]
    else:
        raise OSError(f"Unsupported operating system: {system}")

    for path in possible_paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "Neither Collabora Office nor LibreOffice executable found. Please install either office suite."
    )


def get_python_path():
    """Get the Python executable path based on the operating system"""
    system = platform.system().lower()
    if system == "windows":
        possible_paths = [
            r"C:\Program Files\Collabora Office\program\python.exe",
            r"C:\Program Files (x86)\Collabora Office\program\python.exe",
            r"C:\Program Files\LibreOffice\program\python.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return sys.executable  # Fallback to system Python
    else:
        return sys.executable  # Use the current Python interpreter on Linux


def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def start_office(port=2002):
    """Start Collabora Office in headless mode with socket"""
    global office_process

    if not is_port_in_use(port):
        print("Starting Collabora Office with socket...", file=sys.stderr)
        soffice_path = get_office_path()
        office_process = subprocess.Popen(
            [
                soffice_path,
                "-env:UserInstallation=file:///C:/Temp/LibreOfficeHeadlessProfile",
                "--headless",
                f"--accept=socket,host=localhost,port={port};urp;",
                "--norestore",
                "--nodefault",
                "--nologo",
            ]
        )
        time.sleep(3)  # Give it time to start
    else:
        print(f"Office socket already running on port {port}", file=sys.stderr)


def start_helper():
    """Start the Office helper script"""
    global helper_process

    if not is_port_in_use(8765):
        print("Starting Office helper...", file=sys.stderr)
        exe_dir = os.path.dirname(sys.argv[0])
        helper_script = os.path.join(exe_dir, "helper.py")
        python_path = get_python_path()
        helper_process = subprocess.Popen([python_path, helper_script])
        time.sleep(3)
    else:
        print("Helper script already running on port 8765", file=sys.stderr)


def start_mcp_server():
    """Start the MCP server"""
    print("Starting Office MCP server...", file=sys.stderr)
    server_script = os.path.join(os.path.dirname(__file__), "libre.py")

    subprocess.run(
        [
            sys.executable,  # Use the same Python interpreter
            server_script,
        ]
    )


def main():
    # Register cleanup function to run when the program exits
    atexit.register(cleanup_processes)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    if platform.system() != "Windows":
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    try:
        start_office()
        start_helper()
        start_mcp_server()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...", file=sys.stderr)
        cleanup_processes()
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        cleanup_processes()
        sys.exit(1)


if __name__ == "__main__":
    main()
