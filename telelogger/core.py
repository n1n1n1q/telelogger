import getpass
import socket
import subprocess
import time
import telebot


def get_host() -> str:
    user = getpass.getuser()
    host = socket.gethostname()
    return f"*Host: {user}@{host}*"


def run(bot_token: str, chat_id: int, command: str) -> int:
    """
    Run *command* in a subprocess and stream its output to a Telegram chat.

    Returns the process exit code.
    """
    bot = telebot.TeleBot(bot_token)
    header = get_host()

    try:
        start_msg = bot.send_message(
            chat_id,
            f"{header}\n\n🚀 **Starting execution:**\n`{command}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Telegram: {e}") from e

    reply_msg = bot.send_message(
        chat_id,
        f"{header}\n\n⏳ *Initializing output stream...*",
        reply_to_message_id=start_msg.message_id,
        parse_mode="Markdown",
    )

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_buffer: list[str] = []
    last_update_time = time.time()

    for line in iter(process.stdout.readline, ""):
        output_buffer.append(line.strip())

        if time.time() - last_update_time > 2.0:
            display_text = "\n".join(output_buffer[-15:])
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=reply_msg.message_id,
                    text=f"{header}\n\n⏳ **Running...**\n\n```\n{display_text}\n```",
                    parse_mode="Markdown",
                )
            except telebot.apihelper.ApiTelegramException:
                pass
            last_update_time = time.time()

    process.stdout.close()
    return_code = process.wait()

    final_text = "\n".join(output_buffer[-20:]) or "No console output."
    status_icon = "✅" if return_code == 0 else "❌"
    final_status = (
        "completed successfully"
        if return_code == 0
        else f"failed with exit code {return_code}"
    )

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=reply_msg.message_id,
            text=f"{header}\n{status_icon} **Command {final_status}**\n\n```\n{final_text}\n```",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Failed to send final update: {e}")

    return return_code