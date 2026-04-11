#!/usr/bin/env python3
import os
import argparse
import sys

# Approximate bytes per parameter for different quantization types
KV_CACHE_TYPES = {"fp16": 2.0, "q8_0": 1.06, "q5_0": 0.69, "q4_0": 0.56, "q4_k": 0.59}

# Standard architectures for popular model sizes
MODEL_ARCHITECTURES = {
    "8b": {"layers": 32, "kv_heads": 8, "head_dim": 128, "n_heads": 32},
    "14b": {"layers": 40, "kv_heads": 40, "head_dim": 128, "n_heads": 40},
    "32b": {"layers": 64, "kv_heads": 8, "head_dim": 128, "n_heads": 32},
    "70b": {"layers": 80, "kv_heads": 8, "head_dim": 128, "n_heads": 64},
}


def calculate_max_context(
    model_size_gb: float,
    gpu_memory_gb: float,
    model_class: str = "8b",
    kv_type: str = "fp16",
    flash_attention: bool = True,
    cuda_buffer_gb: float = 0.6,
) -> int:
    """Calculates the maximum context size that can fit in VRAM."""
    if kv_type.lower() not in KV_CACHE_TYPES:
        raise ValueError(
            f"Unsupported KV type. Choose from: {list(KV_CACHE_TYPES.keys())}"
        )
    if model_class.lower() not in MODEL_ARCHITECTURES:
        raise ValueError(
            f"Unsupported model class. Choose from: {list(MODEL_ARCHITECTURES.keys())}"
        )

    gb_to_bytes = 1024**3
    total_vram = gpu_memory_gb * gb_to_bytes
    model_vram = model_size_gb * gb_to_bytes
    buffer_vram = cuda_buffer_gb * gb_to_bytes

    available_vram = total_vram - model_vram - buffer_vram

    if available_vram <= 0:
        return 0

    arch = MODEL_ARCHITECTURES[model_class.lower()]
    bytes_per_element = KV_CACHE_TYPES[kv_type.lower()]

    kv_bytes_per_token = (
        2 * arch["layers"] * arch["kv_heads"] * arch["head_dim"] * bytes_per_element
    )

    low = 0
    high = 1_000_000
    best_context = 0

    while low <= high:
        mid = (low + high) // 2
        kv_vram_needed = mid * kv_bytes_per_token

        if flash_attention:
            compute_buffer = mid * 256
        else:
            compute_buffer = (mid**2) * arch["n_heads"] * 2

        total_needed = kv_vram_needed + compute_buffer

        if total_needed <= available_vram:
            best_context = mid
            low = mid + 1
        else:
            high = mid - 1

    return (best_context // 128) * 128


def parse_env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val else default


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate maximum context size for LLMs based on hardware and quantization.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Positional arguments with environment variable fallbacks
    parser.add_argument(
        "model_size_gb",
        type=float,
        nargs="?",
        default=parse_env_float("MODEL_SIZE_GB", 0.0),
        help="Size of the model weights in GB (Env: MODEL_SIZE_GB)",
    )
    parser.add_argument(
        "gpu_memory_gb",
        type=float,
        nargs="?",
        default=parse_env_float("GPU_MEMORY_GB", 0.0),
        help="Total GPU memory in GB (Env: GPU_MEMORY_GB)",
    )
    parser.add_argument(
        "model_class",
        type=str,
        nargs="?",
        default=os.environ.get("MODEL_CLASS", "8b"),
        help="Model architecture class, e.g., 8b, 14b, 70b (Env: MODEL_CLASS)",
    )

    # Optional flags
    parser.add_argument(
        "--kv-type",
        type=str,
        default=os.environ.get("KV_TYPE", "fp16"),
        choices=list(KV_CACHE_TYPES.keys()),
        help="KV Cache quantization type (Env: KV_TYPE)",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=parse_env_float("CUDA_BUFFER_GB", 0.6),
        help="CUDA safety buffer in GB (Env: CUDA_BUFFER_GB)",
    )

    # Handle Flash Attention boolean via env or flag
    env_fa = os.environ.get("FLASH_ATTENTION", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    parser.add_argument(
        "--no-flash-attn",
        action="store_false",
        dest="flash_attention",
        default=env_fa,
        help="Disable Flash Attention scaling (Env: FLASH_ATTENTION=false)",
    )

    args = parser.parse_args()

    # Enforce required parameters if not supplied via CLI or Env
    if args.model_size_gb == 0.0 or args.gpu_memory_gb == 0.0:
        print(
            "Error: You must provide 'model_size_gb' and 'gpu_memory_gb' either as arguments or environment variables.\n"
        )
        parser.print_help()
        sys.exit(1)

    # Calculate and output
    try:
        ctx = calculate_max_context(
            args.model_size_gb,
            args.gpu_memory_gb,
            args.model_class,
            kv_type=args.kv_type,
            flash_attention=args.flash_attention,
            cuda_buffer_gb=args.buffer,
        )

        print("\n--- Context Calculation ---")
        print(f"Model Size:      {args.model_size_gb} GB")
        print(f"GPU Memory:      {args.gpu_memory_gb} GB")
        print(f"Model Class:     {args.model_class.upper()}")
        print(f"KV Cache Type:   {args.kv_type.upper()}")
        print(f"Flash Attention: {'ON' if args.flash_attention else 'OFF'}")
        print(f"Safety Buffer:   {args.buffer} GB")
        print("-" * 27)
        print(f"MAX CONTEXT:     {ctx:,} tokens\n")

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
