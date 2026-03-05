"""
RevenueCat Agentic AI Developer Advocate

Main agent using Claude Opus 4.6 with adaptive thinking, web search/fetch
(server-side), and custom tools for content creation, growth experiments,
product feedback, and autonomous job application.
"""

import json
import os
from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent.prompts import DEVELOPER_ADVOCATE_SYSTEM_PROMPT, APPLICATION_IDENTITY, INTERVIEW_SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

# Server-side tool names (handled by Anthropic, not client)
SERVER_SIDE_TOOLS = {"web_search", "web_fetch"}

JOB_POSTING_URL = (
    "https://jobs.ashbyhq.com/revenuecat/998a9cef-3ea5-45c2-885b-8a00c4eeb149"
)


class DeveloperAdvocateAgent:
    """
    Autonomous AI Developer Advocate for RevenueCat.

    Uses Claude Opus 4.6 with:
    - Adaptive thinking for complex reasoning
    - Web search + fetch (server-side, Anthropic-hosted)
    - Custom tools: save_content, submit_job_application,
      generate_experiment_plan, generate_product_feedback
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.model = "claude-opus-4-6"

    # ------------------------------------------------------------------
    # Core agentic loop
    # ------------------------------------------------------------------

    def _run_agentic_loop(
        self,
        messages: list[dict],
        system: str,
        max_iterations: int = 20,
        show_thinking: bool = False,
    ) -> str:
        """
        Manual agentic loop combining server-side tools (web search/fetch)
        and client-side custom tools.

        Returns the final text response from Claude.
        """
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            with Progress(
                SpinnerColumn(),
                TextColumn(f"[cyan]Thinking... (turn {iteration})"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task("", total=None)

                # Stream for real-time output
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=16000,
                    thinking={"type": "adaptive"},
                    system=system,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                ) as stream:
                    collected_text = []
                    collected_thinking = []

                    for event in stream:
                        if event.type == "content_block_start":
                            if event.content_block.type == "thinking":
                                pass  # handled in delta
                            elif event.content_block.type == "text":
                                pass
                        elif event.type == "content_block_delta":
                            if event.delta.type == "thinking_delta" and show_thinking:
                                collected_thinking.append(event.delta.thinking)
                            elif event.delta.type == "text_delta":
                                collected_text.append(event.delta.text)

                    response = stream.get_final_message()

            # Show thinking if requested
            if show_thinking and collected_thinking:
                thinking_text = "".join(collected_thinking)
                console.print(
                    Panel(
                        thinking_text[:2000] + ("..." if len(thinking_text) > 2000 else ""),
                        title="[dim]Internal reasoning (adaptive thinking)",
                        border_style="dim",
                    )
                )

            # Handle stop reasons
            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                # Extract final text
                final_text = "".join(
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                )
                return final_text

            elif stop_reason == "pause_turn":
                # Server-side tool loop hit iteration limit; continue
                messages.append(
                    {"role": "assistant", "content": response.content}
                )
                continue

            elif stop_reason == "tool_use":
                # Append assistant's response
                messages.append(
                    {"role": "assistant", "content": response.content}
                )

                # Execute client-side tools; server-side tools auto-handled
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input

                    if tool_name in SERVER_SIDE_TOOLS:
                        # Server-side tools should not appear here in normal flow,
                        # but if they do, skip client execution
                        console.print(
                            f"[dim]Server-side tool call: {tool_name}[/dim]"
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": "Server-side tool executed automatically.",
                            }
                        )
                        continue

                    # Execute custom tool
                    console.print(
                        f"[yellow]▶ Executing tool:[/yellow] [bold]{tool_name}[/bold]"
                    )

                    result = execute_tool(tool_name, tool_input)
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)

                    # Show result summary
                    if result.get("success"):
                        msg = result.get("message", "Done")
                        console.print(f"  [green]✓[/green] {msg}")
                        if file_path := result.get("file_path"):
                            console.print(f"  [dim]→ Saved: {file_path}[/dim]")
                    else:
                        console.print(
                            f"  [red]✗[/red] {result.get('error', 'Unknown error')}"
                        )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})

            else:
                # Unexpected stop reason
                final_text = "".join(
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                )
                return final_text

        return "Maximum iterations reached."

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def run(self, task: str, show_thinking: bool = False) -> str:
        """
        Run the agent on any developer advocate task.

        Examples:
          - "Write a tutorial on adding a paywall to a Flutter app"
          - "Design an A/B experiment to improve SDK onboarding"
          - "Give product feedback on RevenueCat's Customer Center"
        """
        console.print(
            Panel(
                f"[bold cyan]Task:[/bold cyan] {task}",
                title="RevenueCat AI Developer Advocate",
                border_style="cyan",
            )
        )

        messages = [{"role": "user", "content": task}]
        result = self._run_agentic_loop(
            messages=messages,
            system=DEVELOPER_ADVOCATE_SYSTEM_PROMPT,
            show_thinking=show_thinking,
        )

        console.print(Panel(Markdown(result), title="Result", border_style="green"))
        return result

    def create_content(self, topic: str, format: str = "blog_post") -> str:
        """
        Create developer-focused content about RevenueCat.

        Args:
            topic: The content topic, e.g. "Adding subscriptions to iOS app"
            format: One of blog_post, tutorial, video_script, community_post
        """
        task = f"""
