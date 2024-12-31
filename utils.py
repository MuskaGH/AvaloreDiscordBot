import discord
import constants
from datetime import datetime

# Reads the update information from a text file and formats it as an ini code block
def read_avalore_update_file(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            now = datetime.now()
            formatted_lines = [
                "**New commit to Avalore's GitHub repository detected!**",
                "```ini",
                f"Date: {now.strftime('%d/%m/%Y (CET)')}",
                f"Time: {now.strftime('%I:%M %p (CET)')}",
                ""
            ]
            for line in lines:
                formatted_lines.append(line.strip())
            formatted_lines.append("```")
            return "\n".join(formatted_lines)
    except Exception as e:
        print(e)
        return "Failed to read update file."

# Sends an update message to a specified channel
async def send_avalore_update_message(channel: discord.TextChannel, update_message: str) -> None:
    await channel.send(update_message) # Send the update message to the specified channel