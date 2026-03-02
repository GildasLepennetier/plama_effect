"""
Pure rendering core for plasma effect (no Pygame dependencies).
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, Dict


@dataclass(frozen=True)
class Palette:
    """Color palette definition."""
    offsets: np.ndarray  # RGB offsets for cosine coloring
    tint: np.ndarray  # Tint for specular effect
    name: str


# Palette definitions
PALETTES = {
    "warm": Palette(
        offsets=np.array([0.2, 0.5, 0.9], dtype=np.float32),
        tint=np.array([1.0, 0.7, 0.4], dtype=np.float32),
        name="warm",
    ),
    "cool": Palette(
        offsets=np.array([0.3, 0.6, 0.95], dtype=np.float32),
        tint=np.array([0.4, 0.7, 1.0], dtype=np.float32),
        name="cool",
    ),
    "lava": Palette(
        offsets=np.array([0.1, 0.4, 0.85], dtype=np.float32),
        tint=np.array([1.0, 0.3, 0.1], dtype=np.float32),
        name="lava",
    ),
    "neon": Palette(
        offsets=np.array([0.25, 0.55, 1.0], dtype=np.float32),
        tint=np.array([0.0, 1.0, 1.0], dtype=np.float32),
        name="neon",
    ),
}


def phase_default(t, uv):
    """Default phase algorithm: radial + sinusoidal."""
    phase_v = 0.1 + np.cos(uv[..., 1] + np.sin(0.148 - t)) + 2.4 * t
    phase_h = 0.9 + np.sin(uv[..., 0] + np.cos(0.628 + t)) - 0.7 * t
    return phase_v, phase_h


def phase_spiral(t, uv):
    """Spiral phase pattern."""
    phase_v = 0.2 + np.sin(uv[..., 1] * 2.0 + t * 0.5) + t
    phase_h = 0.8 + np.cos(uv[..., 0] * 2.0 - t * 0.5) + t * 1.5
    return phase_v, phase_h


def phase_pulsing(t, uv):
    """Pulsing phase pattern."""
    pulse = np.sin(t) * 0.5 + 0.5
    phase_v = 0.1 + np.cos(uv[..., 1]) * pulse + t * 0.3
    phase_h = 0.9 + np.sin(uv[..., 0]) * pulse - t * 0.2
    return phase_v, phase_h


def phase_layered(t, uv):
    """Layered/interference phase pattern."""
    phase_v = 0.1 + np.cos(uv[..., 1] + t * 0.8) + np.sin(uv[..., 1] * 2.0 - t * 0.3)
    phase_h = 0.9 + np.sin(uv[..., 0] - t * 0.5) + np.cos(uv[..., 0] * 2.0 + t * 0.6)
    return phase_v, phase_h


PHASE_PRESETS = {
    "default": phase_default,
    "spiral": phase_spiral,
    "pulsing": phase_pulsing,
    "layered": phase_layered,
}


class PlasmaRenderer:
    """Pure plasma rendering engine (Pygame-independent)."""

    def __init__(self, width, height, scale, time_scale, specular, palette_name, phase_preset):
        self.width = width
        self.height = height
        self.scale = scale
        self.time_scale = time_scale
        self.specular = specular
        self.palette = PALETTES.get(palette_name, PALETTES["warm"])
        self.phase_func = PHASE_PRESETS.get(phase_preset, phase_default)

        self.i_resolution = np.array([width, height], dtype=np.float32)
        x = np.linspace(0, width, width, endpoint=False, dtype=np.float32)
        y = np.linspace(0, height, height, endpoint=False, dtype=np.float32)
        xv, yv = np.meshgrid(x, y)
        frag_coord = np.stack([xv, yv], axis=-1)
        aspect = np.array([self.i_resolution[0] / self.i_resolution[1], 1.0], dtype=np.float32)
        self.uv_base = self.scale * frag_coord / self.i_resolution * aspect * 4.0
        self.normal_z = np.full((height, width), 0.5 / self.i_resolution[1], dtype=np.float32)

    def render(self, t):
        """Render frame at time t."""
        uv = self.uv_base + t * self.time_scale

        phase_v, phase_h = self.phase_func(t, uv)
        radial = np.sqrt(uv[..., 0] ** 2 + uv[..., 1] ** 2)

        plasma = 7.0 * np.cos(radial + phase_h) * np.sin(phase_v + phase_h)
        frag_color = 0.5 + 0.5 * np.cos(plasma[..., None] + self.palette.offsets)

        if self.specular:
            frag_color = self._apply_specular(frag_color)

        return np.clip(frag_color * 255, 0, 255).astype(np.uint8)

    def _apply_specular(self, frag_color):
        """Apply specular lighting effect."""
        dfdx = np.gradient(frag_color, axis=1)
        dfdy = np.gradient(frag_color, axis=0)

        surface_normal = np.stack(
            [
                np.linalg.norm(dfdx, axis=-1),
                np.linalg.norm(dfdy, axis=-1),
                self.normal_z,
            ],
            axis=-1,
        )

        surface_normal /= np.linalg.norm(surface_normal, axis=-1, keepdims=True)
        spec = np.maximum(surface_normal[..., 2], 0.0) ** 2.0
        return frag_color * (self.palette.tint * spec[..., None] + 0.75)
