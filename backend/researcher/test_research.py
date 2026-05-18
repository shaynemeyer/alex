#!/usr/bin/env python3
"""
Test the researcher Lambda service by generating investment research.
Cross-platform script for Mac/Windows/Linux.
"""

import subprocess
import sys
import json
import requests
import argparse
from pathlib import Path
import os


def get_service_url():
    """Get the Lambda Function URL from Terraform output."""
    terraform_dir = Path(__file__).parent.parent.parent / "terraform" / "4_researcher"
    original_dir = os.getcwd()
    try:
        os.chdir(terraform_dir)
        result = subprocess.run(
            ["terraform", "output", "-raw", "researcher_url"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        if not url:
            print("Error: researcher_url output is empty.")
            print("Run 'terraform apply' in terraform/4_researcher first.")
            sys.exit(1)
        return url
    except subprocess.CalledProcessError as e:
        print(f"Error getting function URL from Terraform: {e}")
        print("Make sure you have run 'terraform apply' in terraform/4_researcher.")
        sys.exit(1)
    finally:
        os.chdir(original_dir)


def test_research(topic=None):
    """Test the researcher service with a topic."""
    display_topic = topic if topic else "Agent's choice (trending topic)"

    print("Getting Lambda Function URL...")
    service_url = get_service_url()
    # Ensure no trailing slash
    service_url = service_url.rstrip("/")
    print(f"Found service at: {service_url}")

    # Health check
    print("\nChecking service health...")
    try:
        response = requests.get(f"{service_url}/health", timeout=30)
        response.raise_for_status()
        print("Service is healthy")
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")
        print("The Lambda may still be initializing (cold start). Try again in a moment.")
        sys.exit(1)

    # Research request
    print(f"\nGenerating research for: {display_topic}")
    print("This will take 20-30 seconds as the agent browses and analyzes...")

    try:
        payload = {"topic": topic} if topic else {}
        response = requests.post(
            f"{service_url}/research",
            json=payload,
            timeout=300,  # 5 minutes — Lambda max is 15 min but research completes in ~30s
        )
        response.raise_for_status()

        result = response.json()

        print("\nResearch generated successfully!")
        print("\n" + "=" * 60)
        print("RESEARCH RESULT:")
        print("=" * 60)
        print(result)
        print("=" * 60)

        print("\nThe research has been automatically stored in your knowledge base.")
        print("To verify, run:")
        print("  cd ../ingest")
        print("  uv run test_search_s3vectors.py")

    except requests.exceptions.Timeout:
        print("Request timed out. Try again — the Lambda may have been cold-starting.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error calling research endpoint: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Error details: {e.response.json()}")
            except (json.JSONDecodeError, AttributeError):
                print(f"Response: {e.response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Test the Alex Researcher Lambda service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run test_research.py
  uv run test_research.py "Tesla competitive advantages"
  uv run test_research.py "Microsoft cloud revenue growth"
        """,
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="Investment topic to research (optional)",
    )
    args = parser.parse_args()
    test_research(args.topic)


if __name__ == "__main__":
    main()