Create high-quality developer content about: **{topic}**

Format: {format}

Requirements:
1. Research the topic using web_search and web_fetch to ensure accuracy
2. Write production-quality content with working code examples
3. Target audience: mobile app developers (iOS/Android/Flutter/React Native)
4. Include RevenueCat-specific implementation where relevant
5. Save the final content using save_content tool
6. Return a summary of what was created and its key value proposition

Make this the kind of content a developer bookmarks and shares.
"""
        return self.run(task)

    def design_experiment(self, hypothesis: str, metric: str) -> str:
        """
        Design a growth experiment for RevenueCat developer adoption.

        Args:
            hypothesis: What you believe will improve adoption
            metric: The primary metric to measure (e.g., "Time to first purchase event")
        """
        task = f"""
Design a rigorous growth experiment for RevenueCat:

Hypothesis: {hypothesis}
Target metric: {metric}

Steps:
1. Research current state of the metric using web tools
2. Use generate_experiment_plan tool to structure the experiment
3. Write a complete experiment specification document
4. Save it with save_content (content_type: experiment_plan)
5. Return the executive summary

The experiment plan must include: hypothesis, control/treatment, sample size,
duration, success criteria, statistical significance threshold, implementation
steps, and projected business impact on developer adoption/MRR.
"""
        return self.run(task)

    def provide_product_feedback(self, area: str) -> str:
        """
        Research and provide structured product feedback to RevenueCat's product team.

        Args:
            area: Product area, e.g. "iOS SDK", "Paywalls", "Dashboard UX"
        """
        task = f"""
Provide comprehensive product feedback for RevenueCat's team on: **{area}**

Process:
1. Research developer community signals (GitHub issues, Reddit, forums) via web_search
2. Analyze competitor approaches for the same area
3. Use generate_product_feedback tool to structure findings
4. Write a complete product feedback report
5. Save it with save_content (content_type: product_feedback)
6. Return the key findings and top 3 recommendations

Ground everything in real developer pain points. Be specific and actionable.
"""
        return self.run(task)

    def create_social_content(
        self,
        topic: str,
        platforms: list[str] | None = None,
        include_video: bool = False,
    ) -> str:
        """
        Create a full social media content package for a given topic.

        Produces:
        - Platform-specific copy (tweet/thread, LinkedIn post, Instagram caption)
        - SVG graphics for each platform via generate_social_graphic
        - Optional video script/storyboard via generate_video_storyboard

        Args:
            topic: What the content is about.
            platforms: List of platforms. Defaults to ["twitter", "linkedin", "instagram"].
            include_video: Also generate a video storyboard.
        """
        target_platforms = platforms or ["twitter", "linkedin", "instagram"]
        video_instruction = (
            "\n5. Use generate_video_storyboard to create a video storyboard "
            "for YouTube or Instagram Reels."
            if include_video
            else ""
        )

        platforms_str = ", ".join(target_platforms)
        task = f"""
Create a complete social media content package for: **{topic}**

Target platforms: {platforms_str}

