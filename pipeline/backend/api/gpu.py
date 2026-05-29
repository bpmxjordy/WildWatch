from flask import Blueprint, jsonify

from extensions import db
from models.gpu import GPUDevice

gpu_bp = Blueprint("gpu", __name__, url_prefix="/api/v1/gpu")


@gpu_bp.route("", methods=["GET"])
def list_gpus():
    gpus = GPUDevice.query.order_by(GPUDevice.device_index).all()

    runtime_stats = []
    try:
        import pynvml
        pynvml.nvmlInit()
        for gpu in gpus:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu.device_index)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            runtime_stats.append({
                **gpu.to_dict(),
                "memory_used_mb": mem_info.used // (1024 * 1024),
                "memory_free_mb": mem_info.free // (1024 * 1024),
                "utilization_percent": util.gpu,
                "temperature_c": temp,
            })
        pynvml.nvmlShutdown()
    except Exception:
        runtime_stats = [gpu.to_dict() for gpu in gpus]

    return jsonify({"gpus": runtime_stats})


@gpu_bp.route("/predict", methods=["GET"])
def predict_memory():
    from models.ml_model import MLModel
    from models.stream import Stream

    models = MLModel.query.all()
    active_model_ids = set(
        s.model_id for s in Stream.query.filter(Stream.is_active.is_(True)).all()
        if s.model_id
    )

    model_usage = []
    total_predicted = 300  # base CUDA context overhead

    for m in models:
        is_active = m.id in active_model_ids
        mem = m.gpu_memory_mb or 0
        if is_active:
            total_predicted += mem
        model_usage.append({
            "model_id": str(m.id),
            "name": m.name,
            "framework": m.framework,
            "gpu_memory_mb": mem,
            "is_active": is_active,
        })

    gpus = GPUDevice.query.all()
    total_vram = sum(g.total_memory_mb for g in gpus)

    return jsonify({
        "models": model_usage,
        "total_predicted_mb": total_predicted,
        "total_vram_mb": total_vram,
        "cuda_overhead_mb": 300,
        "fits": total_predicted <= total_vram * 0.95 if total_vram > 0 else False,
    })
