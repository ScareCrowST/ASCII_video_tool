import argparse
import os
import sys
import time
from typing import Optional

import cv2

from core.video_loader import VideoLoader
from core.terminal import TerminalManager
from core.renderer import FrameRenderer
from core.controls import KeyController
from core.gpu_window import FastAsciiWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="60 FPS HD ASCII Video Player.")
    parser.add_argument("video_path", type=str, help="Путь к видеофайлу")
    parser.add_argument(
        "-c", "--charset",
        type=str,
        choices=["ultra", "hacker", "standard"],
        default="ultra",
        help="Набор символов",
    )
    parser.add_argument(
        "--filter",
        type=str,
        choices=["none", "matrix", "amber", "cyberpunk", "bw"],
        default="none",
        help="Цветовой фильтр",
    )
    parser.add_argument("-f", "--font-size", type=int, default=8, help="Размер символов (меньше = больше деталей)")
    parser.add_argument("--fps", type=float, default=None, help="Целевой FPS окна (по умолчанию 60 с интерполяцией)")
    parser.add_argument("-w", "--width", type=int, default=None, help="Макс. ширина (для режима --terminal)")
    parser.add_argument("-l", "--loop", action="store_true", help="Зациклить видео")
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Запустить в старом текстовом режиме внутри окна терминала",
    )
    return parser.parse_args()


def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def run_fast_window(
    video_path: str,
    charset: str = "ultra",
    color_filter: str = "none",
    font_size: int = 8,
    target_fps: Optional[float] = None,
    loop: bool = False,
) -> None:
    """Аппаратно-ускоренный режим на 60 FPS с интерполяцией промежуточных кадров."""
    win = FastAsciiWindow(
        title=f"60 FPS ASCII Player - {os.path.basename(video_path)}",
        charset_name=charset,
        color_filter=color_filter,
        font_size=font_size,
        saturation=1.15,
    )

    try:
        with VideoLoader(video_path) as video:
            source_fps = video.fps if video.fps > 0 else 30.0
            display_fps = target_fps if target_fps and target_fps > 0 else max(60.0, source_fps)
            frame_duration = 1.0 / display_fps
            total_sec = (video.total_frames / source_fps) if video.total_frames > 0 else 0.0

            paused = False
            playback_time = 0.0
            cached_idx = -1
            frame_0 = None
            frame_1 = None

            real_fps = display_fps
            last_tick = time.perf_counter()

            while True:
                action = win.poll_events()
                if action == "quit":
                    break
                elif action == "pause":
                    paused = not paused
                elif action == "next_filter":
                    win.next_filter()
                elif action == "next_charset":
                    win.next_charset()
                elif action == "sat_up":
                    win.saturation = min(2.5, round(win.saturation + 0.15, 2))
                elif action == "sat_down":
                    win.saturation = max(0.0, round(win.saturation - 0.15, 2))
                elif action in ("seek_back", "seek_forward"):
                    delta_sec = -5.0 if action == "seek_back" else 5.0
                    playback_time = max(0.0, playback_time + delta_sec)
                    if total_sec > 0:
                        playback_time = min(total_sec - 0.1, playback_time)
                    target_idx = int(playback_time * source_fps)
                    video.seek(target_idx)
                    cached_idx = -1
                    frame_0 = None
                    frame_1 = None

                frame_start = time.perf_counter()

                exact_frame = playback_time * source_fps
                idx_0 = int(exact_frame)
                alpha = exact_frame - idx_0

                while cached_idx < idx_0:
                    if frame_1 is not None and cached_idx + 1 == idx_0:
                        frame_0 = frame_1
                        ret, frame_1 = video.cap.read()
                        if not ret:
                            frame_1 = frame_0
                        cached_idx += 1
                    else:
                        ret0, f0 = video.cap.read()
                        if not ret0:
                            if loop:
                                playback_time = 0.0
                                video.seek(0)
                                cached_idx = -1
                                frame_0 = None
                                frame_1 = None
                                idx_0 = 0
                                alpha = 0.0
                                break
                            return
                        ret1, f1 = video.cap.read()
                        frame_0 = f0
                        frame_1 = f1 if ret1 else f0
                        cached_idx = idx_0

                if frame_0 is None:
                    continue

                if frame_1 is not None and 0.05 < alpha < 0.95:
                    render_target = cv2.addWeighted(frame_0, 1.0 - alpha, frame_1, alpha, 0)
                else:
                    render_target = frame_0

                now = time.perf_counter()
                dt = now - last_tick
                if dt > 0:
                    real_fps = 0.85 * real_fps + 0.15 * (1.0 / dt)
                last_tick = now

                if not paused:
                    playback_time += dt if dt < 0.2 else frame_duration
                    if total_sec > 0 and playback_time >= total_sec:
                        if loop:
                            playback_time = 0.0
                            video.seek(0)
                            cached_idx = -1
                            frame_0 = None
                            frame_1 = None
                        else:
                            break

                state_icon = "PAUSED" if paused else "PLAY"
                status = (
                    f"[{state_icon}] {format_time(playback_time)}/{format_time(total_sec)} | "
                    f"FPS: {real_fps:.0f} | Filter[F]: {win.color_filter} | "
                    f"Charset[C]: {win.current_charset_name} | Size[Wheel / []]: {win.font_size}px | "
                    f"[Space] Pause  [<-/->] ±5s  [F11] Fullscreen  [Q] Quit"
                )

                win.render_frame(render_target, status)

                if paused:
                    time.sleep(0.02)
                else:
                    elapsed = time.perf_counter() - frame_start
                    sleep_time = frame_duration - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

    finally:
        win.close()


