# telelogger

Stream any shell command's output to a Telegram chat in real time.

## Install

```bash
pip install .          # from the repo root
# or, once published:
pip install telelogger
```

## Usage

```
telelogger --token <BOT_TOKEN> --chat-id <CHAT_ID> -- <command>
```

### Examples

```bash
# Basic
telelogger --token 123:ABC --chat-id 987654321 -- python train.py

# Long-running build
telelogger --token 123:ABC --chat-id 987654321 -- make -j4

# Using environment variables (recommended)
export TELEGRAM_BOT_TOKEN=123:ABC
export TELEGRAM_CHAT_ID=987654321
telelogger -- ./run_experiment.sh
```

## Environment variables

| Variable              | Description                        |
|-----------------------|------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | Bot token (replaces `--token`)     |
| `TELEGRAM_CHAT_ID`    | Chat ID (replaces `--chat-id`)     |

## CLI reference

```
usage: telelogger [--token BOT_TOKEN] [--chat-id CHAT_ID] -- command [args ...]

options:
  --token BOT_TOKEN   Telegram bot token
  --chat-id CHAT_ID   Telegram chat ID
  -h, --help          Show this help message and exit
```