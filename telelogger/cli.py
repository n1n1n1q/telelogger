import argparse
import os
import sys

from .core import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telegram-cli-logger",
        description="Run a shell command and stream its output to a Telegram chat.",
    )
    parser.add_argument(
        "--token",
        metavar="BOT_TOKEN",
        default=os.environ.get("TELEGRAM_BOT_TOKEN"),
        help=(
            "Telegram bot token. "
            "Falls back to the TELEGRAM_BOT_TOKEN environment variable."
        ),
    )
    parser.add_argument(
        "--chat-id",
        metavar="CHAT_ID",
        type=int,
        default=int(os.environ["TELEGRAM_CHAT_ID"])
        if os.environ.get("TELEGRAM_CHAT_ID")
        else None,
        help=(
            "Telegram chat ID to send output to. "
            "Falls back to the TELEGRAM_CHAT_ID environment variable."
        ),
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Shell command to execute (everything after the flags).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    errors: list[str] = []

    if not args.token:
        errors.append(
            "Bot token is required. Pass --token or set TELEGRAM_BOT_TOKEN."
        )
    if args.chat_id is None:
        errors.append(
            "Chat ID is required. Pass --chat-id or set TELEGRAM_CHAT_ID."
        )
    if not args.command:
        errors.append("No command supplied. Provide a command to run.")

    if errors:
        for msg in errors:
            print(f"error: {msg}", file=sys.stderr)
        parser.print_usage(sys.stderr)
        sys.exit(2)

    command_parts = args.command
    if command_parts and command_parts[0] == "--":
        command_parts = command_parts[1:]

    command_str = " ".join(command_parts)

    try:
        exit_code = run(
            bot_token=args.token,
            chat_id=args.chat_id,
            command=command_str,
        )
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()