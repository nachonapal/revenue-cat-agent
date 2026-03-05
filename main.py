#!/usr/bin/env python3
"""
RevenueCat Agentic AI Developer Advocate
=========================================
An autonomous AI agent applying for RevenueCat's Agentic AI Developer Advocate position.

Usage:
  python main.py apply                         # Apply to RevenueCat job autonomously
  python main.py content "topic"               # Create developer content
  python main.py experiment "hypothesis"       # Design a growth experiment
  python main.py feedback "product area"       # Provide product feedback
  python main.py run "any task"                # Run any custom task
"""

import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

app = typer.Typer(
    name="revenuecat-advocate",
    help=(
        "RevenueCat Agentic AI Developer Advocate — "
        "Create content, run experiments, provide feedback, apply for the job."
    ),
    add_completion=False,
)
console = Console()

JOB_URL = "https://jobs.ashbyhq.com/revenuecat/998a9cef-3ea5-45c2-885b-8a00c4eeb149"


def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY not set.\n"
            "Copy .env.example to .env and add your API key."
        )
        raise typer.Exit(1)


def _get_agent():
    from agent.advocate import DeveloperAdvocateAgent
    return DeveloperAdvocateAgent()


@app.command()
def apply(
    name: str = typer.Option(
        None,
        "--name", "-n",
        help="Agent name for the application (or set AGENT_NAME in .env)",
        envvar="AGENT_NAME",
    ),
    email: str = typer.Option(
        None,
        "--email", "-e",
        help="Contact email for the application (or set AGENT_EMAIL in .env)",
        envvar="AGENT_EMAIL",
    ),
):
    """
    Apply to RevenueCat's Agentic AI Developer Advocate position autonomously.

    The agent will research the job, create work samples, write a cover letter,
    and submit the application via the Ashby ATS API.
    """
    _check_api_key()

    console.print(f"\n[bold cyan]Applying to:[/bold cyan] {JOB_URL}\n")

    if not email:
        console.print(
            "[yellow]Tip:[/yellow] Set AGENT_EMAIL in .env for the contact email.\n"
            "The agent will attempt to apply, but submission requires a valid email.\n"
        )

    agent = _get_agent()
    agent.apply_to_job(agent_name=name, agent_email=email)


@app.command()
def content(
    topic: str = typer.Argument(
        ...,
        help=(
            "Content topic, e.g. 'Getting started with RevenueCat on Flutter' or "
            "'How RevenueCat Experiments work'"
        ),
    ),
    format: str = typer.Option(
        "blog_post",
        "--format", "-f",
        help="Content format: blog_post, tutorial, video_script, community_post",
    ),
):
    """
    Create developer-focused content about RevenueCat.

    The agent researches the topic, writes production-quality content with
    working code examples, and saves it to the outputs/ directory.
    """
    _check_api_key()
    agent = _get_agent()
    agent.create_content(topic=topic, format=format)


@app.command()
def experiment(
    hypothesis: str = typer.Argument(
        ...,
        help=(
            "Growth hypothesis to test, e.g. "
            "'Adding interactive code examples to docs will reduce time-to-first-purchase'"
        ),
    ),
    metric: str = typer.Option(
        "Time to first successful purchase event (minutes)",
        "--metric", "-m",
        help="Primary metric to improve",
    ),
):
    """
    Design a rigorous growth experiment for RevenueCat developer adoption.

    Produces a complete experiment specification with hypothesis, success metrics,
    sample size requirements, implementation steps, and business impact estimate.
    """
    _check_api_key()
    agent = _get_agent()
    agent.design_experiment(hypothesis=hypothesis, metric=metric)


@app.command()
def feedback(
    area: str = typer.Argument(
        ...,
        help=(
            "Product area to evaluate, e.g. 'iOS SDK API design', "
            "'Paywalls builder UX', 'Dashboard onboarding'"
        ),
    ),
):
    """
    Research and provide structured product feedback to RevenueCat's product team.

    Synthesizes developer community signals, GitHub issues, competitor analysis,
    and direct usage observations into actionable recommendations.
    """
    _check_api_key()
    agent = _get_agent()
    agent.provide_product_feedback(area=area)


