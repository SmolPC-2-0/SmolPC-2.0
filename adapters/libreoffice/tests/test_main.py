import pytest
from unittest import mock

# File: libre-writer/test_main.py

from main import (
    get_office_path,
    get_python_path,
    is_port_in_use,
    start_office,
    start_helper,
    start_mcp_server,
    main,
)


def test_get_office_path_windows(monkeypatch):
    """Test that get_office_path returns the correct LibreOffice/Collabora path on Windows when it exists."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    paths = [
        r"C:\Program Files\Collabora Office\program\soffice.exe",
        r"C:\Program Files (x86)\Collabora Office\program\soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
    ]
    # Only second path exists
    monkeypatch.setattr("os.path.exists", lambda p: p == paths[1])
    assert get_office_path() == paths[1]


def test_get_office_path_linux(monkeypatch):
    """Test that get_office_path returns the correct LibreOffice/Collabora path on Linux when it exists."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    paths = [
        "/usr/bin/coolwsd",
        "/usr/bin/collaboraoffice",
        "/opt/collaboraoffice/program/soffice",
        "/usr/lib/collaboraoffice/program/soffice",
    ]
    monkeypatch.setattr("os.path.exists", lambda p: p == paths[2])
    assert get_office_path() == paths[2]


def test_get_office_path_not_found(monkeypatch):
    """Test that get_office_path raises FileNotFoundError when no office installation is found."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr("os.path.exists", lambda p: False)
    with pytest.raises(FileNotFoundError):
        get_office_path()


def test_get_office_path_unsupported_os(monkeypatch):
    """Test that get_office_path raises OSError for unsupported operating systems like macOS."""
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    with pytest.raises(OSError):
        get_office_path()


def test_get_python_path_windows(monkeypatch):
    """Test that get_python_path returns the correct Python executable path from office installation on Windows."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    paths = [
        r"C:\Program Files\Collabora Office\program\python.exe",
        r"C:\Program Files (x86)\Collabora Office\program\python.exe",
        r"C:\Program Files\LibreOffice\program\python.exe",
    ]
    monkeypatch.setattr("os.path.exists", lambda p: p == paths[0])
    assert get_python_path() == paths[0]


def test_get_python_path_windows_fallback(monkeypatch):
    """Test that get_python_path falls back to system Python when office Python is not found on Windows."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr("os.path.exists", lambda p: False)
    monkeypatch.setattr("sys.executable", "/usr/bin/python3")
    assert get_python_path() == "/usr/bin/python3"


def test_get_python_path_linux(monkeypatch):
    """Test that get_python_path returns the system Python executable path on Linux."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("sys.executable", "/usr/bin/python3")
    assert get_python_path() == "/usr/bin/python3"


def test_is_port_in_use_true_false(monkeypatch):
    """Test that is_port_in_use correctly detects when a port is occupied or available."""

    # Simulate port in use
    class DummySocket:
        def __init__(self, *a, **kw):
            pass

        def connect_ex(self, addr) -> int:
            return 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("socket.socket", lambda *a, **kw: DummySocket())
    assert is_port_in_use(1234) is True

    # Simulate port not in use
    class DummySocket2(DummySocket):
        def connect_ex(self, addr) -> int:
            return 1

    monkeypatch.setattr("socket.socket", lambda *a, **kw: DummySocket2())
    assert is_port_in_use(1234) is False


def test_start_office(monkeypatch):
    """Test that start_office successfully launches LibreOffice when the port is available."""
    monkeypatch.setattr("main.is_port_in_use", lambda port: False)
    monkeypatch.setattr("main.get_office_path", lambda: "office_path")
    popen_mock = mock.Mock()
    monkeypatch.setattr("subprocess.Popen", popen_mock)
    monkeypatch.setattr("time.sleep", lambda x: None)
    start_office()
    popen_mock.assert_called_once()
    args = popen_mock.call_args[0][0]
    assert "office_path" in args


def test_start_office_already_running(monkeypatch, capsys):
    """Test that start_office skips launching when LibreOffice is already running on the socket."""
    monkeypatch.setattr("main.is_port_in_use", lambda port: True)
    start_office()
    captured = capsys.readouterr()
    assert "Office socket already running" in captured.err


def test_start_helper(monkeypatch):
    """Test that start_helper successfully launches the helper script when the port is available."""
    monkeypatch.setattr("main.is_port_in_use", lambda port: False)
    monkeypatch.setattr("main.get_python_path", lambda: "python_path")
    monkeypatch.setattr("os.path.dirname", lambda x: "/dir")
    monkeypatch.setattr("os.path.join", lambda *args: "/".join(args))
    popen_mock = mock.Mock()
    monkeypatch.setattr("subprocess.Popen", popen_mock)
    monkeypatch.setattr("time.sleep", lambda x: None)
    monkeypatch.setattr("sys.argv", ["main.py"])
    start_helper()
    popen_mock.assert_called_once()
    args = popen_mock.call_args[0][0]
    assert "python_path" in args
    assert "/dir/helper.py" in args


def test_start_helper_already_running(monkeypatch, capsys):
    """Test that start_helper skips launching when the helper script is already running on the port."""
    monkeypatch.setattr("main.is_port_in_use", lambda port: True)
    start_helper()
    captured = capsys.readouterr()
    assert "Helper script already running" in captured.err


def test_start_mcp_server(monkeypatch):
    """Test that start_mcp_server successfully executes the MCP server with correct arguments."""
    run_mock = mock.Mock()
    monkeypatch.setattr("subprocess.run", run_mock)
    monkeypatch.setattr("os.path.dirname", lambda x: "/dir")
    monkeypatch.setattr("os.path.join", lambda *args: "/".join(args))
    monkeypatch.setattr("sys.executable", "python_path")
    monkeypatch.setattr("main.__file__", "/dir/main.py")
    start_mcp_server()
    run_mock.assert_called_once()
    args = run_mock.call_args[0][0]
    assert "python_path" in args
    assert "/dir/libre.py" in args


def test_main_success(monkeypatch):
    """Test that main function executes successfully when all components start without errors."""
    monkeypatch.setattr("main.start_office", lambda: None)
    monkeypatch.setattr("main.start_helper", lambda: None)
    monkeypatch.setattr("main.start_mcp_server", lambda: None)
    main()  # Should not raise


def test_main_exception(monkeypatch):
    """Test that main function exits with code 1 when an exception occurs during startup."""
    monkeypatch.setattr(
        "main.start_office", lambda: (_ for _ in ()).throw(Exception("fail"))
    )
    exit_mock = mock.Mock()
    monkeypatch.setattr("sys.exit", exit_mock)
    main()
    exit_mock.assert_called_once_with(1)
