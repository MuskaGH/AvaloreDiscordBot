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
GITHUB_CHECK_INTERVAL_OPTIONS = (
    ("30 seconds", 30),
    ("1 minute", 60),
    ("2 minutes", 120),
    ("5 minutes", 300),
)
GITHUB_CHECK_INTERVAL = 60  # Default: check every 1 minute (60 seconds)
GITHUB_MAX_COMMITS_PER_BRANCH = 100  # Safety cap for one branch backfill per check
GITHUB_POSTED_COMMITS_LIMIT = 5000  # Maximum commit SHAs kept for cross-branch dedupe
DISCORD_MESSAGE_LIMIT = 2000  # Discord content limit for a single message
LAST_COMMIT_FILE = "last_commit.txt"  # File to store the last processed commit SHA
