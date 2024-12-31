import discord
import constants
import asyncio
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

# Decorator to register a new command named announce_avalore_update (can be invoked using !Avalore.announce_avalore_update)
@Client.command(name='announce_avalore_update')
async def announce_avalore_update(ctx: commands.Context) -> None:
    if ctx.author.id != constants.MUSKADEV_ID: # Check if the user invoking the command is muskadev
        return # Ignore the command if the user is not muskadev
    
    # Ask for confirmation before sending the update message to the 'patches' channel
    await ctx.send("Are you sure you filled fresh update data? Reply with 'yes' to confirm.")

    # Function to check if the message author is the same as the command invoker and the message content is 'yes'
    def check(m):
        return m.author == ctx.author and m.content.lower() == 'yes'

    try: # Try to wait for a message that satisfies the check function with a timeout of 'AVALORE_UPDATE_TIMOUT_LIMIT' seconds
        confirmation = await Client.wait_for('message', check=check, timeout=constants.AVALORE_UPDATE_TIMOUT_LIMIT)
        if confirmation: # If the confirmation message is received
            channel = Client.get_channel(constants.CHANNEL_ID_PATCHES) # Get the 'channel' object from the channel ID
            await send_avalore_update_message(channel, read_avalore_update_file('avalore_update_data.txt')) # Send the update message to the 'patches' channel
    except asyncio.TimeoutError: # If the timeout limit is reached without receiving the confirmation message (the user didn't reply with 'yes')
        await ctx.send("Update announcement cancelled. Please try again.") # Send a message to the command invoker that the update announcement is cancelled