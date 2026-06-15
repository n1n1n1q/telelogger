import getpass
import io
import socket
import subprocess
import sys
import threading
import time
import telebot


def get_host() -> str:
    user = getpass.getuser()
    host = socket.gethostname()
    return f"*Host: {user}@{host}*"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {rem_seconds:.2f}s"
    hours = int(minutes // 60)
    rem_minutes = minutes % 60
    return f"{hours}h {rem_minutes}m {rem_seconds:.2f}s"


def send_log_file(bot: telebot.TeleBot, chat_id: int, reply_to_message_id: int, file_name: str, content: str) -> None:
    if not content:
        content = "(empty)"
    bio = io.BytesIO(content.encode("utf-8"))
    bio.name = file_name
    try:
        bot.send_document(
            chat_id=chat_id,
            document=bio,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        print(f"Failed to send log file {file_name}: {e}", file=sys.stderr)


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
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    combined_lines: list[str] = []
    lock = threading.Lock()

    def read_stream(stream, buffer, console_stream):
        for line in iter(stream.readline, ""):
            # Write to the local console
            console_stream.write(line)
            console_stream.flush()
            with lock:
                buffer.append(line)
                combined_lines.append(line)

    t_stdout = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines, sys.stdout))
    t_stderr = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines, sys.stderr))

    t_stdout.start()
    t_stderr.start()

    start_time = time.time()
    last_update_time = time.time()

    # Periodically update the Telegram streaming message during execution
    while process.poll() is None or t_stdout.is_alive() or t_stderr.is_alive():
        time.sleep(0.1)
        if time.time() - last_update_time > 2.0:
            with lock:
                display_text = "".join(combined_lines[-15:])
            if display_text.strip():
                # Avoid breaking triple-backtick markdown block
                display_text_clean = display_text.replace("```", "'''")
                try:
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=reply_msg.message_id,
                        text=f"{header}\n\n⏳ **Running...**\n\n```\n{display_text_clean}\n```",
                        parse_mode="Markdown",
                    )
                except telebot.apihelper.ApiTelegramException:
                    try:
                        # Fallback: send without markdown if markdown compilation fails
                        bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=reply_msg.message_id,
                            text=f"{header}\n\nRunning...\n\n{display_text_clean}",
                        )
                    except Exception:
                        pass
            last_update_time = time.time()

    t_stdout.join()
    t_stderr.join()
    return_code = process.wait()
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Edit the initial streaming message to indicate completion
    with lock:
        final_display = "".join(combined_lines[-20:]) or "No console output."
    final_display_clean = final_display.replace("```", "'''")
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=reply_msg.message_id,
            text=f"{header}\n\n🏁 **Execution finished.**\n\n```\n{final_display_clean}\n```",
            parse_mode="Markdown",
        )
    except Exception:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=reply_msg.message_id,
                text=f"{header}\n\nExecution finished.\n\n{final_display_clean}",
            )
        except Exception:
            pass

    # Crash detection logic
    stdout_str = "".join(stdout_lines)
    stderr_str = "".join(stderr_lines)

    crash_keywords = [
        "traceback (most recent call)",
        "segmentation fault",
        "core dumped",
        "fatal error",
        "access violation",
        "exception in thread",
        "unhandled exception",
    ]

    has_crash_keyword = False
    for kw in crash_keywords:
        if kw in stdout_str.lower() or kw in stderr_str.lower():
            has_crash_keyword = True
            break

    is_success = (return_code == 0) and not has_crash_keyword
    status_icon = "✅" if is_success else "❌"
    duration_str = format_duration(elapsed_time)

    if is_success:
        status_msg = (
            f"{header}\n"
            f"{status_icon} **Command Completed Successfully!**\n\n"
            f"• **Command:** `{command}`\n"
            f"• **Duration:** {duration_str}\n"
            f"• **Exit Code:** `0`"
        )
    else:
        exit_code_desc = f"`{return_code}`"
        if return_code == 0 and has_crash_keyword:
            exit_code_desc += " (with crash signature)"

        status_msg = (
            f"{header}\n"
            f"{status_icon} **Command Execution Failed/Crashed!**\n\n"
            f"• **Command:** `{command}`\n"
            f"• **Duration:** {duration_str}\n"
            f"• **Exit Code:** {exit_code_desc}\n"
        )

        last_stdout = "".join(stdout_lines[-10:]).strip().replace("```", "'''")
        last_stderr = "".join(stderr_lines[-10:]).strip().replace("```", "'''")

        if last_stdout:
            status_msg += f"\n📄 **Stdout snippet:**\n```\n{last_stdout}\n```"
        if last_stderr:
            status_msg += f"\n⚠️ **Stderr snippet:**\n```\n{last_stderr}\n```"

    # Send the separate status message
    reply_id = start_msg.message_id
    try:
        status_message = bot.send_message(
            chat_id=chat_id,
            text=status_msg,
            parse_mode="Markdown",
        )
        reply_id = status_message.message_id
    except telebot.apihelper.ApiTelegramException:
        # Fallback to plain text on Markdown syntax failure
        try:
            status_msg_plain = (
                status_msg.replace("**", "")
                .replace("`", "")
                .replace("❌", "[Failed]")
                .replace("✅", "[Success]")
            )
            status_message = bot.send_message(
                chat_id=chat_id,
                text=status_msg_plain,
            )
            reply_id = status_message.message_id
        except Exception as e:
            print(f"Failed to send plain status message: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to send status message: {e}", file=sys.stderr)

    # Save and send stdout and stderr logs as files
    send_log_file(bot, chat_id, reply_id, "stdout.log", stdout_str)
    if stderr_str:
        send_log_file(bot, chat_id, reply_id, "stderr.log", stderr_str)

    return return_code