import discord
from discord.ext import commands

from utils import send_avalore_update_message, read_avalore_update_file

# Creates a new bot client with the default intents and enables message content intent
Intents = discord.Intents.default() # Intents object with the default intents (messages, reactions, etc.)
Intents.message_content = True # Enable message content intent to receive message content in on_message event since it's disabled by default
Client = commands.Bot(command_prefix='!Avalore.', intents=Intents) # Create a new bot client with the intents

# Decorator to register an on_ready event (whenever the bot is connected to Discord Server)
@Client.event
async def on_ready() -> None:
    print(f'{Client.user} has connected to Discord Server!') # Print the bot's username and ID to the console when connected to Discord Server

# Decorator to register a new command named announce_avalore_update (can be invoked using !announce_avalore_update)
@Client.command(name='announce_avalore_update')
async def announce_avalore_update(ctx: commands.Context) -> None:
    if ctx.author.id != 597689905040064522: # Check if the user invoking the command is muskadev (id: 597689905040064522)
        return # Ignore the command if the user is not muskadev
    update_message = read_avalore_update_file('avalore_update_data.txt') # Read the update information from the file
    await send_avalore_update_message(ctx.channel, update_message) # Send the update message to the same channel where the command was invoked