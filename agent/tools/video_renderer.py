"""
Video rendering engine for the RevenueCat AI Developer Advocate.

Converts a structured video script (scenes with narration + on-screen text) into
a real .mp4 file. Uses:
  - Pillow    → render each scene as an RGB image frame
  - gTTS      → text-to-speech narration (Google TTS, requires internet)
  - moviepy   → assemble frames + audio into MP4

No paid external API keys required.
"""

from __future__ import annotations

import io
import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------

RC_PURPLE      = (123,  47, 190)   # #7B2FBE
RC_DARK        = ( 26,  10,  46)   # #1A0A2E
RC_DARK2       = ( 45,  27,  94)   # #2D1B5E
RC_BLUE        = ( 59, 111, 222)   # #3B6FDE
RC_WHITE       = (255, 255, 255)
RC_SUBTEXT     = (196, 181, 232)   # #C4B5E8
RC_CODE_BG     = ( 22,  27,  34)   # #161B22
RC_CODE_FG     = (230, 237, 243)   # #E6EDF3
RC_GREEN_DOT   = ( 39, 201,  63)
RC_YELLOW_DOT  = (255, 189,  46)
RC_RED_DOT     = (255,  95,  86)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pillow font: use default bitmap font (no external font files required)
# For better quality, truetype fonts can be loaded if available.
try:
    from PIL import ImageFont
    _FONT_PATH = None
    # Try common system font paths
    for _candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(_candidate).exists():
            _FONT_PATH = _candidate
            break
    _FONT_REGULAR_PATH = _FONT_PATH  # fallback: same as bold
    for _candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]:
        if Path(_candidate).exists():
            _FONT_REGULAR_PATH = _candidate
            break
    _MONO_PATH = None
    for _candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        if Path(_candidate).exists():
            _MONO_PATH = _candidate
            break
except ImportError:
    _FONT_PATH = None
    _FONT_REGULAR_PATH = None
    _MONO_PATH = None


def _load_font(size: int, bold: bool = False, mono: bool = False):
    """Load a PIL font at the given size, falling back to default."""
    from PIL import ImageFont
    path = (_MONO_PATH if mono else (_FONT_PATH if bold else _FONT_REGULAR_PATH))
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------------------
# Scene data model
# ---------------------------------------------------------------------------

@dataclass
class Scene:
    """A single scene in a video script."""
    title: str = ""                  # Short scene label (e.g. "Hook", "Install SDK")
    narration: str = ""              # Spoken narration text
    on_screen_text: str = ""         # Large text displayed on screen
    body_text: str = ""              # Smaller supporting text
    code: str = ""                   # Optional code snippet
    duration: float = 5.0            # Seconds (overridden by TTS length if available)
    style: str = "dark_purple"       # Visual style key
    slide_type: str = "text"         # "text" | "code" | "title" | "cta"


def parse_script(script_json: list[dict] | str) -> list[Scene]:
    """
    Parse a script from either:
      - A JSON array of scene dicts
      - A raw markdown/text script (parsed heuristically)

    Expected JSON format per scene:
      {
        "title": "Hook",
        "narration": "...",
        "on_screen_text": "...",
        "body_text": "...",      # optional
        "code": "...",           # optional
        "duration": 5.0,         # optional, seconds
        "style": "dark_purple",  # optional
        "slide_type": "text"     # optional
      }
    """
    if isinstance(script_json, str):
        try:
            data = json.loads(script_json)
        except json.JSONDecodeError:
            data = _parse_markdown_script(script_json)
    else:
        data = script_json

    scenes = []
    for d in data:
        scenes.append(Scene(
            title=d.get("title", ""),
            narration=d.get("narration", d.get("on_screen_text", "")),
            on_screen_text=d.get("on_screen_text", d.get("title", "")),
            body_text=d.get("body_text", ""),
            code=d.get("code", ""),
            duration=float(d.get("duration", 5.0)),
            style=d.get("style", "dark_purple"),
            slide_type=d.get("slide_type", "code" if d.get("code") else "text"),
        ))
    return scenes


