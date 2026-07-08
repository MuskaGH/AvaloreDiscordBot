import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MUSKADEV_ID = 597689905040064522
AVALORE_UPDATE_TIMOUT_LIMIT = 10.0

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Load from .env file


@dataclass(frozen=True)
class ProjectConfig:
    """One monitored GitHub repository and the Discord channel it posts to."""
    key: str  # Short slug used for logs and warnings
    display_name: str  # Name used in the Discord message header
    repo_owner: str
    repo_name: str
    channel_id: int  # Discord channel that receives the commit updates (0 = not configured yet)
    state_file: str  # Per-project file storing branch heads and posted SHA history


PROJECTS = (
    ProjectConfig(
        key="avalore",
        display_name="Avalore",
        repo_owner="MuskaGH",
        repo_name="Avalore",
        channel_id=1324115430994083840,
        state_file="last_commit.txt",  # Keeps the pre-existing Avalore state and history
    ),
    ProjectConfig(
        key="thatsillegalnow",
        display_name="ThatsIllegalNow",
        repo_owner="MuskaGH",
        repo_name="ThatsIllegalNow",
        channel_id=1524212101315432580,  # TODO: set to the updates channel ID on the ThatsIllegalNow Discord server
        state_file="last_commit_thatsillegalnow.txt",
    ),
)


def validate_projects(projects) -> None:
    """Reject project lists whose keys or state files collide, which would mix per-project state."""
    seen_keys = set()
    seen_state_files = set()

    for project in projects:
        if project.key in seen_keys:
            raise ValueError(f"Duplicate project key: {project.key}")

        normalized_state_file = os.path.normcase(os.path.abspath(project.state_file))
        if normalized_state_file in seen_state_files:
            raise ValueError(f"Duplicate project state_file: {project.state_file}")

        seen_keys.add(project.key)
        seen_state_files.add(normalized_state_file)


validate_projects(PROJECTS)
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
