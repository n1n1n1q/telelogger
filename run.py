import sys
import subprocess
import time
import telebot

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHAT_ID = 123456789 

bot = telebot.TeleBot(BOT_TOKEN)

def main():
    if len(sys.argv) < 2:
        print("Usage: python tele_logger.py <your system command>")
        sys.exit(1)
    
    target_command = " ".join(sys.argv[1:])
  
    try:
        start_msg = bot.send_message(
            CHAT_ID, 
            f"🚀 **Starting execution:**\n`{target_command}`", 
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to connect to Telegram: {e}")
        sys.exit(1)

    reply_msg = bot.send_message(
        CHAT_ID, 
        "⏳ *Initializing output stream...*", 
        reply_to_message_id=start_msg.message_id,
        parse_mode="Markdown"
    )

    process = subprocess.Popen(
        target_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    output_buffer = []
    last_update_time = time.time()

    for line in iter(process.stdout.readline, ''):
        output_buffer.append(line.strip())
        
        # Update Telegram every 2 seconds to avoid rate limits
        if time.time() - last_update_time > 2.0:
            display_text = "\n".join(output_buffer[-15:])
            try:
                bot.edit_message_text(
                    chat_id=CHAT_ID,
                    message_id=reply_msg.message_id,
                    text=f"⏳ **Running...**\n\n```\n{display_text}\n```",
                    parse_mode="Markdown"
                )
            except telebot.apihelper.ApiTelegramException:
                pass
            last_update_time = time.time()

    process.stdout.close()
    return_code = process.wait()

    final_text = "\n".join(output_buffer[-20:])
    if not final_text.strip():
        final_text = "No console output."

    status_icon = "✅" if return_code == 0 else "❌"
    final_status = "completed successfully" if return_code == 0 else f"failed with exit code {return_code}"

    try:
        bot.edit_message_text(
            chat_id=CHAT_ID,
            message_id=reply_msg.message_id,
            text=f"{status_icon} **Command {final_status}**\n\n```\n{final_text}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to send final update: {e}")

if __name__ == "__main__":
    main()