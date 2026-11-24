import os
import cv2


class VideoLoader:
    """Безопасная обертка над cv2.VideoCapture для загрузки и перемотки видео."""

    def __init__(self, video_path: str) -> None:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видеофайл не найден: {video_path}")
        self.video_path = video_path
        self.cap = None
        self.fps = 30.0
        self.total_frames = 0

    def __enter__(self) -> "VideoLoader":
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {self.video_path}")

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps and fps > 0 else 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.cap is not None:
            self.cap.release()

    def seek(self, frame_idx: int) -> None:
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx))
