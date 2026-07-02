"""Renderer-facing structures used by the prototype scene."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DrawableMesh:
    id: int
    layer: int
    verts: tuple
    color: tuple
    active: bool = True
    opacity: float = 1.0
    debug: bool = False

