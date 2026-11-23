import argparse
import os
import sys
import time
from typing import Optional

from core.video_loader import VideoLoader
from core.terminal import TerminalManager
from core.renderer import FrameRenderer
from core.controls import KeyController


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Интерактивный HD ASCII видеоплеер.")
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
    parser.add_argument("-f", "--font-size", type=int, default=4, help="Размер шрифта в cmd")
    parser.add_argument("--fps", type=float, default=None, help="Принудительный FPS")
    parser.add_argument("-w", "--width", type=int, default=None, help="Макс. ширина")
    parser.add_argument("-l", "--loop", action="store_true", help="Зациклить видео")
    return parser.parse_args()


def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def run_player(
    video_path: str,
    charset: str = "ultra",
    color_filter: str = "none",
    font_size: int = 4,
    target_fps: Optional[float] = None,
    max_width: Optional[int] = None,
    loop: bool = False,
) -> None:
    renderer = FrameRenderer(charset_name=charset, color_filter=color_filter, saturation=1.15)
    controls = KeyController()

    try:
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

                cur_sec = current_idx / fps
                state_icon = "ПАУЗА" if paused else "ИГРАЕТ"
                status = (
                    f"\033[90m[{state_icon}] {format_time(cur_sec)}/{format_time(total_sec)} | "
                    f"Фильтр[F]: \033[96m{renderer.color_filter}\033[90m | "
                    f"Символы[C]: \033[93m{renderer.current_charset_name}\033[90m | "
                    f"Насыщ.[+/-]: {renderer.saturation:.2f} | "
                    f"[Пробел] Пауза  [<-/->] ±5с  [Q] Выход\033[0m"
                )

                term.render(f"{ascii_art}\n{status}")

                
                if paused:
                    time.sleep(0.04)
                else:
                    elapsed = time.perf_counter() - frame_start
                    sleep_time = frame_duration - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Ошибка воспроизведения: {e}", file=sys.stderr)
        input("Нажмите Enter для выхода...")
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    run_player(
        video_path=args.video_path,
        charset=args.charset,
        color_filter=args.filter,
        font_size=args.font_size,
        target_fps=args.fps,
        max_width=args.width,
        loop=args.loop,
    )