"""CLI entry point for ntag424-sdm-provisioner.

This module provides the command-line interface for the provisioning tool.
For the full TUI experience, use: provision-tui
"""

import sys


def cli():
    """Main CLI entry point."""
    print("NTAG424 SDM Provisioner")
    print("=" * 40)
    print()
    print("Available commands:")
    print("  provision-tui    - Launch interactive TUI")
    print()
    print("For TUI mode, run: provision-tui")
    print()

    # If args provided, show help
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            print("Usage: provision-tag")
            print("       provision-tui  (recommended)")
            return 0
        else:
            print(f"Unknown argument: {arg}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(cli())
