import pygame
import time
import os
import argparse
from dataclasses import dataclass
from dotenv import load_dotenv
from plasma_effect_render_core import PlasmaRenderer, PALETTES, PHASE_PRESETS

try:
    from plasma_effect_video_recorder import VideoRecorder  # type: ignore[no-redef]
    HAS_VIDEO_RECORDER = True
except ImportError:
    HAS_VIDEO_RECORDER = False
    
    class VideoRecorder:
        """Stub class for when opencv-python is not installed."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "VideoRecorder requires opencv-python. Install with: pdm add opencv-python"
            )
        
        def write_frame(self, frame):  # type: ignore
            """Stub method."""
            pass
        
        def release(self) -> None:
            """Stub method."""
            pass
        
        @property
        def duration(self) -> float:
            """Stub property."""
            return 0.0

DEFAULT_SETTINGS_FILE = "plasma_effect_settings.txt"


def _parse_bool(value, default):
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes", "y", "on")


def _get_env(name, default):
    value = os.getenv(name)
    return default if value is None else value


def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


@dataclass(frozen=True)
class Settings:
    frame_rate: int
    window_width: int
    window_height: int
    render: "RenderConfig"
    render_width: int
    render_height: int
    settings_file: str

    @classmethod
    def from_sources(cls, settings_file, overrides):
        if settings_file:
            load_dotenv(settings_file, override=True)

        window_width = int(float(_get_env("WINDOW_WIDTH", "1200")))
        window_height = int(float(_get_env("WINDOW_HEIGHT", "800")))
        frame_rate = int(_get_env("FRAME_RATE", "120"))

        render_scale = float(_get_env("RENDER_SCALE", "1.0"))
        scale = float(_get_env("SCALE", "1.0"))
        time_scale = float(_get_env("TIME_SCALE", "0.05"))
        specular = _parse_bool(_get_env("SPECULAR", "True"), True)
        palette = _get_env("PALETTE", "warm")
        phase_preset = _get_env("PHASE_PRESET", "default")
        show_fps = _parse_bool(_get_env("SHOW_FPS", "False"), False)
        record = _parse_bool(_get_env("RECORD", "False"), False)
        record_duration = float(_get_env("RECORD_DURATION", "10.0"))
        record_output = _get_env("RECORD_OUTPUT", "plasma_output.mp4")

        if overrides.window_width is not None:
            window_width = overrides.window_width
        if overrides.window_height is not None:
            window_height = overrides.window_height
        if overrides.frame_rate is not None:
            frame_rate = overrides.frame_rate
        if overrides.render_scale is not None:
            render_scale = overrides.render_scale
        if overrides.scale is not None:
            scale = overrides.scale
        if overrides.time_scale is not None:
            time_scale = overrides.time_scale
        if overrides.specular is not None:
            specular = overrides.specular
        if overrides.palette is not None:
            palette = overrides.palette
        if overrides.phase_preset is not None:
            phase_preset = overrides.phase_preset
        if overrides.show_fps is not None:
            show_fps = overrides.show_fps
        if overrides.record is not None:
            record = overrides.record
        if overrides.record_duration is not None:
            record_duration = overrides.record_duration
        if overrides.record_output is not None:
            record_output = overrides.record_output

        window_width = int(_clamp(window_width, 100, 4096))
        window_height = int(_clamp(window_height, 100, 4096))
        frame_rate = int(_clamp(frame_rate, 1, 240))
        record_duration = _clamp(record_duration, 0.1, 3600.0)

        render_scale = _clamp(render_scale, 0.05, 2.0)
        scale = _clamp(scale, 0.1, 5.0)
        time_scale = _clamp(time_scale, 0.001, 5.0)

        if palette not in PALETTES:
            palette = "warm"
        if phase_preset not in PHASE_PRESETS:
            phase_preset = "default"

        render_width = max(1, int(window_width * render_scale))
        render_height = max(1, int(window_height * render_scale))

        render = RenderConfig(
            specular=specular,
            scale=scale,
            time_scale=time_scale,
            render_scale=render_scale,
            palette=palette,
            phase_preset=phase_preset,
            show_fps=show_fps,
            record=record,
            record_duration=record_duration,
            record_output=record_output,
        )

        return cls(
            frame_rate=frame_rate,
            window_width=window_width,
            window_height=window_height,
            render=render,
            render_width=render_width,
            render_height=render_height,
            settings_file=settings_file,
        )


@dataclass(frozen=True)
class RenderConfig:
    specular: bool
    scale: float
    time_scale: float
    render_scale: float
    palette: str
    phase_preset: str
    show_fps: bool
    record: bool
    record_duration: float
    record_output: str


class FPSCounter:
    """Simple FPS counter for real-time monitoring."""

    def __init__(self, window_size=60):
        self.window_size = window_size
        self.frame_times = []
        self.last_time = time.time()

    def tick(self):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        self.frame_times.append(dt)
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)

    @property
    def fps(self):
        if not self.frame_times:
            return 0
        avg_dt = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_dt if avg_dt > 0 else 0

    @property
    def frame_time_ms(self):
        if not self.frame_times:
            return 0
        return (sum(self.frame_times) / len(self.frame_times)) * 1000


def render_text_to_surface(font, text, color=(255, 255, 255)):
    """Render text to a surface."""
    return font.render(text, True, color)


def parse_args():
    parser = argparse.ArgumentParser(description="Plasma effect renderer")
    parser.add_argument("--settings-file", default=os.getenv("SETTINGS_FILE", DEFAULT_SETTINGS_FILE))
    parser.add_argument("--window-width", type=int)
    parser.add_argument("--window-height", type=int)
    parser.add_argument("--frame-rate", type=int)
    parser.add_argument("--render-scale", type=float)
    parser.add_argument("--time-scale", type=float)
    parser.add_argument("--scale", type=float)
    parser.add_argument("--palette", choices=list(PALETTES.keys()))
    parser.add_argument("--phase-preset", choices=list(PHASE_PRESETS.keys()))
    parser.add_argument("--show-fps", action="store_true", default=None)
    parser.add_argument("--record", action="store_true", default=None, help="Record animation to video")
    parser.add_argument("--record-duration", type=float, help="Recording duration in seconds")
    parser.add_argument("--record-output", help="Output video file path")
    parser.add_argument("--specular", dest="specular", action="store_true")
    parser.add_argument("--no-specular", dest="specular", action="store_false")
    parser.set_defaults(specular=None)
    return parser.parse_args()


def print_startup_info(settings):
    """Print startup configuration and validation."""
    print("\n" + "=" * 60)
    print("PLASMA EFFECT - START CONFIGURATION")
    print("=" * 60)
    print(f"Window:        {settings.window_width}x{settings.window_height}")
    print(f"Render:        {settings.render_width}x{settings.render_height} (scale: {settings.render.render_scale})")
    print(f"Frame rate:    {settings.frame_rate} FPS")
    print(f"Palette:       {settings.render.palette}")
    print(f"Phase preset:  {settings.render.phase_preset}")
    print(f"Time scale:    {settings.render.time_scale}")
    print(f"Specular:      {'ON' if settings.render.specular else 'OFF'}")
    print(f"Show FPS:      {'YES' if settings.render.show_fps else 'NO'}")
    if settings.render.record:
        if HAS_VIDEO_RECORDER:
            print(f"Recording:     YES → {settings.render.record_output} ({settings.render.record_duration}s)")
        else:
            print("Recording:     REQUESTED but opencv-python not installed (run: pdm add opencv-python)")
    else:
        print("Recording:     NO")
    print("-" * 60)
    print("KEYBINDS:")
    print("  ESC/Q:       Quit")
    print("  S:           Toggle specular effect")
    print("  P:           Cycle palettes")
    print("  M:           Cycle phase presets")
    print("  +/-:         Adjust time scale")
    print("=" * 60 + "\n")


def main():
    """Main function to run the plasma effect visualization."""
    args = parse_args()
    settings = Settings.from_sources(args.settings_file, args)

    print_startup_info(settings)

    window_width = settings.window_width
    window_height = settings.window_height
    render_width = settings.render_width
    render_height = settings.render_height

    pygame.init()
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Plasma Effect")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    # Current state (mutable)
    palette_idx = list(PALETTES.keys()).index(settings.render.palette)
    phase_idx = list(PHASE_PRESETS.keys()).index(settings.render.phase_preset)
    current_time_scale = settings.render.time_scale
    current_specular = settings.render.specular
    show_fps = settings.render.show_fps

    renderer = PlasmaRenderer(
        render_width,
        render_height,
        settings.render.scale,
        current_time_scale,
        current_specular,
        settings.render.palette,
        settings.render.phase_preset,
    )

    # Setup video recording if requested
    video_recorder = None
    if settings.render.record and HAS_VIDEO_RECORDER:
        try:
            video_recorder = VideoRecorder(
                settings.render.record_output,
                render_width,
                render_height,
                fps=settings.frame_rate,
                codec="mp4",
            )
            print(f"[Recording] Started → {settings.render.record_output}")
        except Exception as e:
            print(f"[Recording] Error: {e}")
            video_recorder = None
    elif settings.render.record and not HAS_VIDEO_RECORDER:
        print("[Recording] opencv-python not installed. Run: pdm add opencv-python")

    fps_counter = FPSCounter()
    running = True
    start_time = time.time()

    while running:
        fps_counter.tick()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_s:
                    current_specular = not current_specular
                    renderer = PlasmaRenderer(
                        render_width,
                        render_height,
                        settings.render.scale,
                        current_time_scale,
                        current_specular,
                        list(PALETTES.keys())[palette_idx],
                        list(PHASE_PRESETS.keys())[phase_idx],
                    )
                    print(f"Specular: {'ON' if current_specular else 'OFF'}")
                elif event.key == pygame.K_p:
                    palette_idx = (palette_idx + 1) % len(PALETTES)
                    palette_name = list(PALETTES.keys())[palette_idx]
                    renderer = PlasmaRenderer(
                        render_width,
                        render_height,
                        settings.render.scale,
                        current_time_scale,
                        current_specular,
                        palette_name,
                        list(PHASE_PRESETS.keys())[phase_idx],
                    )
                    print(f"Palette: {palette_name}")
                elif event.key == pygame.K_m:
                    phase_idx = (phase_idx + 1) % len(PHASE_PRESETS)
                    phase_name = list(PHASE_PRESETS.keys())[phase_idx]
                    renderer = PlasmaRenderer(
                        render_width,
                        render_height,
                        settings.render.scale,
                        current_time_scale,
                        current_specular,
                        list(PALETTES.keys())[palette_idx],
                        phase_name,
                    )
                    print(f"Phase preset: {phase_name}")
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    current_time_scale = _clamp(current_time_scale * 1.2, 0.001, 5.0)
                    renderer = PlasmaRenderer(
                        render_width,
                        render_height,
                        settings.render.scale,
                        current_time_scale,
                        current_specular,
                        list(PALETTES.keys())[palette_idx],
                        list(PHASE_PRESETS.keys())[phase_idx],
                    )
                    print(f"Time scale: {current_time_scale:.4f}")
                elif event.key == pygame.K_MINUS:
                    current_time_scale = _clamp(current_time_scale / 1.2, 0.001, 5.0)
                    renderer = PlasmaRenderer(
                        render_width,
                        render_height,
                        settings.render.scale,
                        current_time_scale,
                        current_specular,
                        list(PALETTES.keys())[palette_idx],
                        list(PHASE_PRESETS.keys())[phase_idx],
                    )
                    print(f"Time scale: {current_time_scale:.4f}")

        elapsed_time = time.time() - start_time
        frame = renderer.render(elapsed_time)

        # Write to video if recording
        if video_recorder is not None:
            video_recorder.write_frame(frame)
            if video_recorder.duration >= settings.render.record_duration:
                print(f"[Recording] Duration reached ({video_recorder.duration:.1f}s). Stopping...")
                running = False

        # Convert NumPy array to Pygame surface
        surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        if (render_width, render_height) != (window_width, window_height):
            surface = pygame.transform.smoothscale(surface, (window_width, window_height))

        screen.blit(surface, (0, 0))

        # Draw recording indicator and FPS overlay
        if video_recorder is not None:
            record_text = render_text_to_surface(
                font, f"REC {video_recorder.duration:.1f}s / {settings.render.record_duration:.0f}s", (255, 0, 0)
            )
            screen.blit(record_text, (10, 10))

        if show_fps:
            fps_text = render_text_to_surface(font, f"FPS: {fps_counter.fps:.1f} | Frame: {fps_counter.frame_time_ms:.2f}ms")
            offset = (10, 40) if video_recorder is not None else (10, 10)
            screen.blit(fps_text, offset)

        pygame.display.flip()
        clock.tick(settings.frame_rate)

    # Cleanup
    if video_recorder is not None:
        video_recorder.release()
        print(f"[Recording] Saved → {settings.render.record_output} ({video_recorder.duration:.1f}s)")

    pygame.quit()
    print("Goodbye!")


if __name__ == "__main__":
    # exemple: pdm run python plasma_effect.py --record --record-duration 20 --palette lava --phase-preset spiral
    main()
