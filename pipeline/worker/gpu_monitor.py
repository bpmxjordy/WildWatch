from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_gpus() -> list[dict]:
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            cc_major, cc_minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            gpus.append({
                "device_index": i,
                "name": name,
                "total_memory_mb": mem.total // (1024 * 1024),
                "compute_capability": f"{cc_major}.{cc_minor}",
            })
        pynvml.nvmlShutdown()
        return gpus
    except Exception as e:
        logger.info("No NVIDIA GPUs detected: %s", e)
        return []


def get_gpu_stats() -> list[dict]:
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        stats = []
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            stats.append({
                "device_index": i,
                "memory_used_mb": mem.used // (1024 * 1024),
                "memory_free_mb": mem.free // (1024 * 1024),
                "memory_total_mb": mem.total // (1024 * 1024),
                "utilization_percent": util.gpu,
                "temperature_c": temp,
            })
        pynvml.nvmlShutdown()
        return stats
    except Exception:
        return []
