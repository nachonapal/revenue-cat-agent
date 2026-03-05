"""
Tool definitions and handlers for the RevenueCat Developer Advocate Agent.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Tool schemas (raw JSON for manual agentic loop)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    # Server-side tools (Anthropic-hosted, no client execution needed)
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},

    # Custom client-side tools
    {
        "name": "save_content",
        "description": (
            "Save generated content (blog posts, tutorials, guides, scripts, experiment "
            "proposals, product feedback reports) to disk as a file. Use this after "
            "creating any content to persist it. Returns the saved file path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "File name with extension, e.g. 'getting-started-revenuecat-ios.md' "
                        "or 'experiment-paywall-cta-q1-2026.md'. Use kebab-case."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Full content to save to the file.",
                },
                "content_type": {
                    "type": "string",
                    "enum": [
                        "blog_post",
                        "tutorial",
                        "code_sample",
                        "video_script",
                        "video_storyboard",
                        "social_graphic",
                        "experiment_plan",
                        "product_feedback",
                        "community_post",
                        "application",
                        "other",
                    ],
                    "description": "Category of content being saved.",
                },
            },
            "required": ["filename", "content", "content_type"],
        },
    },
    {
        "name": "submit_job_application",
        "description": (
            "Submit an application to the RevenueCat Agentic AI Developer Advocate position "
            "(job ID: 998a9cef-3ea5-45c2-885b-8a00c4eeb149) via the Ashby ATS API. "
            "This tool fetches the application form, fills it out with the provided details, "
            "and submits it. Use this when the user asks to apply to the job."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "applicant_name": {
                    "type": "string",
                    "description": "Full name of the applicant / agent name.",
                },
                "applicant_email": {
                    "type": "string",
                    "description": "Contact email for the application.",
                },
                "cover_letter": {
                    "type": "string",
                    "description": (
                        "Compelling cover letter that demonstrates the agent's capabilities, "
                        "understanding of RevenueCat, and concrete plans for the role. "
                        "Should be 400-600 words, technical, and showcase real value."
                    ),
                },
                "demo_description": {
                    "type": "string",
                    "description": (
                        "Description of a concrete demo, work sample, or capability showcase. "
                        "Could be a link to a GitHub repo, a sample blog post, an experiment "
                        "proposal, or a product feedback report."
                    ),
                },
                "additional_answers": {
                    "type": "object",
                    "description": (
                        "Answers to any additional application questions as key-value pairs "
                        "where keys are field IDs or question names."
                    ),
                },
            },
            "required": ["applicant_name", "applicant_email", "cover_letter"],
        },
    },
    {
        "name": "generate_experiment_plan",
        "description": (
            "Generate a structured growth experiment plan for RevenueCat's developer adoption. "
            "This produces a complete experiment specification including hypothesis, success "
            "metrics, implementation steps, and expected impact. The result is returned as "
            "structured data AND saved to disk."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "experiment_name": {
                    "type": "string",
                    "description": "Short descriptive name for the experiment.",
                },
                "hypothesis": {
                    "type": "string",
                    "description": "The hypothesis being tested.",
                },
                "target_metric": {
                    "type": "string",
                    "description": (
                        "Primary metric to improve, e.g. 'Time to first purchase event', "
                        "'Documentation page bounce rate', 'SDK install to active usage rate'."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or constraints for the experiment.",
                },
            },
            "required": ["experiment_name", "hypothesis", "target_metric"],
        },
    },
    {
        "name": "generate_social_graphic",
        "description": (
            "Generate a social media graphic as an SVG file. Use for Twitter/X cards, "
            "LinkedIn posts, Instagram squares, and YouTube thumbnails. The SVG uses "
            "RevenueCat brand colors and is saved to disk. Returns the file path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["twitter", "linkedin", "instagram", "youtube_thumbnail"],
                    "description": (
                        "Target platform. Determines canvas size: "
                        "twitter=1200×628, linkedin=1200×627, "
                        "instagram=1080×1080, youtube_thumbnail=1280×720."
                    ),
                },
                "headline": {
                    "type": "string",
                    "description": "Main headline text. Keep under 60 characters for readability.",
                },
                "body": {
                    "type": "string",
                    "description": (
                        "Supporting body text (1-2 sentences). "
                        "Optional — leave empty for minimal/bold designs."
                    ),
                },
                "cta": {
                    "type": "string",
                    "description": (
                        "Call-to-action label, e.g. 'Read more', 'Try it free', "
                        "'Watch the tutorial'. Optional."
                    ),
                },
                "style": {
                    "type": "string",
                    "enum": ["dark_purple", "light", "code_card", "gradient"],
                    "description": (
                        "Visual style. dark_purple=RevenueCat brand dark; "
                        "light=white/clean; code_card=terminal-style dark with code; "
                        "gradient=purple-to-blue gradient."
                    ),
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Output filename without extension, e.g. "
                        "'storekit2-migration-twitter'. Will be saved as .svg."
                    ),
                },
                "code_snippet": {
                    "type": "string",
                    "description": (
                        "Optional code snippet to display (for code_card style). "
                        "Keep under 8 lines."
                    ),
                },
            },
            "required": ["platform", "headline", "style", "filename"],
        },
    },
    {
        "name": "generate_video_storyboard",
        "description": (
            "Generate a complete video storyboard for a social media or YouTube video. "
            "Produces a structured scene-by-scene breakdown with on-screen text, "
            "narration script, visual direction, and B-roll suggestions. "
            "Saved as a markdown file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Video title.",
                },
                "platform": {
                    "type": "string",
                    "enum": ["youtube", "twitter", "linkedin", "instagram_reels", "tiktok"],
                    "description": "Target platform — determines length and format style.",
                },
                "topic": {
                    "type": "string",
                    "description": (
                        "What the video is about, e.g. "
                        "'How to add a paywall to a Flutter app in 5 minutes'."
                    ),
                },
                "target_audience": {
                    "type": "string",
                    "description": (
                        "Who the video is for, e.g. 'indie iOS developers', "
                        "'mobile startup CTOs', 'Flutter beginners'."
                    ),
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main points to cover (3-7 items).",
                },
                "duration_seconds": {
                    "type": "integer",
                    "description": "Target duration in seconds (e.g. 60, 180, 600).",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename without extension.",
                },
            },
            "required": ["title", "platform", "topic", "target_audience", "filename"],
        },
    },
    {
        "name": "render_video_from_script",
        "description": (
            "Render a complete .mp4 video from a structured script. "
            "Each scene becomes a slide with on-screen text; narration is spoken aloud "
            "via text-to-speech (gTTS). The output is a real MP4 file saved to disk. "
            "Use this after writing a video script to produce the actual video."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Output filename without extension, e.g. 'revenuecat-storekit2-intro'. Will be saved as .mp4.",
                },
                "scenes": {
                    "type": "array",
                    "description": (
                        "Ordered list of scenes. Each scene is an object with: "
                        "title (str), on_screen_text (str, shown large on screen), "
                        "narration (str, spoken aloud), body_text (str, smaller supporting text, optional), "
                        "code (str, code snippet for code slides, optional), "
                        "duration (float, seconds, optional — auto-set by TTS length), "
                        "slide_type (str: 'text'|'title'|'code'|'cta', optional), "
                        "style (str: 'dark_purple'|'gradient'|'light'|'code_card', optional)."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "on_screen_text": {"type": "string"},
                            "narration": {"type": "string"},
                            "body_text": {"type": "string"},
                            "code": {"type": "string"},
                            "duration": {"type": "number"},
                            "slide_type": {
                                "type": "string",
                                "enum": ["text", "title", "code", "cta"],
                            },
                            "style": {
                                "type": "string",
                                "enum": ["dark_purple", "gradient", "light", "code_card"],
                            },
                        },
                        "required": ["on_screen_text", "narration"],
                    },
                },
                "resolution": {
                    "type": "string",
                    "enum": ["1280x720", "1920x1080", "1080x1080", "1080x1920"],
                    "description": (
                        "Video resolution. "
                        "1280x720=YouTube/Twitter (16:9 HD), "
                        "1920x1080=YouTube (Full HD), "
                        "1080x1080=Instagram square, "
                        "1080x1920=Reels/TikTok (9:16 vertical)."
                    ),
                },
                "use_tts": {
                    "type": "boolean",
                    "description": (
                        "Whether to generate spoken narration via text-to-speech. "
                        "Requires internet access. Defaults to true."
                    ),
                },
            },
            "required": ["filename", "scenes"],
        },
    },
    {
        "name": "generate_product_feedback",
        "description": (
            "Generate a structured product feedback report for RevenueCat's product team. "
            "Synthesizes developer community signals, SDK usability observations, and "
            "competitive analysis into actionable product improvement recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "area": {
                    "type": "string",
                    "description": (
                        "Product area to evaluate, e.g. 'iOS SDK API design', "
                        "'Paywalls builder UX', 'Documentation onboarding', "
                        "'Experiments setup flow'."
                    ),
                },
                "observations": {
                    "type": "string",
                    "description": (
                        "Key observations from community research, developer interviews, "
                        "GitHub issues, support tickets, or direct usage."
                    ),
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Estimated priority for the product team.",
                },
            },
            "required": ["area", "observations"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution handlers
# ---------------------------------------------------------------------------

def save_content(filename: str, content: str, content_type: str) -> dict[str, Any]:
    """Save generated content to the outputs directory."""
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    file_path = OUTPUT_DIR / safe_filename
    file_path.write_text(content, encoding="utf-8")

    metadata = {
        "file_path": str(file_path),
        "filename": safe_filename,
        "content_type": content_type,
        "size_bytes": len(content.encode("utf-8")),
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    # Write metadata sidecar
    meta_path = OUTPUT_DIR / f"{safe_filename}.meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "success": True,
        "message": f"Content saved to {file_path}",
        **metadata,
    }


def submit_job_application(
    applicant_name: str,
    applicant_email: str,
    cover_letter: str,
    demo_description: str = "",
    additional_answers: dict | None = None,
) -> dict[str, Any]:
    """
    Submit an application to RevenueCat's Agentic AI Developer Advocate role
    via the Ashby ATS API.

    Job posting ID: 998a9cef-3ea5-45c2-885b-8a00c4eeb149
    """
    JOB_POSTING_ID = "998a9cef-3ea5-45c2-885b-8a00c4eeb149"
    ASHBY_BASE_URL = "https://api.ashbyhq.com"
    HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://jobs.ashbyhq.com",
        "Referer": f"https://jobs.ashbyhq.com/revenuecat/{JOB_POSTING_ID}",
        "User-Agent": "RevenueCat-AI-Developer-Advocate-Agent/1.0",
    }

    # Step 1: Fetch the form definition
    try:
        with httpx.Client(timeout=30.0) as client:
            form_response = client.get(
                f"{ASHBY_BASE_URL}/applicationForm.load",
                params={"jobPostingId": JOB_POSTING_ID},
                headers=HEADERS,
            )
            form_response.raise_for_status()
            form_data = form_response.json()
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"Failed to load application form: {e.response.status_code} {e.response.text}",
            "step": "form_load",
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Network error loading form: {str(e)}",
            "step": "form_load",
        }

    # Step 2: Build the application payload
    # Ashby uses _systemfield_ prefix for standard fields
    application_form: dict[str, Any] = {
        "_systemfield_name": applicant_name,
        "_systemfield_email": applicant_email,
        "_systemfield_resume_text": cover_letter,
    }

    # Map known custom fields if they exist in the form
    fields = form_data.get("data", {}).get("form", {}).get("fields", [])
    field_map = {field.get("label", "").lower(): field.get("id") for field in fields}

    cover_letter_field = field_map.get("cover letter") or field_map.get("why this role")
    if cover_letter_field:
        application_form[cover_letter_field] = cover_letter

    demo_field = field_map.get("demo") or field_map.get("work sample") or field_map.get("portfolio")
    if demo_field and demo_description:
        application_form[demo_field] = demo_description

    # Add any additional answers
    if additional_answers:
        for key, value in additional_answers.items():
            # Try to find matching field ID
            matching_field = field_map.get(key.lower())
            if matching_field:
                application_form[matching_field] = value
            else:
                application_form[key] = value

    # Step 3: Submit the application
    payload = {
        "jobPostingId": JOB_POSTING_ID,
        "applicationForm": application_form,
    }

    # Save application to disk before submitting
    application_content = f"""# RevenueCat Job Application
