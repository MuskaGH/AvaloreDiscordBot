import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MUSKADEV_ID = 597689905040064522
CHANNEL_ID_PATCHES = 1324115430994083840
AVALORE_UPDATE_TIMOUT_LIMIT = 10.0

# GitHub Configuration
GITHUB_REPO_OWNER = "MuskaGH"
GITHUB_REPO_NAME = "Avalore"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Load from .env file
GITHUB_CHECK_INTERVAL = 60  # Check every 1 minute (60 seconds)
LAST_COMMIT_FILE = "last_commit.txt"  # File to store the last processed commit SHA
