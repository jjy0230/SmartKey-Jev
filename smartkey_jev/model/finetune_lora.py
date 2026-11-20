"""
AnyJev QLoRA Fine-Tuning Pipeline for Lightweight SLMs (Qwen2.5-1.5B / SmolLM2-1.7B).
Configured for sub-2B parameter models with 4-bit quantization and LoRA adapters.
"""

import os
import argparse
from typing import Dict, Any


def print_training_recipe(model_name: str, dataset_path: str, output_dir: str):
    """
    Prints standard execution recipe and hyperparameter configuration
    for training AnyJev on consumer hardware (single RTX 3060/4060+ with 8GB-12GB VRAM).
    """
    print("=" * 76)
    print("  SmartKey-Jev: AnyJev LoRA Fine-Tuning Recipe")
    print("=" * 76)
    print(f"Base Model:       {model_name}")
    print(f"Dataset Path:     {dataset_path}")
    print(f"Output Directory: {output_dir}")
    print("-" * 76)
    print("Recommended Hyperparameters:")
    print("  • Quantization:       4-bit NormalFloat (NF4) with Double Quantization")
    print("  • LoRA Rank (r):      16")
    print("  • LoRA Alpha:         32")
    print("  • Target Modules:     q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj")
    print("  • Learning Rate:      2e-4 (Cosine decay)")
    print("  • Batch Size:         4 per device with Gradient Accumulation = 4 (Effective = 16)")
    print("  • Max Sequence Len:   512 tokens (Sufficient for 300-char snippets + context)")
    print("  • Epochs:             3")
    print("-" * 76)
    print("Launch Command (via unsloth / huggingface peft):")
    print(f"  python -m smartkey_jev.model.finetune_lora --model {model_name} --data {dataset_path}")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="AnyJev Model Training Orchestrator")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct", help="Base model identifier")
    parser.add_argument("--data", type=str, default="data/train_intent.jsonl", help="Input dataset path")
    parser.add_argument("--output", type=str, default="models/anyjev-1.5b-lora", help="Output directory")
    args = parser.parse_args()

    print_training_recipe(args.model, args.data, args.output)


if __name__ == "__main__":
    main()
