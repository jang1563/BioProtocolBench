"""Backward-compatible scorer exports for LabCraft."""

from .trajectory_scorer import build_transform_trajectory_scorer


def protocol_error_scorer(*args, **kwargs):
    """Compatibility alias while the project transitions from ProtocolErrorBench."""
    return build_transform_trajectory_scorer()