**Position**: Agentic AI Developer Advocate
**Job ID**: {JOB_POSTING_ID}
**Applicant**: {applicant_name}
**Email**: {applicant_email}
**Submitted**: {datetime.utcnow().isoformat()}Z

## Cover Letter

{cover_letter}

## Demo / Work Sample

{demo_description}

## Additional Answers

{json.dumps(additional_answers or {}, indent=2)}
"""
    save_content(
        filename=f"application-revenuecat-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.md",
        content=application_content,
        content_type="application",
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            submit_response = client.post(
                f"{ASHBY_BASE_URL}/applicationForm.submit",
                json=payload,
                headers=HEADERS,
            )
            submit_response.raise_for_status()
            result = submit_response.json()

        return {
            "success": True,
            "message": "Application submitted successfully to RevenueCat",
            "applicant": applicant_name,
            "email": applicant_email,
            "job_posting_id": JOB_POSTING_ID,
            "response": result,
        }

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"Submission failed: {e.response.status_code} {e.response.text}",
            "step": "submit",
            "payload_saved": True,
            "note": "Application content was saved locally. Submit manually via the Ashby form.",
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Network error during submission: {str(e)}",
            "step": "submit",
            "payload_saved": True,
            "note": "Application content was saved locally. Submit manually via the Ashby form.",
        }


def generate_experiment_plan(
    experiment_name: str,
    hypothesis: str,
    target_metric: str,
    context: str = "",
) -> dict[str, Any]:
    """Generate and save an experiment plan."""
    # This tool handler just returns structured data;
    # the agent uses its own reasoning to fill the plan details.
    plan = {
        "name": experiment_name,
        "hypothesis": hypothesis,
        "target_metric": target_metric,
        "context": context,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "draft",
    }

    return {
        "success": True,
        "message": f"Experiment plan template created for: {experiment_name}",
        "plan": plan,
        "instruction": (
            "Use this structured data to write a complete experiment specification document. "
            "Include: success criteria, sample size requirements, control vs treatment, "
            "implementation timeline, and business impact estimate."
        ),
    }


def generate_product_feedback(
    area: str,
    observations: str,
    priority: str = "medium",
) -> dict[str, Any]:
    """Generate a product feedback report structure."""
    return {
        "success": True,
        "message": f"Product feedback structure created for: {area}",
        "feedback": {
            "area": area,
            "observations": observations,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
        "instruction": (
            "Use this to write a complete product feedback report. Include: "
            "problem statement, developer impact, current workarounds, "
            "proposed solution, competitive analysis, and priority justification."
        ),
    }


def render_video_from_script(
    filename: str,
    scenes: list[dict],
    resolution: str = "1280x720",
    use_tts: bool = True,
) -> dict[str, Any]:
    """Render a structured scene list into a real .mp4 video."""
    from agent.tools.video_renderer import parse_script, render_video as _render_video

    # Parse resolution
    try:
        w, h = (int(x) for x in resolution.split("x"))
    except Exception:
        w, h = 1280, 720

    safe_name = filename.replace("/", "_").replace("\\", "_")
    if not safe_name.endswith(".mp4"):
        safe_name += ".mp4"
    output_path = OUTPUT_DIR / safe_name

    parsed_scenes = parse_script(scenes)

    if not parsed_scenes:
        return {"success": False, "error": "No scenes could be parsed from the provided script."}

    result = _render_video(
        scenes=parsed_scenes,
        output_path=output_path,
        width=w,
        height=h,
        use_tts=use_tts,
    )

    if result.get("success"):
        result["filename"] = safe_name
        result["content_type"] = "video"
        result["note"] = (
            f"MP4 saved to {output_path}. "
            "Play with any video player or upload directly to social platforms."
        )
    return result


def generate_social_graphic(
    platform: str,
    headline: str,
    style: str,
    filename: str,
    body: str = "",
    cta: str = "",
    code_snippet: str = "",
) -> dict[str, Any]:
    """Generate a social media graphic as an SVG and save it."""

    SIZES = {
        "twitter": (1200, 628),
        "linkedin": (1200, 627),
        "instagram": (1080, 1080),
        "youtube_thumbnail": (1280, 720),
    }
    COLORS = {
        "dark_purple": {
            "bg": "#1A0A2E",
            "bg2": "#2D1B5E",
            "text": "#FFFFFF",
            "subtext": "#C4B5E8",
            "accent": "#9B72CF",
            "cta_bg": "#7B2FBE",
            "cta_text": "#FFFFFF",
            "logo": "#9B72CF",
        },
        "light": {
            "bg": "#FFFFFF",
            "bg2": "#F3EEFF",
            "text": "#1A0A2E",
            "subtext": "#4B3B6E",
            "accent": "#7B2FBE",
            "cta_bg": "#7B2FBE",
            "cta_text": "#FFFFFF",
            "logo": "#7B2FBE",
        },
        "code_card": {
            "bg": "#0D1117",
            "bg2": "#161B22",
            "text": "#E6EDF3",
            "subtext": "#8B949E",
            "accent": "#9B72CF",
            "cta_bg": "#7B2FBE",
            "cta_text": "#FFFFFF",
            "logo": "#9B72CF",
        },
        "gradient": {
            "bg": "#7B2FBE",
            "bg2": "#3B6FDE",
            "text": "#FFFFFF",
            "subtext": "#E0D0FF",
            "accent": "#FFD700",
            "cta_bg": "#FFFFFF",
            "cta_text": "#7B2FBE",
            "logo": "#FFFFFF",
        },
    }

    w, h = SIZES.get(platform, (1200, 628))
    c = COLORS.get(style, COLORS["dark_purple"])

    # Gradient definition for bg
    bg_gradient = (
        f'<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c["bg"]}"/>'
        f'<stop offset="100%" stop-color="{c["bg2"]}"/>'
        f'</linearGradient>'
        f'<linearGradient id="accent_bar" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="#7B2FBE"/>'
        f'<stop offset="100%" stop-color="#3B6FDE"/>'
        f'</linearGradient>'
        f'</defs>'
    )

    # Wrap text into lines (simple word-wrap at ~max_chars per line)
    def wrap(text: str, max_chars: int) -> list[str]:
        words = text.split()
        lines, current = [], ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # Headline sizing
    headline_font = max(32, min(72, int(w * 0.055)))
    headline_max_chars = int(w / (headline_font * 0.52))
    headline_lines = wrap(headline, headline_max_chars)

    body_font = max(20, int(w * 0.023))
    body_max_chars = int(w / (body_font * 0.54))
    body_lines = wrap(body, body_max_chars) if body else []

    # Calculate vertical layout
    padding = int(w * 0.07)
    logo_y = int(h * 0.1)
    headline_start_y = int(h * 0.35)
    line_h = int(headline_font * 1.25)
    body_start_y = headline_start_y + len(headline_lines) * line_h + int(h * 0.04)
    cta_y = body_start_y + (len(body_lines) * int(body_font * 1.4) if body_lines else 0) + int(h * 0.05)

    # Build headline SVG elements
    headline_svg = ""
    for i, line in enumerate(headline_lines):
        y = headline_start_y + i * line_h
        headline_svg += (
            f'<text x="{w // 2}" y="{y}" '
            f'font-family="system-ui,-apple-system,sans-serif" '
            f'font-size="{headline_font}" font-weight="800" '
            f'fill="{c["text"]}" text-anchor="middle">{line}</text>\n'
        )

    # Body text
    body_svg = ""
    if body_lines:
        bline_h = int(body_font * 1.45)
        for i, line in enumerate(body_lines):
            y = body_start_y + i * bline_h
            body_svg += (
                f'<text x="{w // 2}" y="{y}" '
                f'font-family="system-ui,-apple-system,sans-serif" '
                f'font-size="{body_font}" font-weight="400" '
                f'fill="{c["subtext"]}" text-anchor="middle">{line}</text>\n'
            )

    # CTA button
    cta_svg = ""
    if cta:
        btn_w = min(260, int(len(cta) * body_font * 0.65) + 60)
        btn_h = int(body_font * 1.9)
        btn_x = (w - btn_w) // 2
        cta_svg = (
            f'<rect x="{btn_x}" y="{cta_y}" width="{btn_w}" height="{btn_h}" '
            f'rx="8" fill="{c["cta_bg"]}"/>\n'
            f'<text x="{w // 2}" y="{cta_y + btn_h // 2 + int(body_font * 0.35)}" '
            f'font-family="system-ui,-apple-system,sans-serif" '
            f'font-size="{body_font}" font-weight="700" '
            f'fill="{c["cta_text"]}" text-anchor="middle">{cta}</text>\n'
        )

    # Code snippet block (code_card style)
    code_svg = ""
    if code_snippet and style == "code_card":
        lines = code_snippet.strip().split("\n")[:8]
        code_font = max(14, int(w * 0.018))
        code_line_h = int(code_font * 1.6)
        block_h = len(lines) * code_line_h + 40
        block_w = int(w * 0.8)
        block_x = (w - block_w) // 2
        block_y = int(h * 0.42)
        code_svg = (
            f'<rect x="{block_x}" y="{block_y}" width="{block_w}" height="{block_h}" '
            f'rx="10" fill="#161B22" stroke="#30363D" stroke-width="1"/>\n'
            f'<!-- Terminal dots -->\n'
            f'<circle cx="{block_x + 18}" cy="{block_y + 18}" r="5" fill="#FF5F56"/>\n'
            f'<circle cx="{block_x + 34}" cy="{block_y + 18}" r="5" fill="#FFBD2E"/>\n'
            f'<circle cx="{block_x + 50}" cy="{block_y + 18}" r="5" fill="#27C93F"/>\n'
        )
        for i, line in enumerate(lines):
            # Escape XML chars
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            cy = block_y + 40 + i * code_line_h
            code_svg += (
                f'<text x="{block_x + 20}" y="{cy}" '
                f'font-family="monospace" font-size="{code_font}" '
                f'fill="#E6EDF3">{safe_line}</text>\n'
            )

    # Logo / branding
    logo_font = max(16, int(w * 0.022))
    logo_svg = (
        f'<text x="{padding}" y="{logo_y}" '
        f'font-family="system-ui,-apple-system,sans-serif" '
        f'font-size="{logo_font}" font-weight="700" '
        f'fill="{c["logo"]}">RevenueCat</text>\n'
    )

    # Bottom accent bar
    bar_h = max(5, int(h * 0.008))
    accent_bar = (
        f'<rect x="0" y="{h - bar_h}" width="{w}" height="{bar_h}" '
        f'fill="url(#accent_bar)"/>\n'
    )

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  {bg_gradient}
  <!-- Background -->
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <!-- Logo -->
  {logo_svg}
  <!-- Headline -->
  {headline_svg}
  <!-- Body -->
  {body_svg}
  <!-- Code block -->
  {code_svg}
  <!-- CTA -->
  {cta_svg}
  <!-- Accent bar -->
  {accent_bar}
</svg>"""

    safe_name = filename.replace("/", "_").replace("\\", "_")
    if not safe_name.endswith(".svg"):
        safe_name += ".svg"

    file_path = OUTPUT_DIR / safe_name
    file_path.write_text(svg, encoding="utf-8")

    return {
        "success": True,
        "message": f"Social graphic saved to {file_path}",
        "file_path": str(file_path),
        "filename": safe_name,
        "platform": platform,
        "size": f"{w}×{h}",
        "style": style,
        "content_type": "social_graphic",
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "note": (
            "SVG file saved. Open in a browser or vector editor to preview. "
            "Convert to PNG with: inkscape --export-png=out.png graphic.svg  "
            "or: cairosvg graphic.svg -o out.png"
        ),
    }