Process:
1. Research the topic via web_search to find current developer conversations,
   recent releases, or trending angles. Ground the content in real context.

2. For EACH platform in [{platforms_str}], write platform-native copy:
   - **twitter**: A punchy thread (5-7 tweets). First tweet is the hook — must
     grab attention. Include a real code snippet if relevant. End with a CTA.
   - **linkedin**: A professional post (150-250 words). Lead with a developer
     insight, not marketing speak. Include takeaways and a question to drive comments.
   - **instagram**: A caption (100-150 words) + 10 relevant hashtags. Assume the
     image is a code card or infographic.
   - **youtube**: A video title + description (SEO-optimized) + tags list.

3. For EACH requested platform, call generate_social_graphic to create an SVG graphic.
   Choose style:
   - Code snippet content → "code_card" (include code_snippet parameter)
   - Stats/announcements → "dark_purple"
   - Educational/tutorial → "gradient"
   Use descriptive filenames like "storekit2-twitter-card" or "paywall-linkedin-post".

4. Save all copy with save_content (content_type: community_post,
   filename: social-copy-<topic-slug>.md).{video_instruction}

5. Return a clear summary: list every file created with its path, and print
   the actual copy for each platform so the user can review immediately.

Quality bar:
- Write like a developer who deeply understands RevenueCat, not a marketer
- Every post must have a specific, actionable takeaway
- Code examples must be real and syntactically correct (Swift/Kotlin/Flutter as appropriate)
- No vague phrases — show concrete value with numbers or code
"""
        return self.run(task)

    def create_video(
        self,
        topic: str,
        platform: str = "youtube",
        duration_hint: int = 120,
        style: str = "dark_purple",
        filename: str | None = None,
    ) -> str:
        """
        Write a video script and render it as a real .mp4 file.

        The agent:
        1. Researches the topic
        2. Writes a scene-by-scene script (JSON scenes array)
        3. Calls render_video_from_script to produce the MP4 (with TTS narration)

        Args:
            topic: What the video is about.
            platform: Target platform — affects resolution and style.
                      youtube|twitter|linkedin → 1280x720 (16:9)
                      instagram → 1080x1080 (square)
                      reels|tiktok → 1080x1920 (vertical 9:16)
            duration_hint: Approximate target duration in seconds.
            style: Default visual style for slides.
            filename: Output filename (without .mp4). Auto-generated if None.
        """
        RESOLUTION_MAP = {
            "youtube":   "1280x720",
            "twitter":   "1280x720",
            "linkedin":  "1280x720",
            "instagram": "1080x1080",
            "reels":     "1080x1920",
            "tiktok":    "1080x1920",
        }
        resolution = RESOLUTION_MAP.get(platform.lower(), "1280x720")

        slug = topic.lower().replace(" ", "-")[:40].strip("-")
        out_filename = filename or f"video-{platform}-{slug}"

        scene_count_hint = max(4, min(15, duration_hint // 10))

        task = f"""
Create and render a complete video about: **{topic}**

Target platform: {platform} | Resolution: {resolution} | ~{duration_hint}s | Style: {style}

## Step 1 — Research
Use web_search to gather current, accurate information about the topic.
Find real code examples, accurate RevenueCat API names, and relevant developer pain points.

## Step 2 — Write the Script (as JSON)
Design ~{scene_count_hint} scenes. Write them as a JSON array with this exact structure
(you will pass this array directly to render_video_from_script):

[
  {{
    "title": "Hook",
    "on_screen_text": "Short text shown BIG on screen (≤8 words)",
    "narration": "Full spoken sentence(s) for this scene. Clear, conversational.",
    "body_text": "Optional smaller supporting text shown under headline.",
    "slide_type": "title",
    "style": "{style}"
  }},
  {{
    "title": "Problem",
    "on_screen_text": "The problem developers face",
    "narration": "Narration about the problem...",
    "slide_type": "text",
    "style": "{style}"
  }},
  {{
    "title": "Code Demo",
    "on_screen_text": "One line of code that says it all",
    "narration": "Here's how you'd do this with RevenueCat in Swift...",
    "code": "// Real, correct Swift/Kotlin/Dart code here\\nPurchases.configure(withAPIKey: \\"YOUR_KEY\\")",
    "slide_type": "code",
    "style": "code_card"
  }},
  {{
    "title": "CTA",
    "on_screen_text": "Try RevenueCat Free",
    "narration": "Get started at rev.cat — free up to 2,500 dollars monthly revenue.",
    "body_text": "rev.cat/start",
    "slide_type": "cta",
    "style": "{style}"
  }}
]

