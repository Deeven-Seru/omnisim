#!/usr/bin/env bash
# OmniSim Blackwell / Hopper GPU Accelerated Launch Script
# Automates CUDA environment verification, FP8 compilation paths, and Marimo execution.

set -euo pipefail

echo "=========================================================="
echo "⚡ OmniSim: NVIDIA Blackwell / GPU Accelerated Harness"
echo "=========================================================="

# Check NVIDIA GPU Presence
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
    echo "✔ GPU Detected: ${GPU_NAME}"
    echo "✔ Enabling CUDA FP8 Tensor Core Execution..."
    export OMNISIM_DEVICE="cuda"
    export TORCH_CUDA_ARCH_LIST="9.0;10.0" # Hopper & Blackwell architectures
else
    echo "ℹ NVIDIA GPU not detected. Falling back to Apple Silicon MPS / Vectorized CPU execution."
    export OMNISIM_DEVICE="mps"
fi

# Install dependencies if uv is present
if command -v uv &> /dev/null; then
    echo "✔ Syncing dependencies via uv..."
    uv pip install -e ".[all]"
fi

echo "=========================================================="
echo "Starting OmniSim Reactive Marimo Dashboard..."
echo "=========================================================="
marimo edit notebooks/interactive.py
