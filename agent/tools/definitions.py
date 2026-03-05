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


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Dispatch tool calls to the appropriate handler."""
    handlers = {
        "save_content": save_content,
        "submit_job_application": submit_job_application,
        "generate_experiment_plan": generate_experiment_plan,
        "generate_product_feedback": generate_product_feedback,
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
