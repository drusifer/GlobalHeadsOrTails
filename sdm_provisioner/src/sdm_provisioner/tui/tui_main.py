import sys
from sdm_provisioner.tui.app import NtagProvisionerApp


def main():
    try:
        app = NtagProvisionerApp()
    except ConnectionError as e:
        print("\n" + "=" * 70, file=sys.stderr)
        print(" [FATAL ERROR] tag_validator_service is unreachable", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f" {e}", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)
    app.run()


if __name__ == "__main__":
    main()
