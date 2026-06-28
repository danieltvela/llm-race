"""System information collector for benchmark metadata.

Collects OS, CPU, GPU, RAM, and network information for machine
identification and benchmark reproducibility.

Note on WSL/containers: platform detection may report the host OS
rather than the container OS. Verify results if running in containers.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import socket
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

import psutil

logger = logging.getLogger(__name__)

__all__ = ["SystemInfo", "SystemInfoError", "collect_system_info", "get_system_info"]


class SystemInfoError(Exception):
    """Raised when system info collection fails unexpectedly."""
    pass


@dataclass
class SystemInfo:
    hostname: str
    cpu: str
    cpu_cores: int
    cpu_threads: int
    cpu_architecture: str
    gpu: str | None
    gpu_count: int | None
    gpu_driver_version: str | None
    gpu_cuda_version: str | None
    gpu_vram_gb: float | None
    ram_total_gb: float
    ram_available_gb: float
    os: str
    os_version: str
    os_kernel: str
    python_version: str
    ip_local: str

    def to_dict(self) -> dict[str, Any]:
        """Return dict with keys matching Machine model fields."""
        d = asdict(self)
        # Map to Machine model field names
        return {
            "hostname": d["hostname"],
            "cpu": d["cpu"],
            "gpu": d["gpu"],
            "gpu_count": d["gpu_count"],
            "ram_gb": d["ram_total_gb"],
            "os": d["os"],
            "os_version": d["os_version"],
            "driver_version": d["gpu_driver_version"],
            "python_version": d["python_version"],
        }


def _get_os_info() -> dict[str, str]:
    """Collect OS platform information."""
    system_name = platform.system() or "Unknown"
    release = platform.release() or "Unknown"
    version = platform.version() or "Unknown"
    # On macOS, platform.version() returns the kernel version, not the macOS version
    # platform.mac_ver() returns (release, versioninfo, machine)
    if system_name == "Darwin":
        mac_ver = platform.mac_ver()[0]
        if mac_ver:
            version = mac_ver
    return {
        "os": system_name,
        "os_version": version,
        "os_kernel": release,
        "python_version": platform.python_version(),
    }


def _get_cpu_info() -> dict[str, str | int]:
    """Collect CPU information."""
    processor = platform.processor() or platform.machine() or "Unknown"
    machine = platform.machine() or "Unknown"
    cpu_count = os.cpu_count() or 0

    return {
        "cpu": processor,
        "cpu_cores": cpu_count,
        "cpu_threads": cpu_count,
        "cpu_architecture": machine,
    }


def _get_ram_info() -> dict[str, float]:
    """Collect RAM information using psutil."""
    mem = psutil.virtual_memory()
    total_gb = round(mem.total / (1024 ** 3), 2)
    available_gb = round(mem.available / (1024 ** 3), 2)
    return {
        "ram_total_gb": total_gb,
        "ram_available_gb": available_gb,
    }


def _get_network_info() -> dict[str, str]:
    """Collect network/hostname information."""
    hostname = socket.gethostname()
    try:
        ip_local = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip_local = "127.0.0.1"
        logger.debug("Could not resolve hostname to IP, using 127.0.0.1")
    return {
        "hostname": hostname,
        "ip_local": ip_local,
    }


def _get_gpu_info() -> dict[str, Any]:
    """Detect GPU information. Tries NVIDIA → AMD → Apple Silicon → None."""
    result = {
        "gpu": None,
        "gpu_count": None,
        "gpu_driver_version": None,
        "gpu_cuda_version": None,
        "gpu_vram_gb": None,
    }

    # 1. Try NVIDIA
    try:
        gpu_info = _get_nvidia_gpu_info()
        if gpu_info is not None:
            result.update(gpu_info)
            logger.debug("GPU detected via nvidia-smi: %s", result["gpu"])
            return result
    except Exception:
        logger.debug("NVIDIA detection failed", exc_info=True)

    # 2. Try AMD
    try:
        gpu_info = _get_amd_gpu_info()
        if gpu_info is not None:
            result.update(gpu_info)
            logger.debug("GPU detected via rocm-smi: %s", result["gpu"])
            return result
    except Exception:
        logger.debug("AMD detection failed", exc_info=True)

    # 3. Try Apple Silicon
    try:
        gpu_info = _get_apple_gpu_info()
        if gpu_info is not None:
            result.update(gpu_info)
            logger.debug("GPU detected via system_profiler: %s", result["gpu"])
            return result
    except Exception:
        logger.debug("Apple Silicon detection failed", exc_info=True)

    logger.debug("No GPU detection method succeeded")
    return result


def _get_nvidia_gpu_info() -> dict[str, Any] | None:
    """Detect NVIDIA GPU via nvidia-smi."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        lines = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip()]
        if not lines:
            return None

        gpu_count = len(lines)
        first_line = lines[0]
        parts = [p.strip() for p in first_line.split(",")]

        name = parts[0] if len(parts) > 0 else "Unknown NVIDIA GPU"
        driver = parts[1] if len(parts) > 1 else None
        vram_mib_str = parts[2] if len(parts) > 2 else None

        vram_gb = None
        if vram_mib_str:
            try:
                vram_mib = float(vram_mib_str.replace(" MiB", "").strip())
                vram_gb = round(vram_mib / 1024, 1)
            except (ValueError, AttributeError):
                pass

        # Try to get CUDA version
        cuda_version = None
        try:
            cuda_proc = subprocess.run(
                ["nvidia-smi", "--query", "--xml-format"],
                capture_output=True, text=True, timeout=5,
            )
            if cuda_proc.returncode == 0:
                match = re.search(r'<cuda_version>([^<]+)</cuda_version>', cuda_proc.stdout)
                if match:
                    cuda_version = match.group(1).strip()
        except Exception:
            pass

        return {
            "gpu": f"NVIDIA {name}",
            "gpu_count": gpu_count,
            "gpu_driver_version": driver,
            "gpu_cuda_version": cuda_version,
            "gpu_vram_gb": vram_gb,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def _get_amd_gpu_info() -> dict[str, Any] | None:
    """Detect AMD GPU via rocm-smi."""
    try:
        proc = subprocess.run(
            ["rocm-smi", "--showproductname", "--showdrive", "--showmeminfo", "vram"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        output = proc.stdout

        # Parse key=value style output from rocm-smi
        name_match = re.search(r'Product Name\s*:\s*(.+)', output)
        driver_match = re.search(r'Driver version\s*:\s*(.+)', output)
        vram_match = re.search(r'VRAM Size\s*:\s*(\d+)\s*MB', output, re.IGNORECASE)

        name = name_match.group(1).strip() if name_match else None
        driver = driver_match.group(1).strip() if driver_match else None

        vram_gb = None
        if vram_match:
            vram_mb = float(vram_match.group(1))
            vram_gb = round(vram_mb / 1024, 1)

        if name is None:
            return None

        return {
            "gpu": f"AMD {name}",
            "gpu_count": 1,
            "gpu_driver_version": driver,
            "gpu_cuda_version": None,  # CUDA is NVIDIA only
            "gpu_vram_gb": vram_gb,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def _get_apple_gpu_info() -> dict[str, Any] | None:
    """Detect Apple Silicon GPU via system_profiler."""
    try:
        proc = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        output = proc.stdout

        name_match = re.search(r'Chipset Model:\s*(.+)', output)
        vram_match = re.search(r'VRAM \(Total\):\s*(\d+)\s*MB', output)

        name = name_match.group(1).strip() if name_match else None

        vram_gb = None
        if vram_match:
            vram_mb = float(vram_match.group(1))
            vram_gb = round(vram_mb / 1024, 1)

        if name is None:
            return None

        # Strip leading "Apple" from name if present (chipset model may include it)
        clean_name = name.removeprefix("Apple ").removeprefix("Apple")
        return {
            "gpu": f"Apple {clean_name}".strip() if clean_name else None,
            "gpu_count": 1,
            "gpu_driver_version": None,  # Not easily available via system_profiler
            "gpu_cuda_version": None,
            "gpu_vram_gb": vram_gb,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


_cached_info: SystemInfo | None = None


def get_system_info(force: bool = False) -> SystemInfo:
    """Return cached system info or collect fresh.

    Args:
        force: If True, re-collect system info even if cached.
    """
    global _cached_info
    if force or _cached_info is None:
        _cached_info = collect_system_info()
    return _cached_info


def collect_system_info() -> SystemInfo:
    """Collect all system information and return a SystemInfo instance.

    Raises:
        SystemInfoError: If collection fails unexpectedly.
    """
    global _cached_info
    try:
        os_info = _get_os_info()
        cpu_info = _get_cpu_info()
        ram_info = _get_ram_info()
        network_info = _get_network_info()
        gpu_info = _get_gpu_info()

        info = SystemInfo(
            hostname=network_info["hostname"],
            cpu=str(cpu_info["cpu"]),
            cpu_cores=int(cpu_info["cpu_cores"]),
            cpu_threads=int(cpu_info["cpu_threads"]),
            cpu_architecture=str(cpu_info["cpu_architecture"]),
            gpu=gpu_info["gpu"],
            gpu_count=gpu_info["gpu_count"],
            gpu_driver_version=gpu_info["gpu_driver_version"],
            gpu_cuda_version=gpu_info["gpu_cuda_version"],
            gpu_vram_gb=gpu_info["gpu_vram_gb"],
            ram_total_gb=ram_info["ram_total_gb"],
            ram_available_gb=ram_info["ram_available_gb"],
            os=os_info["os"],
            os_version=os_info["os_version"],
            os_kernel=os_info["os_kernel"],
            python_version=os_info["python_version"],
            ip_local=network_info["ip_local"],
        )
        _cached_info = info
        logger.info("System info collected: %s / %s / %s cores", info.hostname, info.os, info.cpu_cores)
        return info
    except Exception as exc:
        raise SystemInfoError(f"Failed to collect system info: {exc}") from exc