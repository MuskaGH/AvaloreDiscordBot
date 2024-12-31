import os
import discord

from dotenv import load_dotenv

# 01: Load environment variables
load_dotenv() # Load environment variables from .env file found in the same directory as this file
TOKEN: str = os.getenv('DISCORD_TOKEN') # Get the bot token from the environment variables

# 02: Create a new bot client
Intents = discord.Intents.default() # Intents object with the default intents (messages, reactions, etc.) used by the bot
Intents.message_content = True # Enable message content intent to receive message content in on_message event since it's disabled by default
Client = discord.Client(intents=Intents) # Create a new bot client with the intents

# 03: Message functionality
async def send_message(message: discord.Message, user_message: str) -> None:
    # Check if the message is empty (no content, embeds, or attachments)
    if not message.content and not message.embeds and not message.attachments:
        print("Message was empty (no content, embeds, or attachments).")
        return
    
    try:
        await message.channel.send("Hey! I'm Avalore bot developed by Muska") # Send the response to the same channel where the message was received
    except Exception as e:
        print(e)

# Handles the event when the bot is connected to Discord Server
@Client.event
async def on_ready() -> None:
    print(f'{Client.user} has connected to Discord Server!') # Print the bot's username and ID to the console when connected to Discord Server

# Handles the event when a message is sent in a channel where the bot has access
@Client.event
async def on_message(message: discord.Message) -> None:
    if message.author == Client.user: # Check if the message was sent by the bot itself
        return

    print(f'{message.author.name} sent: {message.content}') # Print the message content and author's name to the console

    await send_message(message, message.content) # Send a response based on the message content

def main() -> None:
    Client.run(TOKEN) # Run the bot with the token obtained from the environment variables

if __name__ == '__main__':
    main() # Run the main function when the script is executed