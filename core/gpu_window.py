import cv2
import numpy as np
import pygame
from typing import Optional


class FastAsciiWindow:
    """Аппаратно-ускоренное окно рендера ASCII-символов на 60 FPS через кэш глифов NumPy + Pygame."""

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
        title: str = "60 FPS HD ASCII Player",
        charset_name: str = "ultra",
        color_filter: str = "none",
        font_size: int = 8,
        saturation: float = 1.15,
    ) -> None:
        pygame.init()
        pygame.display.set_caption(title)

        info = pygame.display.Info()
        self.win_w = int(info.current_w * 0.92)
        self.win_h = int(info.current_h * 0.90)
        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
        self.ui_font = pygame.font.SysFont("Consolas", 15)

        self.charset_names = list(self.CHARSETS.keys())
        self.current_charset_name = charset_name if charset_name in self.CHARSETS else "ultra"
        self.color_filter = color_filter if color_filter in self.FILTERS else "none"
        self.saturation = saturation
        self.font_size = max(4, min(24, font_size))

        self._build_glyph_cache()

    def _build_glyph_cache(self) -> None:
        font = pygame.font.SysFont("Consolas", self.font_size, bold=False)
        self.glyph_w, self.glyph_h = font.size("M")
        self.glyph_w = max(3, self.glyph_w)
        self.glyph_h = max(5, self.glyph_h)

        chars_str = self.CHARSETS[self.current_charset_name]
        self.num_chars = len(chars_str)

        glyphs = np.zeros((self.num_chars, self.glyph_h, self.glyph_w), dtype=np.float32)

        for i, ch in enumerate(chars_str):
            if ch == " ":
                continue
            surf = font.render(ch, True, (255, 255, 255), (0, 0, 0))
            arr = pygame.surfarray.array3d(surf)[:, :, 0].T
            h = min(self.glyph_h, arr.shape[0])
            w = min(self.glyph_w, arr.shape[1])
            glyphs[i, :h, :w] = arr[:h, :w] / 255.0

        self.glyph_cache = glyphs

    def set_font_size(self, new_size: int) -> None:
        clamped = max(4, min(24, new_size))
        if clamped != self.font_size:
            self.font_size = clamped
            self._build_glyph_cache()

    def next_charset(self) -> str:
        idx = (self.charset_names.index(self.current_charset_name) + 1) % len(self.charset_names)
        self.current_charset_name = self.charset_names[idx]
        self._build_glyph_cache()
        return self.current_charset_name

    def next_filter(self) -> str:
        idx = (self.FILTERS.index(self.color_filter) + 1) % len(self.FILTERS)
        self.color_filter = self.FILTERS[idx]
        return self.color_filter

    def _apply_color_effects(self, rgb: np.ndarray, luminance: np.ndarray) -> np.ndarray:
        if self.color_filter == "matrix":
            out = np.zeros_like(rgb, dtype=np.float32)
            out[:, :, 0] = luminance * 0.12
            out[:, :, 1] = luminance * 1.18
            out[:, :, 2] = luminance * 0.22
            return np.clip(out, 0, 255).astype(np.uint8)

        if self.color_filter == "amber":
            out = np.zeros_like(rgb, dtype=np.float32)
            out[:, :, 0] = luminance * 1.18
            out[:, :, 1] = luminance * 0.68
            out[:, :, 2] = luminance * 0.08
            return np.clip(out, 0, 255).astype(np.uint8)

        if self.color_filter == "bw":
            gray = np.clip(luminance, 0, 255).astype(np.uint8)
            return np.stack([gray, gray, gray], axis=-1)

        sat = self.saturation * (1.45 if self.color_filter == "cyberpunk" else 1.0)
        if abs(sat - 1.0) > 0.02:
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat, 0, 255)
            rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

        if self.color_filter == "cyberpunk":
            out = rgb.astype(np.float32)
            out[:, :, 0] = out[:, :, 0] * 1.15 + 15
            out[:, :, 1] = out[:, :, 1] * 0.88
            out[:, :, 2] = out[:, :, 2] * 1.25 + 20
            return np.clip(out, 0, 255).astype(np.uint8)

        return rgb

    def render_frame(self, bgr_frame: np.ndarray, status_text: str) -> None:
        avail_w = self.win_w
        avail_h = max(20, self.win_h - 26)

        orig_h, orig_w, _ = bgr_frame.shape
        aspect = orig_h / orig_w
        glyph_aspect = self.glyph_w / self.glyph_h

        cols = max(1, avail_w // self.glyph_w)
        rows = max(1, int(cols * aspect * glyph_aspect))
        if rows * self.glyph_h > avail_h:
            rows = max(1, avail_h // self.glyph_h)
            cols = max(1, int(rows / (aspect * glyph_aspect)))

        resized = cv2.resize(bgr_frame, (cols, rows), interpolation=cv2.INTER_AREA)
        rgb = resized[:, :, ::-1]

        luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        luminance = 255.0 * np.power(np.clip(luminance / 255.0, 0.0, 1.0), 0.92)
        rgb_styled = self._apply_color_effects(rgb, luminance)

        dither = np.tile(self.BAYER_4X4, (rows // 4 + 1, cols // 4 + 1))[:rows, :cols]
        lum_final = np.clip(luminance + dither, 0, 255)
        indices = np.clip((lum_final / 256.0) * self.num_chars, 0, self.num_chars - 1).astype(np.int32)

        selected_glyphs = self.glyph_cache[indices]
        canvas = (
            selected_glyphs[:, :, :, :, None] * rgb_styled[:, :, None, None, :]
        ).transpose(0, 2, 1, 3, 4).reshape(rows * self.glyph_h, cols * self.glyph_w, 3).astype(np.uint8)

        self.screen.fill((8, 8, 8))
        frame_surf = pygame.surfarray.make_surface(canvas.transpose(1, 0, 2))
        offset_x = (avail_w - frame_surf.get_width()) // 2
        offset_y = (avail_h - frame_surf.get_height()) // 2
        self.screen.blit(frame_surf, (offset_x, offset_y))

        status_surf = self.ui_font.render(status_text, True, (180, 180, 180))
        self.screen.blit(status_surf, (12, self.win_h - 22))
        pygame.display.flip()

    def poll_events(self) -> Optional[str]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.VIDEORESIZE:
                self.win_w, self.win_h = event.w, event.h
                self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEWHEEL:
                self.set_font_size(self.font_size + event.y)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "quit"
                elif event.key == pygame.K_SPACE:
                    return "pause"
                elif event.key == pygame.K_LEFT:
                    return "seek_back"
                elif event.key == pygame.K_RIGHT:
                    return "seek_forward"
                elif event.key == pygame.K_f:
                    return "next_filter"
                elif event.key == pygame.K_c:
                    return "next_charset"
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    return "sat_up"
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    return "sat_down"
                elif event.key == pygame.K_LEFTBRACKET:
                    self.set_font_size(self.font_size + 1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    self.set_font_size(self.font_size - 1)
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
        return None

    def close(self) -> None:
        pygame.quit()
