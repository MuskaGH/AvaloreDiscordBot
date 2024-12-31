import discord

# Provides a response to the user based on the message content
async def send_message(message: discord.Message, user_message: str) -> None:
    # Check if the message is empty (no content, embeds, or attachments)
    if not message.content and not message.embeds and not message.attachments:
        print("Message was empty (no content, embeds, or attachments).")
        return
    
    try:
        await message.channel.send("Hey! I'm Avalore bot developed by Muska") # Send the response to the same channel where the message was received
    except Exception as e:
        print(e)