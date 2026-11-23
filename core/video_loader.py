import os
import cv2
import numpy as np
from typing import Generator, Tuple


class VideoLoader:
    """Обертка над OpenCV для безопасного покадрового чтения видео."""

    def __init__(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Видеофайл не найден: {file_path}")

        self.file_path = file_path
        self.cap = cv2.VideoCapture(file_path)

        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть видеофайл: {file_path}")

        raw_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps: float = raw_fps if raw_fps > 0 else 30.0
        self.total_frames: int = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def __enter__(self) -> "VideoLoader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def frames(self) -> Generator[Tuple[int, np.ndarray], None, None]:
        frame_idx = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame_idx, frame
            frame_idx += 1

    def seek(self, frame_number: int) -> None:
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    def release(self) -> None:
        if self.cap.isOpened():
            self.cap.release()