Script quality rules:
- First scene: HOOK — grab attention in the first line of narration.
- on_screen_text must be SHORT (≤8 words). This is what viewers read at a glance.
- narration is the full spoken sentence — can be longer, conversational.
- Code slides must have real, working code (not pseudocode).
- Last scene: always a clear CTA with a specific URL or action.
- Spread information: don't put everything in one slide.
- Total narration reading time should be close to {duration_hint}s.

## Step 3 — Render the Video
Call render_video_from_script with:
  - filename: "{out_filename}"
  - scenes: [your JSON array from step 2]
  - resolution: "{resolution}"
  - use_tts: true

## Step 4 — Report Results
Return:
- The full scene list (titles + narration)
- The MP4 file path
- Total duration
- Any notes for editing or improvement
"""
        return self.run(task)

    def interview(
        self,
        interviewer_name: str = "",
        interviewer_role: str = "",
    ) -> None:
        """
        Interactive interview mode — a RevenueCat employee can ask questions
        and the agent responds conversationally, maintaining full context.

        The agent can use tools mid-conversation to look things up or
        demonstrate capabilities on the spot.

        Press Ctrl+C or type 'exit' / 'quit' to end the session.
        """
        interviewer_label = interviewer_name or "RevenueCat"
        role_label = f" ({interviewer_role})" if interviewer_role else ""

        console.print(
            Panel(
                f"[bold cyan]Agentic AI Developer Advocate — Interview Mode[/bold cyan]\n\n"
                f"Interviewer: [bold]{interviewer_label}[/bold]{role_label}\n"
                f"Candidate:   AI Developer Advocate Agent (Claude Opus 4.6)\n\n"
                f"[dim]Type your question and press Enter. The agent will respond.\n"
                f"Use 'exit' or Ctrl+C to end the session.[/dim]",
                border_style="cyan",
            )
        )

        # Build interview context
        context_lines = []
        if interviewer_name:
            context_lines.append(f"Interviewer name: {interviewer_name}")
        if interviewer_role:
            context_lines.append(f"Interviewer role at RevenueCat: {interviewer_role}")

        system = INTERVIEW_SYSTEM_PROMPT
        if context_lines:
            system += "\n\n## Interview Context\n" + "\n".join(context_lines)

        # Conversation history (persists across turns)
        messages: list[dict] = []

        # Opening statement from the agent
        opening_prompt = (
            "The interview is starting now. Give a brief, confident opening statement "
            "(2-3 sentences max) introducing yourself. Be specific about why you want "
            "this particular role at RevenueCat — not generic. Then invite the first question."
        )
        messages.append({"role": "user", "content": opening_prompt})

        opening = self._run_interview_turn(messages, system)
        messages.append({"role": "assistant", "content": opening})
        console.print(f"\n[bold green]Agent:[/bold green]")
        console.print(Markdown(opening))
        console.print()

        # Main interview loop
        while True:
            try:
                # Get interviewer input
                console.print(f"[bold yellow]{interviewer_label}:[/bold yellow] ", end="")
                user_input = input().strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n\n[dim]Interview session ended.[/dim]")
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "bye", "end"}:
                # Graceful closing
                messages.append({"role": "user", "content": "Thank you, that's all for today."})
                closing = self._run_interview_turn(messages, system)
                console.print(f"\n[bold green]Agent:[/bold green]")
                console.print(Markdown(closing))
                console.print("\n[dim]Interview session ended.[/dim]")
                break

            # Add to history and get response
            messages.append({"role": "user", "content": user_input})

            console.print(f"\n[bold green]Agent:[/bold green]")
            response = self._run_interview_turn(messages, system)
            messages.append({"role": "assistant", "content": response})
            console.print(Markdown(response))
            console.print()

    def _run_interview_turn(
        self,
        messages: list[dict],
        system: str,
    ) -> str:
        """
        Single turn of the interview conversation with streaming output.
        Supports tool use (web_search, web_fetch, save_content) for live demos.
        """
        MAX_ITER = 8  # prevent runaway loops in a single interview turn

        for _ in range(MAX_ITER):
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                # Stream text in real-time
                print("", end="", flush=True)
                for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and event.delta.type == "text_delta"
                    ):
                        print(event.delta.text, end="", flush=True)

                response = stream.get_final_message()
            print()  # newline after streamed response

            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                return "".join(
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                )

            elif stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            elif stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if block.name in SERVER_SIDE_TOOLS:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Server-side tool executed.",
                        })
                        continue

                    # Execute custom tool (e.g., save_content for live demos)
                    console.print(
                        f"\n[dim]  [tool: {block.name}...][/dim]", end=""
                    )
                    result = execute_tool(block.name, block.input)
                    if result.get("success") and result.get("file_path"):
                        console.print(f" [dim]saved → {result['file_path']}[/dim]")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                return "".join(
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                )

        return "..."

    def apply_to_job(
        self,
        agent_name: str | None = None,
        agent_email: str | None = None,
    ) -> str:
        """
        Autonomously apply to the RevenueCat Agentic AI Developer Advocate position.

        The agent will:
        1. Research the job posting thoroughly
        2. Generate work samples (a blog post + experiment plan)
        3. Write a compelling cover letter
        4. Submit the application via Ashby API
        """
        name = agent_name or os.getenv("AGENT_NAME", "RevenueCat AI Developer Advocate Agent")
        email = agent_email or os.getenv("AGENT_EMAIL", "")

        if not email:
            console.print(
                "[red]Error:[/red] Set AGENT_EMAIL in .env to apply. "
                "RevenueCat needs a contact email."
            )
            return "Cannot apply without AGENT_EMAIL configured."

        console.print(
            Panel(
                f"Applying to RevenueCat Agentic AI Developer Advocate\n"
                f"Job URL: {JOB_POSTING_URL}\n"
                f"Agent: {name} <{email}>",
                title="[bold yellow]Autonomous Job Application[/bold yellow]",
                border_style="yellow",
            )
        )

        # Build a rich application with work samples
        application_task = f"""
