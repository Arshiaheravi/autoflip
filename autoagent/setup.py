#!/usr/bin/env python3
"""
AutoAgent — One-time setup script.
Run this once to install all required dependencies.

Usage:
    py autoagent/setup.py
"""
import subprocess
import sys


def run(cmd: str, description: str):
    print(f"\n>>> {description}")
    print(f"    $ {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0:
        print(f"    WARNING: command exited with code {result.returncode}")
    else:
        print(f"    OK")
    return result.returncode == 0


def main():
    print("=" * 55)
    print("AutoAgent Setup")
    print("=" * 55)

    # Core Python dependencies
    packages = [
        "anthropic",
        "httpx",
        "beautifulsoup4",
        "python-dotenv",
        "playwright",
    ]

    print("\nInstalling Python packages...")
    all_ok = True
    for pkg in packages:
        ok = run(f"pip install {pkg}", f"Install {pkg}")
        if not ok:
            all_ok = False

    # Install Playwright browsers
    run("python -m playwright install chromium", "Install Playwright Chromium browser")

    print("\n" + "=" * 55)
    if all_ok:
        print("Setup complete!")
    else:
        print("Setup completed with some warnings. Check output above.")
    print("=" * 55)
    print("\nNext steps:")
    print("  1. Edit autoagent/PROJECT.md — describe your project")
    print("  2. Edit autoagent/config.json — set model, budget, URLs")
    print("  3. Add your ANTHROPIC_API_KEY to .env (if using API mode)")
    print("  4. Run: py autoagent/run.py")
    print()


if __name__ == "__main__":
    main()
