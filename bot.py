import discord
import constants
import asyncio
from discord.ext import commands, tasks

from github_integration import GitHubMonitor

# Creates a new bot client with the default intents and enables message content intent
Intents = discord.Intents.default() # Intents object with the default intents (messages, reactions, etc.)
Intents.message_content = True # Enable message content intent to receive message content in on_message event since it's disabled by default
Client = commands.Bot(command_prefix='!Avalore.', intents=Intents) # Create a new bot client with the intents

# Initialize GitHub monitor
github_monitor = GitHubMonitor()

# Background task to check for new GitHub commits
@tasks.loop(seconds=constants.GITHUB_CHECK_INTERVAL)
async def check_github_commits() -> None:
    """Background task that checks for new commits every 5 minutes."""
    try:
        # Check for new commits
        update_message = await github_monitor.check_for_new_commits()
        
        if update_message:
            # Get the patches channel
            channel = Client.get_channel(constants.CHANNEL_ID_PATCHES)
            
            if isinstance(channel, discord.TextChannel):
                # Send the update message
                await channel.send(update_message)
                print(f"Posted new commit update to Discord at {discord.utils.utcnow()}")
            else:
                print("Error: Patches channel not found or is not a text channel.")
    except Exception as e:
        print(f"Error in GitHub commit checker: {e}")

@check_github_commits.before_loop
async def before_check_github_commits() -> None:
    """Wait until the bot is ready before starting the background task."""
    await Client.wait_until_ready()
    print("GitHub commit checker started. Checking every 60 seconds...")

# Decorator to register an on_ready event (whenever the bot is connected to Discord Server)
@Client.event
async def on_ready() -> None:
    print(f'{Client.user} has connected to Discord Server!') # Print the bot's username and ID to the console when connected to Discord Server
    
    # Start the GitHub commit checker if it's not already running
    if not check_github_commits.is_running():
        check_github_commits.start()
