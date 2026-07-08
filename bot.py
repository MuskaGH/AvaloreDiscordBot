import discord
import constants
import asyncio
from discord.ext import commands, tasks

from github_integration import GitHubMonitor

# Creates a new bot client with the default intents and enables message content intent
Intents = discord.Intents.default() # Intents object with the default intents (messages, reactions, etc.)
Intents.message_content = True # Enable message content intent to receive message content in on_message event since it's disabled by default
Client = commands.Bot(command_prefix='!CommitsBot.', intents=Intents) # Create a new bot client with the intents

# Initialize one GitHub monitor per configured project
project_monitors = tuple(
    (project, GitHubMonitor(project)) for project in constants.PROJECTS
)
_github_check_interval = constants.GITHUB_CHECK_INTERVAL
_github_check_lock = None
_unconfigured_projects_warned = set()


def format_github_check_interval(seconds: int) -> str:
    """Return a readable label for a GitHub check interval."""
    for label, value in constants.GITHUB_CHECK_INTERVAL_OPTIONS:
        if value == seconds:
            return label
    return f"{seconds} seconds"


def get_github_check_interval() -> int:
    """Return the currently configured GitHub check interval."""
    return _github_check_interval


def set_github_check_interval(seconds: int) -> int:
    """Set the background GitHub check interval."""
    allowed_intervals = {value for _, value in constants.GITHUB_CHECK_INTERVAL_OPTIONS}
    seconds = int(seconds)

    if seconds not in allowed_intervals:
        raise ValueError(f"Unsupported GitHub check interval: {seconds} seconds")

    global _github_check_interval
    _github_check_interval = seconds
    check_github_commits.change_interval(seconds=seconds)
    print(f"GitHub check interval set to {format_github_check_interval(seconds)}.")
    return seconds


def _get_github_check_lock() -> asyncio.Lock:
    """Create the check lock lazily on the bot event loop."""
    global _github_check_lock
    if _github_check_lock is None:
        _github_check_lock = asyncio.Lock()
    return _github_check_lock


async def _run_project_commit_check(
    project: constants.ProjectConfig,
    monitor: GitHubMonitor,
) -> bool:
    """Check one project for new commits and post them to its Discord channel."""
    # Check for new commits, but do not advance state until Discord delivery succeeds.
    commit_check = await monitor.check_for_new_commit_updates()

    if commit_check.updates:
        # Get the project's updates channel
        channel = Client.get_channel(project.channel_id)

        if isinstance(channel, discord.TextChannel):
            posted_commits = list(commit_check.posted_commits)

            try:
                # Send every queued commit update in chronological order.
                for commit_update in commit_check.updates:
                    await channel.send(commit_update.message)
                    posted_commits.append(commit_update.commit_sha)
                    monitor.save_processed_commits(
                        commit_check.branch_state,
                        posted_commits,
                    )
            except Exception as e:
                print(f"Error sending {project.display_name} commit update to Discord: {e}")
                return False

            monitor.save_processed_commits(
                commit_check.next_branch_state,
                posted_commits,
            )

            print(
                f"Posted {len(commit_check.updates)} new {project.display_name} commit update(s) "
                f"to Discord at {discord.utils.utcnow()}"
            )
            return True

        print(f"Error: updates channel for {project.display_name} not found or is not a text channel.")
        return False

    if commit_check.should_save_state:
        monitor.save_processed_commits(
            commit_check.next_branch_state,
            commit_check.posted_commits,
        )

    return False


async def run_github_commit_check(manual: bool = False) -> bool:
    """Run one GitHub commit check across all projects and post any new commits."""
    check_lock = _get_github_check_lock()

    if check_lock.locked():
        check_type = "manual" if manual else "scheduled"
        print(f"GitHub check already in progress; skipping {check_type} check.")
        return False

    async with check_lock:
        if manual:
            print("Manual GitHub check requested.")

        posted_any = False

        for project, monitor in project_monitors:
            if not project.channel_id:
                if project.key not in _unconfigured_projects_warned:
                    print(
                        f"Skipping {project.display_name}: no Discord channel configured "
                        f"(set channel_id for '{project.key}' in constants.py)."
                    )
                    _unconfigured_projects_warned.add(project.key)
                continue

            try:
                if await _run_project_commit_check(project, monitor):
                    posted_any = True
            except Exception as e:
                print(f"Error checking {project.display_name} for new commits: {e}")

        if manual and not posted_any:
            print("Manual GitHub check completed; no new commits found.")

        return posted_any


async def force_github_commit_check() -> bool:
    """Force an immediate GitHub commit check."""
    return await run_github_commit_check(manual=True)

# Background task to check for new GitHub commits
@tasks.loop(seconds=constants.GITHUB_CHECK_INTERVAL)
async def check_github_commits() -> None:
    """Background task that checks for new commits at the configured interval."""
    try:
        await run_github_commit_check()
    except Exception as e:
        print(f"Error in GitHub commit checker: {e}")

@check_github_commits.before_loop
async def before_check_github_commits() -> None:
    """Wait until the bot is ready before starting the background task."""
    await Client.wait_until_ready()
    print(f"GitHub commit checker started. Checking every {format_github_check_interval(_github_check_interval)}...")

# Decorator to register an on_ready event (whenever the bot is connected to Discord Server)
@Client.event
async def on_ready() -> None:
    print(f'{Client.user} has connected to Discord Server!') # Print the bot's username and ID to the console when connected to Discord Server
    
    # Start the GitHub commit checker if it's not already running
    if not check_github_commits.is_running():
        check_github_commits.start()