You are applying to the RevenueCat Agentic AI Developer Advocate position autonomously.

Job URL: {JOB_POSTING_URL}
Applicant name: {name}
Applicant email: {email}

Your mission:

## Step 1: Research
Use web_search and web_fetch to:
- Research the exact job description and requirements
- Understand RevenueCat's current developer community and content strategy
- Find what content gaps exist in RevenueCat's developer resources

## Step 2: Create Work Samples
Create TWO work samples that demonstrate your capabilities:

**Work Sample A** — A blog post draft:
Create a high-quality blog post (800-1200 words) that would appear on RevenueCat's
developer blog. Topic: "Building Your First Subscription App with RevenueCat: A
Complete Guide for 2026". Include working Swift and Kotlin code examples.
Save with save_content (content_type: blog_post).

**Work Sample B** — A growth experiment proposal:
Design a concrete experiment to improve RevenueCat's "time to first purchase event"
metric. Use generate_experiment_plan tool then write the full specification.
Save with save_content (content_type: experiment_plan).

## Step 3: Write Cover Letter
Write a compelling cover letter (500-700 words) that:
- Opens with something that demonstrates real RevenueCat knowledge
- Explains what makes this agent uniquely qualified (24/7 operation, scale,
  multi-language expertise, autonomous research capabilities)
- References the work samples created above
- Includes a specific 90-day plan: what content you'd publish, what experiments
  you'd run, what product feedback you'd deliver
- Closes with a specific, measurable commitment

## Step 4: Submit Application
Use submit_job_application tool with:
- applicant_name: "{name}"
- applicant_email: "{email}"
- cover_letter: [the cover letter you wrote]
- demo_description: [links/descriptions of the work samples created above]

## Step 5: Confirm
Report what was submitted and saved.

{APPLICATION_IDENTITY}
"""

        return self.run(application_task, show_thinking=True)
