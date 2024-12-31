import discord

# Reads the update information from a text file and formats it as an ini code block
def read_avalore_update_file(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            formatted_lines = ["**New commit to Avalore's GitHub repository detected!**", "```ini"]
            for line in lines:
                formatted_lines.append(line.strip())
            formatted_lines.append("```")
            return "\n".join(formatted_lines)
    except Exception as e:
        print(e)
        return "Failed to read update file."

# Sends an update message to a specified channel
async def send_avalore_update_message(channel: discord.TextChannel, update_message: str) -> None:
    try:
        await channel.send(update_message) # Send the update message to the specified channel
    except Exception as e:
        print(e)