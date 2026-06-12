"""ERP prompt templates (loaded from .txt files in this directory)."""

import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by filename (with or without .txt suffix)."""
    if not name.endswith(".txt"):
        name = f"{name}.txt"
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


__all__ = ["load_prompt", "PROMPTS_DIR"]
