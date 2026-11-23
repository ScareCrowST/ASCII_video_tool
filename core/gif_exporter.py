import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Literal

RenderMode = Literal["ascii", "blocks"]


class GifExporter:
    """Рендерит цветные ASCII/пиксельные кадры на картинку и сохраняет в зацикленный GIF."""

    CHARSETS = {
        "standard": " .:-=+*#%@",
        "detailed": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
        "minimal": " ░▒▓█",
    }

    def __init__(
        self,
        output_path: str,
        fps: float = 15.0,
        width_chars: int = 80,
        mode: RenderMode = "ascii",
        charset_name: str = "standard",
        font_size: int = 12,
    ) -> None:
        self.output_path = output_path
        self.fps = min(fps, 24.0)
        self.width_chars = width_chars
        self.mode = mode
        self.chars = np.array(list(self.CHARSETS.get(charset_name, self.CHARSETS["standard"])))
        self.num_chars = len(self.chars)
        self.frames: List[Image.Image] = []

        self.font = self._load_monospace_font(font_size)
        bbox = self.font.getbbox("A")
        self.char_w = max(1, bbox[2] - bbox[0])
        self.char_h = max(1, int((bbox[3] - bbox[1]) * 1.35))

    def _load_monospace_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for font_name in ["consola.ttf", "lucon.ttf", "DejaVuSansMono.ttf", "Menlo.ttc", "Courier New.ttf"]:
            try:
                return ImageFont.truetype(font_name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def add_frame(self, bgr_frame: np.ndarray) -> None:
        orig_h, orig_w, _ = bgr_frame.shape
        aspect_ratio = orig_h / orig_w

        if self.mode == "blocks":
            # В режиме blocks создаем четкую пиксельную сетку и увеличиваем без мыла (NEAREST)
            target_w = self.width_chars
            target_h = max(1, int(target_w * aspect_ratio))
            resized = cv2.resize(bgr_frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
            rgb = resized[:, :, ::-1]
            small_img = Image.fromarray(rgb, mode="RGB")
            scale = max(2, self.char_w)
            canvas = small_img.resize((target_w * scale, target_h * scale), resample=Image.Resampling.NEAREST)
        else:
            # В режиме ascii рисуем символы шрифтом на темном холсте
            target_w = self.width_chars
            target_h = max(1, int(target_w * aspect_ratio * (self.char_w / self.char_h)))
            resized = cv2.resize(bgr_frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
            rgb = resized[:, :, ::-1]

            luminance = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
            indices = np.clip((luminance / 256.0) * self.num_chars, 0, self.num_chars - 1).astype(np.int32)
            char_matrix = self.chars[indices]

            canvas = Image.new("RGB", (target_w * self.char_w, target_h * self.char_h), color=(12, 12, 12))
            draw = ImageDraw.Draw(canvas)

            for y in range(target_h):
                y_pos = y * self.char_h
                for x in range(target_w):
                    char = char_matrix[y, x]
                    if char != " ":
                        color = tuple(int(c) for c in rgb[y, x])
                        draw.text((x * self.char_w, y_pos), char, font=self.font, fill=color)

        quantized = canvas.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
        self.frames.append(quantized)

    def save(self) -> None:
        if not self.frames:
            raise ValueError("Нет кадров для сохранения в GIF.")

        out_dir = os.path.dirname(os.path.abspath(self.output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        duration_ms = int(1000 / self.fps)
        self.frames[0].save(
            self.output_path,
            save_all=True,
            append_images=self.frames[1:],
            duration=duration_ms,
            loop=0,  
            optimize=True,
        )