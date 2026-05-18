#!/usr/bin/env python3
"""
Deploy researcher service to AWS Lambda (container image).
Cross-platform deployment script for Mac/Windows/Linux.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)


def run_command(cmd, capture_output=False):
    """Run a command and handle errors."""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
        if capture_output:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        sys.exit(1)


def main():
    print("Alex Researcher Service - Lambda Container Deployment")
    print("=====================================================")

    account_id = run_command(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True,
    )

    region = os.environ.get("DEFAULT_AWS_REGION")
    if not region:
        print("Error: DEFAULT_AWS_REGION not found in your .env file.")
        sys.exit(1)

    print(f"AWS Account: {account_id}")
    print(f"Region: {region}")

    # Get ECR repository URL from Terraform output
    print("\nGetting ECR repository URL...")
    terraform_dir = Path(__file__).parent.parent.parent / "terraform" / "4_researcher"
    original_dir = os.getcwd()

    try:
        os.chdir(terraform_dir)
        ecr_url = run_command(
            ["terraform", "output", "-raw", "ecr_repository_url"], capture_output=True
        )
    finally:
        os.chdir(original_dir)

    if not ecr_url:
        print("Error: ECR repository not found. Run 'terraform apply' first.")
        sys.exit(1)

    print(f"ECR Repository: {ecr_url}")

    # Login to ECR
    print("\nLogging in to ECR...")
    password = run_command(
        ["aws", "ecr", "get-login-password", "--region", region], capture_output=True
    )

    login_process = subprocess.Popen(
        ["podman", "login", "--username", "AWS", "--password-stdin", ecr_url],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = login_process.communicate(input=password)
    if login_process.returncode != 0:
        print(f"Error logging into ECR: {stderr}")
        sys.exit(1)
    print("Login successful!")

    image_tag = f"deploy-{int(time.time())}"
    ecr_repository = "alex-researcher"

    # Build Docker image
    print(f"\nBuilding Docker image for linux/amd64 with tag: {image_tag}")
    run_command(
        ["podman", "build", "--platform", "linux/amd64", "-t", f"{ecr_repository}:{image_tag}", "."]
    )

    # Tag and push to ECR
    print("\nTagging image for ECR...")
    run_command(["podman", "tag", f"{ecr_repository}:{image_tag}", f"{ecr_url}:{image_tag}"])
    run_command(["podman", "tag", f"{ecr_repository}:{image_tag}", f"{ecr_url}:latest"])

    print("\nPushing image to ECR...")
    run_command(["podman", "push", f"{ecr_url}:{image_tag}"])
    run_command(["podman", "push", f"{ecr_url}:latest"])

    print("\nDocker image pushed successfully!")

    # Update Lambda function to use the new image
    print("\nUpdating Lambda function code...")
    run_command(
        [
            "aws", "lambda", "update-function-code",
            "--function-name", "alex-researcher",
            "--image-uri", f"{ecr_url}:{image_tag}",
            "--region", region,
        ]
    )

    # Wait for the update to complete
    print("Waiting for Lambda update to complete...")
    max_attempts = 30
    for attempt in range(max_attempts):
        status = run_command(
            [
                "aws", "lambda", "get-function",
                "--function-name", "alex-researcher",
                "--region", region,
                "--query", "Configuration.LastUpdateStatus",
                "--output", "text",
            ],
            capture_output=True,
        )

        if status == "Successful":
            print("Lambda update complete!")
            break
        elif status == "Failed":
            print("Lambda update failed. Check CloudWatch logs.")
            sys.exit(1)
        else:
            print(".", end="", flush=True)
            time.sleep(5)
    else:
        print("\nUpdate is taking longer than expected. Check the AWS Console.")
        sys.exit(1)

    # Get and display the function URL
    try:
        os.chdir(terraform_dir)
        function_url = run_command(
            ["terraform", "output", "-raw", "researcher_url"], capture_output=True
        )
    finally:
        os.chdir(original_dir)

    print(f"\nYour researcher is available at:")
    print(f"  {function_url}")
    print(f"\nTest it with:")
    print(f"  curl {function_url}health")
    print(f"\nNext step: Run 'terraform apply' in terraform/4_researcher if you haven't yet.")


if __name__ == "__main__":
    main()