def _parse_markdown_script(md: str) -> list[dict]:
    """
    Heuristic parser: extract scenes from a markdown storyboard.
    Looks for ### SCENE headings and pulls narration / on-screen text.
    """
    scenes = []
    blocks = re.split(r"(?=###\s+SCENE)", md, flags=re.IGNORECASE)
    for block in blocks:
        if not block.strip():
            continue
        title_match = re.search(r"###\s+SCENE\s+\d+\s*[—-]\s*(.+?)(?:\(|$)", block)
        title = title_match.group(1).strip() if title_match else "Scene"

        narration = ""
        narration_match = re.search(r"\*\*Narration\*\*:\s*(.+?)(?:\n\*\*|\Z)", block, re.DOTALL)
        if narration_match:
            narration = narration_match.group(1).strip().strip("[]")

        on_screen = title
        on_screen_match = re.search(r"\*\*On Screen\*\*:\s*(.+?)(?:\n\*\*|\Z)", block, re.DOTALL)
        if on_screen_match:
            on_screen = on_screen_match.group(1).strip().strip("[]")

        code_match = re.search(r"```(?:\w+)?\n(.+?)```", block, re.DOTALL)
        code = code_match.group(1) if code_match else ""

        scenes.append({
            "title": title,
            "narration": narration or on_screen,
            "on_screen_text": on_screen,
            "code": code,
            "slide_type": "code" if code else "text",
        })
    return scenes if scenes else [{"title": "Content", "on_screen_text": md[:200], "narration": md[:500]}]


# ---------------------------------------------------------------------------
# Frame rendering
# ---------------------------------------------------------------------------