def generate_video_storyboard(
    title: str,
    platform: str,
    topic: str,
    target_audience: str,
    filename: str,
    key_points: list[str] | None = None,
    duration_seconds: int | None = None,
) -> dict[str, Any]:
    """Generate a structured video storyboard and save it as markdown."""

    PLATFORM_DEFAULTS = {
        "youtube": {"duration": 480, "style": "Educational walkthrough, 16:9"},
        "twitter": {"duration": 60, "style": "Punchy hook, quick demo, 16:9 or square"},
        "linkedin": {"duration": 90, "style": "Professional insight, subtitles-first"},
        "instagram_reels": {"duration": 60, "style": "Visual, fast-paced, 9:16 vertical"},
        "tiktok": {"duration": 45, "style": "Hook in first 2s, trend-aware, 9:16 vertical"},
    }

    platform_info = PLATFORM_DEFAULTS.get(platform, PLATFORM_DEFAULTS["youtube"])
    target_duration = duration_seconds or platform_info["duration"]
    points = key_points or []

    nl = "\n"
    points_list = nl.join(f"- {p}" for p in points) if points else "*(Define key points in the agent task)*"

    scene_per_duration = target_duration // max(1, len(points) + 2)
    middle_scenes_parts = []
    for i, point in enumerate(points):
        scene_dur = target_duration // max(1, len(points) + 3)
        middle_scenes_parts.append(
            f"### SCENE {i + 3} — {point} (~{scene_dur}s)\n"
            f"**On Screen**: [Key text or visual for this point]\n"
            f"**Narration**: [What to say about: {point}]\n"
            f"**Visual Direction**: [Screen recording? Code? Animation?]\n"
            f"**B-Roll Suggestion**: [RevenueCat dashboard? SDK code? Docs?]\n"
            f"\n---\n"
        )
    middle_scenes = nl.join(middle_scenes_parts) if middle_scenes_parts else (
        "### SCENES 3-N — Main Content\n*(Add scenes for each key point)*\n\n---\n"
    )

    storyboard_md = f"""# Video Storyboard: {title}

**Platform**: {platform.replace("_", " ").title()}
**Topic**: {topic}
**Target Audience**: {target_audience}
**Target Duration**: {target_duration}s (~{target_duration // 60}m {target_duration % 60}s)
**Format Style**: {platform_info["style"]}
**Created**: {datetime.utcnow().strftime("%Y-%m-%d")}

---

## Key Points to Cover

{points_list}

---

## Scene Breakdown

> **Instructions for the agent**: Use this template to write the full scene-by-scene
> script. Each scene should have specific on-screen text, narration, visual direction,
> and B-roll. Aim for {scene_per_duration}s per scene on average.

### SCENE 1 — Hook (~{min(8, target_duration // 8)}s)
**On Screen**: [Opening visual — should grab attention immediately]
**Narration**: [First words spoken — hook the audience in 1-2 sentences]
**Visual Direction**: [Describe the visual: screen recording, talking head, animation?]
**B-Roll Suggestion**: [What footage/screenshots support this?]

---

### SCENE 2 — Problem Setup (~{min(20, target_duration // 5)}s)
**On Screen**: [Establish the pain point or question]
**Narration**: [Describe the problem the viewer faces]
**Visual Direction**: [Code editor showing error? Developer frustration animation?]
**B-Roll Suggestion**: [StackOverflow post, GitHub issue, developer forums?]

---

{middle_scenes}

### FINAL SCENE — CTA (~{min(15, target_duration // 6)}s)
**On Screen**: [Call to action — what should the viewer do next?]
**Narration**: [Clear next step: "Try RevenueCat free at rev.cat/start"]
**Visual Direction**: [Show the landing page or sign-up screen]
**B-Roll Suggestion**: [RevenueCat homepage, pricing page, or dashboard]

---

## Production Checklist

- [ ] Script reviewed for technical accuracy
- [ ] Code examples tested and working
- [ ] RevenueCat branding follows brand guidelines
- [ ] Captions/subtitles prepared (especially for {platform})
- [ ] Thumbnail created (see `generate_social_graphic` with youtube_thumbnail)
- [ ] Description and tags prepared for {platform}
- [ ] CTA links verified

## Thumbnail Brief

**Headline suggestion**: [Bold, <7 words, addresses viewer benefit]
**Visual**: [What should be in the thumbnail — face, code, phone screenshot?]
**Text overlay**: [Short punchy text visible at small size]

---
*Generated by RevenueCat AI Developer Advocate Agent*
"""

    safe_name = filename.replace("/", "_").replace("\\", "_")
    if not safe_name.endswith(".md"):
        safe_name += ".md"

    file_path = OUTPUT_DIR / safe_name
    file_path.write_text(storyboard_md, encoding="utf-8")

    return {
        "success": True,
        "message": f"Video storyboard saved to {file_path}",
        "file_path": str(file_path),
        "filename": safe_name,
        "platform": platform,
        "duration_seconds": target_duration,
        "content_type": "video_storyboard",
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "instruction": (
            "The storyboard template is saved. Now write the full scene-by-scene content: "
            "narration script, on-screen text, visual direction for each scene. "
            "Use save_content to save the completed version as a video_script."
        ),
    }


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Dispatch tool calls to the appropriate handler."""
    handlers = {
        "save_content": save_content,
        "submit_job_application": submit_job_application,
        "generate_experiment_plan": generate_experiment_plan,
        "generate_product_feedback": generate_product_feedback,
        "generate_social_graphic": generate_social_graphic,
        "generate_video_storyboard": generate_video_storyboard,
        "render_video_from_script": render_video_from_script,
    }

    if tool_name not in handlers:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    try:
        return handlers[tool_name](**tool_input)
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution error: {str(e)}",
            "tool": tool_name,
        }