def run_terminal_player(
    video_path: str,
    charset: str = "ultra",
    color_filter: str = "none",
    font_size: int = 6,
    target_fps: Optional[float] = None,
    max_width: Optional[int] = None,
    loop: bool = False,
) -> None:
    """Классический текстовый режим внутри окна терминала."""
    renderer = FrameRenderer(charset_name=charset, color_filter=color_filter, saturation=1.15)
    controls = KeyController()

    with VideoLoader(video_path) as video, TerminalManager(
        title=f"ASCII Player - {os.path.basename(video_path)}",
        font_size=font_size,
        maximize=True,
    ) as term:
        time.sleep(0.1)
        fps = target_fps if target_fps and target_fps > 0 else video.fps
        frame_duration = 1.0 / fps
        total_sec = (video.total_frames / fps) if video.total_frames > 0 else 0.0

        paused = False
        current_idx = 0
        last_frame = None
        real_fps = fps
        last_tick = time.perf_counter()

        while True:
            action = controls.poll_action()
            if action == "quit":
                break
            elif action == "pause":
                paused = not paused
            elif action == "next_filter":
                renderer.next_filter()
            elif action == "next_charset":
                renderer.next_charset()
            elif action == "sat_up":
                renderer.saturation = min(2.5, round(renderer.saturation + 0.15, 2))
            elif action == "sat_down":
                renderer.saturation = max(0.0, round(renderer.saturation - 0.15, 2))
            elif action == "res_up":
                renderer.MAX_TOTAL_CELLS = min(150000, renderer.MAX_TOTAL_CELLS + 8000)
            elif action == "res_down":
                renderer.MAX_TOTAL_CELLS = max(10000, renderer.MAX_TOTAL_CELLS - 8000)
            elif action in ("seek_back", "seek_forward"):
                step_frames = int(fps * 5)
                delta = -step_frames if action == "seek_back" else step_frames
                current_idx = max(0, current_idx + delta)
                if video.total_frames > 0:
                    current_idx = min(video.total_frames - 1, current_idx)
                video.seek(current_idx)
                last_frame = None

            frame_start = time.perf_counter()
            if not paused or last_frame is None:
                ret, frame = video.cap.read()
                if not ret:
                    if loop:
                        current_idx = 0
                        video.seek(0)
                        continue
                    break
                last_frame = frame
                current_idx += 1

            cols, rows = term.get_size()
            if max_width is not None:
                cols = min(cols, max_width)

            ascii_art = renderer.render(last_frame, cols, rows)

            now = time.perf_counter()
            dt = now - last_tick
            if dt > 0:
                real_fps = 0.85 * real_fps + 0.15 * (1.0 / dt)
            last_tick = now

            cur_sec = current_idx / fps
            state_icon = "PAUSED" if paused else "PLAY"
            status = (
                f"\033[90m[{state_icon}] {format_time(cur_sec)}/{format_time(total_sec)} | "
                f"FPS: \033[92m{real_fps:.0f}\033[90m | "
                f"Filter[F]: \033[96m{renderer.color_filter}\033[90m | "
                f"Charset[C]: \033[93m{renderer.current_charset_name}\033[90m | "
                f"Density[ [/] ]: {renderer.MAX_TOTAL_CELLS // 1000}k | "
                f"[Space] Pause [<-/->] ±5s [Q] Quit\033[0m"
            )

            term.render(f"{ascii_art}\n{status}")

            if paused:
                time.sleep(0.04)
            else:
                elapsed = time.perf_counter() - frame_start
                sleep_time = frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)


if __name__ == "__main__":
    args = parse_args()
    try:
        if args.terminal:
            run_terminal_player(
                video_path=args.video_path,
                charset=args.charset,
                color_filter=args.filter,
                font_size=args.font_size,
                target_fps=args.fps,
                max_width=args.width,
                loop=args.loop,
            )
        else:
            run_fast_window(
                video_path=args.video_path,
                charset=args.charset,
                color_filter=args.filter,
                font_size=args.font_size,
                target_fps=args.fps,
                loop=args.loop,
            )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Playback error: {e}", file=sys.stderr)
        input("Press Enter to exit...")
        sys.exit(1)