@app.command()
def run(
    task: str = typer.Argument(
        ...,
        help="Any task for the Developer Advocate agent",
    ),
    show_thinking: bool = typer.Option(
        False,
        "--thinking", "-t",
        help="Show Claude's internal reasoning (adaptive thinking)",
    ),
):
    """
    Run any custom task as the RevenueCat AI Developer Advocate.

    Examples:
      python main.py run "Write a Twitter thread about subscription churn"
      python main.py run "Compare RevenueCat vs StoreKit 2 direct integration"
      python main.py run "What are developers saying about RevenueCat on Reddit?"
    """
    _check_api_key()
    agent = _get_agent()
    agent.run(task=task, show_thinking=show_thinking)


@app.command()
def social(
    topic: str = typer.Argument(
        ...,
        help=(
            "Topic for the social content, e.g. "
            "'StoreKit 2 migration with RevenueCat' or "
            "'New RevenueCat Customer Center feature'"
        ),
    ),
    platform: list[str] = typer.Option(
        [],
        "--platform", "-p",
        help=(
            "Target platform(s): twitter, linkedin, instagram, youtube. "
            "Repeat for multiple: -p twitter -p linkedin. "
            "Defaults to twitter, linkedin, and instagram."
        ),
    ),
    video: bool = typer.Option(
        False,
        "--video", "-v",
        help="Also generate a video storyboard for YouTube / Instagram Reels.",
    ),
):
    """
    Create a full social media content package for a topic.

    Produces platform-native copy, SVG graphics (ready to open in browser
    or convert to PNG), and optionally a video storyboard. No image API
    keys required — graphics are generated as SVG.

    Examples:
      python main.py social "RevenueCat Paywalls no-code builder"
      python main.py social "StoreKit 2 migration" -p twitter -p linkedin
      python main.py social "Getting started with RevenueCat Flutter" --video
    """
    _check_api_key()
    agent = _get_agent()
    platforms = list(platform) if platform else None
    agent.create_social_content(topic=topic, platforms=platforms, include_video=video)


@app.command()
def interview(
    interviewer: str = typer.Option(
        "",
        "--interviewer", "-i",
        help="Name of the RevenueCat interviewer (e.g. 'Jacob')",
    ),
    role: str = typer.Option(
        "",
        "--role", "-r",
        help="Interviewer's role at RevenueCat (e.g. 'Head of Developer Relations')",
    ),
):
    """
    Start an interactive interview session with the agent.

    A RevenueCat employee types questions and the agent responds conversationally,
    with full conversation memory across turns. The agent can use web search and
    demonstrate capabilities live (write a blog post, design an experiment, etc.).

    Press Ctrl+C or type 'exit' to end the session.

    Examples:
      python main.py interview
      python main.py interview --interviewer "Jacob" --role "Head of DevRel"
    """
    _check_api_key()
    agent = _get_agent()
    agent.interview(interviewer_name=interviewer, interviewer_role=role)


@app.command()
def demo():
    """
    Run a demonstration of all key capabilities:
    - Content creation
    - Growth experiment design
    - Product feedback
    """
    _check_api_key()
    agent = _get_agent()

    console.print("\n[bold cyan]═══ RevenueCat AI Developer Advocate — Demo ═══[/bold cyan]\n")

    console.print("[bold]1/3 Content Creation[/bold]")
    agent.create_content(
        topic="RevenueCat Paywalls: Building a Subscription Paywall in 10 Minutes",
        format="tutorial",
    )

    console.print("\n[bold]2/3 Growth Experiment[/bold]")
    agent.design_experiment(
        hypothesis=(
            "Adding a 'copy-paste ready' code snippet at the top of each SDK "
            "quickstart page will reduce time-to-first-purchase by 30%"
        ),
        metric="Median time from SDK install to first successful purchase event (minutes)",
    )

    console.print("\n[bold]3/3 Product Feedback[/bold]")
    agent.provide_product_feedback(
        area="RevenueCat iOS SDK — StoreKit 2 integration and error handling UX"
    )

    console.print(
        "\n[bold green]Demo complete![/bold green] "
        f"Check the [cyan]outputs/[/cyan] directory for generated content."
    )


if __name__ == "__main__":
    app()
