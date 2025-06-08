import os
from bot import Client

from dotenv import load_dotenv

# Loads environment variables to make sure the bot token is not exposed to the public
load_dotenv() # Load the variables from .env file found in the same directory as this python file
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN') # Get the bot token variable from the environment variables

def main() -> None:
    if BOT_TOKEN is None:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not found. Please check your .env file.")
    Client.run(BOT_TOKEN) # Run the bot with the token obtained from the environment variables

if __name__ == '__main__':
    main() # Run the main function when the script is executed
