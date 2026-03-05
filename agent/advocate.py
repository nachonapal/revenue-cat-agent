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

from agent.prompts import DEVELOPER_ADVOCATE_SYSTEM_PROMPT, APPLICATION_IDENTITY
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