PALETTE = {
    "dark_purple": {
        "bg":      RC_DARK,
        "bg2":     RC_DARK2,
        "text":    RC_WHITE,
        "subtext": RC_SUBTEXT,
        "accent":  RC_PURPLE,
    },
    "gradient": {
        "bg":      RC_PURPLE,
        "bg2":     RC_BLUE,
        "text":    RC_WHITE,
        "subtext": (224, 208, 255),
        "accent":  (255, 215, 0),
    },
    "light": {
        "bg":      RC_WHITE,
        "bg2":     (243, 238, 255),
        "text":    RC_DARK,
        "subtext": (75,  59, 110),
        "accent":  RC_PURPLE,
    },
    "code_card": {
        "bg":      (13,  17,  23),
        "bg2":     RC_CODE_BG,
        "text":    RC_CODE_FG,
        "subtext": (139, 148, 158),
        "accent":  RC_PURPLE,
    },
}


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def render_frame(scene: Scene, width: int = 1280, height: int = 720) -> "Image.Image":
    """Render a single scene to a Pillow RGB image."""
    from PIL import Image, ImageDraw

    p = PALETTE.get(scene.style, PALETTE["dark_purple"])

    # --- Background gradient (vertical, top→bottom) ---
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        color = _lerp_color(p["bg"], p["bg2"], t)
        draw.line([(0, y), (width, y)], fill=color)

    # --- Bottom accent bar (purple→blue gradient) ---
    bar_h = max(5, height // 90)
    for x in range(width):
        t = x / width
        color = _lerp_color(RC_PURPLE, RC_BLUE, t)
        draw.rectangle([(x, height - bar_h), (x + 1, height)], fill=color)

    pad = int(width * 0.08)

    # --- RevenueCat logo (top-left) ---
    logo_font = _load_font(max(18, width // 55), bold=True)
    draw.text((pad, int(height * 0.07)), "RevenueCat", font=logo_font, fill=p["accent"])

    if scene.slide_type == "code" and scene.code:
        _render_code_layout(draw, img, scene, width, height, pad, p)
    elif scene.slide_type == "title":
        _render_title_layout(draw, scene, width, height, pad, p)
    elif scene.slide_type == "cta":
        _render_cta_layout(draw, scene, width, height, pad, p)
    else:
        _render_text_layout(draw, scene, width, height, pad, p)

    return img


def _wrapped_lines(text: str, font, max_width: int, draw) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _render_text_layout(draw, scene: Scene, w: int, h: int, pad: int, p: dict):
    """Standard text slide: big headline + optional body."""
    # Headline
    font_size = max(36, min(80, w // 14))
    font = _load_font(font_size, bold=True)
    lines = _wrapped_lines(scene.on_screen_text, font, w - pad * 2, draw)
    line_h = int(font_size * 1.3)
    total_h = len(lines) * line_h
    y = (h - total_h) // 2 - (int(h * 0.05) if scene.body_text else 0)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=p["text"])
        y += line_h

    # Body
    if scene.body_text:
        body_font_size = max(20, w // 40)
        body_font = _load_font(body_font_size)
        body_lines = _wrapped_lines(scene.body_text, body_font, w - pad * 2, draw)
        body_y = y + int(h * 0.03)
        body_line_h = int(body_font_size * 1.4)
        for line in body_lines:
            bbox = draw.textbbox((0, 0), line, font=body_font)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x, body_y), line, font=body_font, fill=p["subtext"])
            body_y += body_line_h


def _render_title_layout(draw, scene: Scene, w: int, h: int, pad: int, p: dict):
    """Full-screen title card with accent line."""
    # Accent line
    draw.rectangle([(pad, h // 2 - 4), (w - pad, h // 2)], fill=p["accent"])

    font_size = max(48, min(96, w // 10))
    font = _load_font(font_size, bold=True)
    lines = _wrapped_lines(scene.on_screen_text, font, w - pad * 2, draw)
    line_h = int(font_size * 1.25)
    y = h // 2 - (len(lines) * line_h) // 2 + int(h * 0.06)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=p["text"])
        y += line_h

    if scene.body_text:
        sub_font = _load_font(max(20, w // 45))
        sub_lines = _wrapped_lines(scene.body_text, sub_font, w - pad * 2, draw)
        sub_y = y + int(h * 0.04)
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x, sub_y), line, font=sub_font, fill=p["subtext"])
            sub_y += int(max(20, w // 45) * 1.4)


def _render_cta_layout(draw, scene: Scene, w: int, h: int, pad: int, p: dict):
    """CTA slide with button-style highlight."""
    _render_text_layout(draw, scene, w, h, pad, p)
    # CTA button outline box
    btn_text = scene.body_text or "Try RevenueCat free →"
    btn_font = _load_font(max(22, w // 38), bold=True)
    btn_lines = _wrapped_lines(btn_text, btn_font, w - pad * 4, draw)
    btn_line = btn_lines[0] if btn_lines else btn_text
    bbox = draw.textbbox((0, 0), btn_line, font=btn_font)
    bw = (bbox[2] - bbox[0]) + 60
    bh = (bbox[3] - bbox[1]) + 30
    bx = (w - bw) // 2
    by = int(h * 0.72)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=10, fill=RC_PURPLE)
    draw.text((bx + 30, by + 15), btn_line, font=btn_font, fill=RC_WHITE)


def _render_code_layout(draw, img, scene: Scene, w: int, h: int, pad: int, p: dict):
    """Code card layout: headline top, terminal code block below."""
    from PIL import Image, ImageDraw

    # Headline (shorter, at top)
    font_size = max(28, min(56, w // 20))
    font = _load_font(font_size, bold=True)
    lines = _wrapped_lines(scene.on_screen_text, font, w - pad * 2, draw)
    line_h = int(font_size * 1.25)
    y = int(h * 0.18)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=p["text"])
        y += line_h

    # Code block background
    code_lines = scene.code.strip().split("\n")[:10]
    code_font_size = max(14, w // 65)
    code_font = _load_font(code_font_size, mono=True)
    code_line_h = int(code_font_size * 1.65)
    block_w = int(w * 0.84)
    block_h = len(code_lines) * code_line_h + 50
    block_x = (w - block_w) // 2
    block_y = int(h * 0.38)

    # Draw code block
    draw.rounded_rectangle(
        [(block_x, block_y), (block_x + block_w, block_y + block_h)],
        radius=10, fill=RC_CODE_BG, outline=(48, 54, 61), width=1,
    )
    # Terminal dots
    for i, dot_color in enumerate([RC_RED_DOT, RC_YELLOW_DOT, RC_GREEN_DOT]):
        cx = block_x + 16 + i * 18
        cy = block_y + 16
        draw.ellipse([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=dot_color)

    # Code text
    for i, code_line in enumerate(code_lines):
        ty = block_y + 38 + i * code_line_h
        draw.text((block_x + 18, ty), code_line, font=code_font, fill=RC_CODE_FG)


# ---------------------------------------------------------------------------
# TTS narration
# ---------------------------------------------------------------------------

def generate_narration(narration_text: str, output_path: Path) -> float:
    """
    Generate an MP3 narration file using gTTS.
    Returns duration in seconds (estimated from word count if audio fails).
    """
    # Estimate duration: average speaking rate ~150 words/min
    word_count = len(narration_text.split())
    estimated_duration = max(2.0, word_count / 2.5)  # 150 wpm → 2.5 words/s

    if not narration_text.strip():
        return estimated_duration

    try:
        from gtts import gTTS
        tts = gTTS(text=narration_text, lang="en", slow=False)
        tts.save(str(output_path))
        # Try to get actual duration via moviepy
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(str(output_path)) as audio:
                return audio.duration
        except Exception:
            return estimated_duration
    except Exception:
        # TTS failed (network, etc.) — return silent duration
        return estimated_duration


# ---------------------------------------------------------------------------
# Main render pipeline
# ---------------------------------------------------------------------------

def render_video(
    scenes: list[Scene],
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    use_tts: bool = True,
    default_scene_duration: float = 5.0,
    transition_duration: float = 0.0,
) -> dict[str, Any]:
    """
    Render a list of scenes into an MP4 file.

    Returns a dict with file_path, duration, scene_count.
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

    tmp_dir = OUTPUT_DIR / "_tmp_frames"
    tmp_dir.mkdir(exist_ok=True)

    clips = []
    total_duration = 0.0

    for idx, scene in enumerate(scenes):
        # 1. Render frame
        frame_img = render_frame(scene, width, height)
        frame_path = tmp_dir / f"frame_{idx:03d}.png"
        frame_img.save(str(frame_path))

        # 2. Generate narration audio
        audio_path = tmp_dir / f"narration_{idx:03d}.mp3"
        narration = scene.narration.strip()

        if use_tts and narration:
            dur = generate_narration(narration, audio_path)
        else:
            dur = scene.duration if scene.duration > 0 else default_scene_duration

        dur = max(2.0, dur)  # minimum 2 seconds per slide

        # 3. Build clip
        clip = ImageClip(str(frame_path), duration=dur)

        if use_tts and narration and audio_path.exists():
            try:
                audio = AudioFileClip(str(audio_path)).with_duration(dur)
                clip = clip.with_audio(audio)
            except Exception:
                pass  # no audio for this scene

        clips.append(clip)
        total_duration += dur

    if not clips:
        return {"success": False, "error": "No scenes to render."}

    # 4. Concatenate and write
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    final.close()
    for clip in clips:
        clip.close()

    # Cleanup temp files
    for f in tmp_dir.iterdir():
        f.unlink()
    tmp_dir.rmdir()

    return {
        "success": True,
        "file_path": str(output_path),
        "duration_seconds": round(total_duration, 1),
        "scene_count": len(scenes),
        "resolution": f"{width}×{height}",
        "fps": fps,
    }
