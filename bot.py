import discord

from utils import send_message

# 02: Create a new bot client
Intents = discord.Intents.default() # Intents object with the default intents (messages, reactions, etc.) used by the bot
Intents.message_content = True # Enable message content intent to receive message content in on_message event since it's disabled by default
Client = discord.Client(intents=Intents) # Create a new bot client with the intents

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