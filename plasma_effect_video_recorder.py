"""
Video recording utility for plasma effect animation.
"""

import cv2
import numpy as np
import os
from typing import Optional


class VideoRecorder:
    """Records rendered frames to an MP4 or other video format."""

    CODEC_MAP = {
        "mp4": ("mp4v", ".mp4"),
        "avi": ("MJPG", ".avi"),
        "webm": ("VP90", ".webm"),
    }

    def __init__(self, output_path: str, width: int, height: int, fps: int = 30, codec: str = "mp4"):
        """
        Initialize the video recorder.

        Args:
            output_path (str): Path to save the video file.
            width (int): Video width in pixels.
            height (int): Video height in pixels.
            fps (int): Frames per second for the output video.
            codec (str): Codec to use (mp4, avi, webm).
        """
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.frame_count = 0

        # Determine codec fourcc and extension
        codec_str = "mp4v"
        ext = ".mp4"
        if codec in self.CODEC_MAP:
            codec_str, ext = self.CODEC_MAP[codec]
        
        self.fourcc = cv2.VideoWriter_fourcc(*codec_str)  # type: ignore[no-untyped-call]

        # Ensure output path has correct extension
        if not output_path.endswith(ext):
            self.output_path = output_path + ext

        # Create the video writer
        self.writer = cv2.VideoWriter(
            self.output_path,
            self.fourcc,
            self.fps,
            (self.width, self.height),
        )

        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to open video writer for {self.output_path}")

    def write_frame(self, frame: np.ndarray) -> None:
        """
        Write a frame to the video file.

        Args:
            frame (np.ndarray): RGB frame (height, width, 3) with uint8 values.
        """
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(
                f"Frame shape mismatch. Expected {(self.height, self.width, 3)}, "
                f"got {frame.shape}"
            )

        # OpenCV expects BGR, so convert RGB to BGR
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self.writer.write(bgr_frame)
        self.frame_count += 1

    def release(self) -> None:
        """Close the video writer and save the file."""
        if self.writer is not None:
            self.writer.release()

    def __enter__(self) -> "VideoRecorder":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    @property
    def duration(self) -> float:
        """Duration of the recorded video in seconds."""
        return self.frame_count / self.fps if self.fps > 0 else 0.0
