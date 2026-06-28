"""Unit tests for the system info collector."""

from __future__ import annotations

import os
import platform
import socket
import subprocess as real_subprocess
from unittest.mock import MagicMock, patch

import psutil
import pytest

from llm_race.utils.system import SystemInfo, get_system_info


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_platform():
    """Mock platform module functions."""
    with (
        patch.object(platform, "system", return_value="Linux"),
        patch.object(platform, "release", return_value="5.15.0"),
        patch.object(platform, "version", return_value="#1 SMP"),
        patch.object(platform, "processor", return_value="x86_64"),
        patch.object(platform, "machine", return_value="x86_64"),
        patch.object(platform, "python_version", return_value="3.11.0"),
    ):
        yield


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for GPU detection."""
    with patch("llm_race.utils.system.subprocess", create=True) as mock:
        yield mock


@pytest.fixture
def mock_socket():
    """Mock socket functions."""
    with (
        patch.object(socket, "gethostname", return_value="test-machine"),
        patch.object(socket, "gethostbyname", return_value="192.168.1.1"),
    ):
        yield


@pytest.fixture
def mock_psutil():
    """Mock psutil.virtual_memory."""
    mock_vmem = MagicMock()
    mock_vmem.total = 17179869184  # 16 GB
    mock_vmem.available = 8589934592  # 8 GB
    with patch.object(psutil, "virtual_memory", return_value=mock_vmem):
        yield


# ---------------------------------------------------------------------------
# Test: _get_os_info
# ---------------------------------------------------------------------------

def test_get_os_info(mock_platform) -> None:
    """Test that _get_os_info returns correct OS platform data."""
    from llm_race.utils.system import _get_os_info

    info = _get_os_info()
    assert info["os"] == "Linux"
    assert info["os_kernel"] == "5.15.0"
    assert info["os_version"] == "#1 SMP"
    assert info["python_version"] == "3.11.0"


def test_get_cpu_info() -> None:
    """Test that _get_cpu_info returns correct CPU data (cores, arch)."""
    from llm_race.utils.system import _get_cpu_info
    import os

    with (
        patch.object(platform, "processor", return_value="arm64"),
        patch.object(platform, "machine", return_value="arm64"),
        patch.object(os, "cpu_count", return_value=8),
    ):
        info = _get_cpu_info()
        assert info["cpu"] == "arm64"
        assert info["cpu_cores"] == 8
        assert info["cpu_threads"] == 8
        assert info["cpu_architecture"] == "arm64"


def test_get_ram_info(mock_psutil) -> None:
    """Test that _get_ram_info returns correct RAM totals."""
    from llm_race.utils.system import _get_ram_info

    info = _get_ram_info()
    assert info["ram_total_gb"] == 16.0
    assert info["ram_available_gb"] == 8.0


def test_get_network_info(mock_socket) -> None:
    """Test that _get_network_info returns hostname and IP."""
    from llm_race.utils.system import _get_network_info

    info = _get_network_info()
    assert info["hostname"] == "test-machine"
    assert info["ip_local"] == "192.168.1.1"


def test_get_gpu_info_nvidia(mock_subprocess) -> None:
    """Test GPU detection via nvidia-smi."""
    from llm_race.utils.system import _get_gpu_info

    mock_run = MagicMock()
    mock_run.stdout = "NVIDIA A100 80GB PCIe, 12.0, 81250 MiB\n"
    mock_run.returncode = 0

    mock_cuda_run = MagicMock()
    mock_cuda_run.stdout = '<?xml><nvidia_smi_log><cuda_version>12.2</cuda_version></nvidia_smi_log>'
    mock_cuda_run.returncode = 0

    mock_subprocess.run.side_effect = [mock_run, mock_cuda_run]

    info = _get_gpu_info()
    assert info["gpu"] == "NVIDIA NVIDIA A100 80GB PCIe"
    assert info["gpu_count"] == 1
    assert info["gpu_driver_version"] == "12.0"
    assert info["gpu_cuda_version"] == "12.2"


def test_get_gpu_info_apple(mock_subprocess) -> None:
    """Test GPU detection via system_profiler (Apple Silicon)."""
    from llm_race.utils.system import _get_gpu_info

    mock_apple_run = MagicMock()
    mock_apple_run.stdout = """
Graphics/Displays:

    Apple M3 Max:
      Chipset Model: Apple M3 Max
      VRAM (Total): 49152 MB
"""
    mock_apple_run.returncode = 0

    mock_subprocess.run.side_effect = [
        real_subprocess.CalledProcessError(127, "nvidia-smi"),
        real_subprocess.CalledProcessError(127, "rocm-smi"),
        mock_apple_run,
    ]

    info = _get_gpu_info()
    assert info["gpu"] == "Apple M3 Max"
    assert info["gpu_count"] == 1
    assert info["gpu_vram_gb"] == 48.0


def test_get_gpu_info_no_gpu(mock_subprocess) -> None:
    """Test graceful fallback when no GPU tool is available."""
    from llm_race.utils.system import _get_gpu_info

    mock_subprocess.run.side_effect = [
        FileNotFoundError(),
        FileNotFoundError(),
        FileNotFoundError(),
    ]

    info = _get_gpu_info()
    assert info["gpu"] is None
    assert info["gpu_count"] is None
    assert info["gpu_driver_version"] is None
    assert info["gpu_cuda_version"] is None
    assert info["gpu_vram_gb"] is None


def test_collect_system_info(
    mock_platform, mock_subprocess, mock_socket, mock_psutil
) -> None:
    """Test that collect_system_info assembles all data correctly."""
    from llm_race.utils.system import collect_system_info, _cached_info
    import llm_race.utils.system as sys_mod

    sys_mod._cached_info = None

    mock_run = MagicMock()
    mock_run.stdout = "A100, 12.0, 81250 MiB\n"
    mock_run.returncode = 0
    mock_cuda_run = MagicMock()
    mock_cuda_run.stdout = '<xml><cuda_version>12.2</cuda_version></xml>'
    mock_cuda_run.returncode = 0
    mock_subprocess.run.side_effect = [mock_run, mock_cuda_run]

    with patch.object(os, "cpu_count", return_value=8):
        info = collect_system_info()
        assert info.hostname == "test-machine"
        assert info.os == "Linux"
        assert info.cpu_cores == 8
        assert info.ram_total_gb == 16.0
        assert info.ip_local == "192.168.1.1"


def test_get_system_info_cache() -> None:
    """Test that get_system_info returns cached value on repeated call."""
    from llm_race.utils.system import get_system_info, _cached_info
    import llm_race.utils.system as sys_mod

    sys_mod._cached_info = None

    a = get_system_info(force=True)
    b = get_system_info()
    assert a is b


def test_get_system_info_force() -> None:
    """Test that force=True causes re-collection."""
    from llm_race.utils.system import get_system_info, _cached_info
    import llm_race.utils.system as sys_mod

    sys_mod._cached_info = None

    a = get_system_info(force=True)
    b = get_system_info(force=True)
    assert a is not b