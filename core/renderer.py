import cv2
import numpy as np
from typing import Tuple


class FrameRenderer:
    """Рендерер с мягким сглаживанием, визуальными фильтрами и управлением насыщенностью."""

    CHARSETS = {
        "ultra": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
        "hacker": " .'`^\",:;!i~+_-?][}{)(|/\\&%#@$",
        "standard": " .:-=+*#%@",
    }

    BAYER_4X4 = (
        np.array(
            [
                [0, 8, 2, 10],
                [12, 4, 14, 6],
                [3, 11, 1, 9],
                [15, 7, 13, 5],
            ],
            dtype=np.float32,
        )
        / 16.0
        - 0.5
    ) * 4.5

    FILTERS = ["none", "matrix", "amber", "cyberpunk", "bw"]

    def __init__(
        self,
        charset_name: str = "ultra",
        color_filter: str = "none",
        saturation: float = 1.15,
    ) -> None:
        self.charset_names = list(self.CHARSETS.keys())
        self.set_charset(charset_name)
        self.color_filter = color_filter if color_filter in self.FILTERS else "none"
        self.saturation = saturation

    def set_charset(self, charset_name: str) -> None:
        self.current_charset_name = charset_name if charset_name in self.CHARSETS else "ultra"
        chars_str = self.CHARSETS[self.current_charset_name]
        self.chars = np.array(list(chars_str))
        self.num_chars = len(self.chars)

    def next_charset(self) -> str:
        idx = (self.charset_names.index(self.current_charset_name) + 1) % len(self.charset_names)
        self.set_charset(self.charset_names[idx])
        return self.current_charset_name

    def next_filter(self) -> str:
        idx = (self.FILTERS.index(self.color_filter) + 1) % len(self.FILTERS)
        self.color_filter = self.FILTERS[idx]
        return self.color_filter

    def _calculate_target_size(
        self, orig_w: int, orig_h: int, max_cols: int, max_rows: int
    ) -> Tuple[int, int]:
        # Оставляем 2 строки снизу под строку статуса/управления
        avail_rows = max(1, max_rows - 2)
        avail_cols = max(1, max_cols)
        aspect_ratio = orig_h / orig_w

        font_aspect = 0.48
        target_w = avail_cols
        target_h = int(target_w * aspect_ratio * font_aspect)

        if target_h > avail_rows:
            target_h = avail_rows
            target_w = max(1, int(target_h / (aspect_ratio * font_aspect)))

        return max(1, target_w), max(1, target_h)

    def _apply_color_effects(self, rgb: np.ndarray, luminance: np.ndarray) -> np.ndarray:
        """Применяет насыщенность и выбранный цветовой фильтр."""
        if self.color_filter == "matrix":
            # Фосфорный зеленый в стиле Матрицы
            out = np.zeros_like(rgb)
            out[:, :, 0] = np.clip(luminance * 0.12, 0, 255)
            out[:, :, 1] = np.clip(luminance * 1.15, 0, 255)
            out[:, :, 2] = np.clip(luminance * 0.22, 0, 255)
            return out.astype(np.uint8)

        if self.color_filter == "amber":
            # Теплый янтарный CRT-монитор
            out = np.zeros_like(rgb)
            out[:, :, 0] = np.clip(luminance * 1.15, 0, 255)
            out[:, :, 1] = np.clip(luminance * 0.68, 0, 255)
            out[:, :, 2] = np.clip(luminance * 0.08, 0, 255)
            return out.astype(np.uint8)

        if self.color_filter == "bw":
            # Чистый монохром
            gray = np.clip(luminance, 0, 255).astype(np.uint8)
            return np.stack([gray, gray, gray], axis=-1)

        # Регулировка насыщенности для обычного режима и cyberpunk
        sat = self.saturation * (1.45 if self.color_filter == "cyberpunk" else 1.0)
        if abs(sat - 1.0) > 0.02:
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat, 0, 255)
            rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

        if self.color_filter == "cyberpunk":
            # Неоновый пурпурно-голубой сдвиг
            out = rgb.astype(np.float32)
            out[:, :, 0] = np.clip(out[:, :, 0] * 1.15 + 15, 0, 255)
            out[:, :, 1] = np.clip(out[:, :, 1] * 0.88, 0, 255)
            out[:, :, 2] = np.clip(out[:, :, 2] * 1.25 + 20, 0, 255)
            return out.astype(np.uint8)

        return rgb

    def render(self, frame: np.ndarray, max_cols: int, max_rows: int) -> str:
        orig_h, orig_w, _ = frame.shape
        target_w, target_h = self._calculate_target_size(orig_w, orig_h, max_cols, max_rows)

        smoothed = cv2.GaussianBlur(frame, (3, 3), sigmaX=0.6)
        resized = cv2.resize(smoothed, (target_w, target_h), interpolation=cv2.INTER_AREA)

        soft_blur = cv2.GaussianBlur(resized, (0, 0), sigmaX=0.8)
        balanced = cv2.addWeighted(resized, 1.2, soft_blur, -0.2, 0)

        rgb = balanced[:, :, ::-1]

        luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        luminance = 255.0 * np.power(np.clip(luminance / 255.0, 0.0, 1.0), 0.92)

        rgb_styled = self._apply_color_effects(rgb, luminance)

        dither = np.tile(self.BAYER_4X4, (target_h // 4 + 1, target_w // 4 + 1))[:target_h, :target_w]
        lum_final = np.clip(luminance + dither, 0, 255)

        indices = np.clip((lum_final / 256.0) * self.num_chars, 0, self.num_chars - 1).astype(np.int32)
        char_matrix = self.chars[indices]

        r_arr, g_arr, b_arr = rgb_styled[:, :, 0], rgb_styled[:, :, 1], rgb_styled[:, :, 2]

        lines = []
        for y in range(target_h):
            row_parts = []
            prev_color = (-1, -1, -1)
            r_row, g_row, b_row = r_arr[y], g_arr[y], b_arr[y]
            c_row = char_matrix[y]

            for x in range(target_w):
                ch = c_row[x]
                if ch == " ":
                    row_parts.append(" ")
                    continue

                color = (int(r_row[x]), int(g_row[x]), int(b_row[x]))
                if color != prev_color:
                    row_parts.append(f"\033[38;2;{color[0]};{color[1]};{color[2]}m{ch}")
                    prev_color = color
                else:
                    row_parts.append(ch)

            lines.append("".join(row_parts))

        return "\n".join(lines) + "\033[0m"