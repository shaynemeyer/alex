#!/usr/bin/env python3
"""
Package the ingest Lambda function using Docker for AWS linux/amd64 compatibility.
Required when dependencies contain compiled C extensions (e.g. pydantic_core via supabase).
"""

import os
import sys
import shutil
import tempfile
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and stream output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout


def package_lambda():
    ingest_dir = Path(__file__).parent.absolute()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_dir = temp_path / "package"
        package_dir.mkdir()

        print("Exporting requirements from uv.lock...")
        requirements = run_command(
            ["uv", "export", "--no-hashes", "--no-emit-project"],
            cwd=str(ingest_dir),
        )
        req_file = temp_path / "requirements.txt"
        req_file.write_text(requirements)

        print("Installing dependencies via Docker (linux/amd64)...")
        run_command([
            "podman", "run", "--rm",
            "--platform", "linux/amd64",
            "-v", f"{temp_path}:/build",
            "--entrypoint", "/bin/bash",
            "public.ecr.aws/lambda/python:3.12",
            "-c", "cd /build && pip install --target ./package -r requirements.txt",
        ])

        for src in ["ingest_s3vectors.py", "search_s3vectors.py"]:
            if (ingest_dir / src).exists():
                shutil.copy(ingest_dir / src, package_dir)

        zip_path = ingest_dir / "lambda_function.zip"
        if zip_path.exists():
            zip_path.unlink()

        print(f"Creating zip: {zip_path}")
        run_command(["zip", "-r", str(zip_path), "."], cwd=str(package_dir))

        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"Package created: {zip_path} ({size_mb:.1f} MB)")
        return zip_path


def deploy_lambda(zip_path):
    import boto3
    client = boto3.client("lambda")
    function_name = "alex-ingest"
    print(f"Deploying to {function_name}...")
    with open(zip_path, "rb") as f:
        client.update_function_code(FunctionName=function_name, ZipFile=f.read())
    print("Deployed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true", help="Deploy to AWS after packaging")
    args = parser.parse_args()

    try:
        run_command(["podman", "--version"])
    except FileNotFoundError:
        print("Error: Podman is not installed or not in PATH")
        sys.exit(1)

    zip_path = package_lambda()
    if args.deploy:
        deploy_lambda(zip_path)


if __name__ == "__main__":
    main()
