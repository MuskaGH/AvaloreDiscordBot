# GitHub Automation Setup Guide

This guide will help you set up the automated GitHub commit monitoring for your Discord bot.

## Overview

The bot now automatically:
- Checks your GitHub repository every 5 minutes for new commits
- Extracts commit information (author, message, changed files)
- Formats and posts updates to your Discord channel automatically
- No manual intervention needed!

## Setup Steps

### 1. Create a GitHub Personal Access Token (PAT)

Since your repository is private, you need to create a token for the bot to access it:

1. Go to GitHub.com and log in
2. Click your profile picture (top right) → **Settings**
3. Scroll down and click **Developer settings** (bottom left)
4. Click **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**
6. Configure the token:
   - **Note**: "Discord Bot - Avalore Repo Access"
   - **Expiration**: Choose your preference (recommend "No expiration" for convenience)
   - **Scopes**: Check the following:
     - ✅ `repo` (Full control of private repositories)
       - This will automatically check all sub-options
7. Click **Generate token** at the bottom
8. **IMPORTANT**: Copy the token immediately! You won't be able to see it again.
   - It will look something like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. Add the Token to Your Bot

1. Open `constants.py` in your project
2. Find the line: `GITHUB_TOKEN = ""`
3. Paste your token between the quotes:
   ```python
   GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```
4. Save the file

**Security Note**: Never commit this file to a public repository! The token gives access to your private repos.

### 3. Initialize the Last Commit Tracker

When you first run the bot, it needs to know which commit to start from. You have two options:

**Option A: Start fresh (recommended)**
- Just run the bot. It will automatically track the latest commit and only post NEW commits from that point forward.

**Option B: Manually set starting point**
- Create a file named `last_commit.txt` in your project directory
- Put the SHA of the last commit you want to start from (you can find this on GitHub)
- The bot will only post commits AFTER this one

### 4. Run the Bot

Simply run your bot as usual:
```bash
python main.py
```

You should see:
```
[Bot Username] has connected to Discord Server!
GitHub commit checker started. Checking every 5 minutes...
```

### 5. Test the Automation

To test if it's working:

1. Make a commit to your Avalore repository
2. Push it to GitHub
3. Wait up to 5 minutes
4. The bot should automatically post the update to your Discord channel!

## How It Works

### Automatic Posting
- Every 5 minutes, the bot checks GitHub for new commits
- If a new commit is found, it:
  - Extracts the commit author, message, and changed files
  - Formats it into a nice Discord message
  - Posts it automatically to your patches channel
  - Saves the commit SHA so it doesn't post duplicates

### Message Format
The automated messages include:
- Date and time (CET timezone)
- Commit author
- Commit SHA (short version)
- Commit title
- Commit description (if provided)
- List of changed files (added, modified, removed)
- Total additions and deletions
- Direct link to the commit on GitHub


## Configuration Options

You can customize the behavior in `constants.py`:

```python
# Check interval (in seconds)
GITHUB_CHECK_INTERVAL = 300  # 5 minutes (default)
# Change to 600 for 10 minutes, 900 for 15 minutes, etc.

# Repository details
GITHUB_REPO_OWNER = "MuskaGH"
GITHUB_REPO_NAME = "Avalore"
```

## Troubleshooting

### "GitHub API authentication failed"
- Your token is invalid or expired
- Generate a new token and update `constants.py`

### "Repository not found"
- Check that `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` are correct
- Ensure your token has `repo` scope access

### Bot doesn't post updates
- Check the console for error messages
- Verify the bot has permission to post in the patches channel
- Make sure the bot is running continuously (not just started and stopped)

### Duplicate posts
- The `last_commit.txt` file may have been deleted
- The bot will auto-recover by tracking from the next commit

## Important Notes

1. **Keep the bot running**: The bot must be running continuously to check for commits every 5 minutes
2. **Token security**: Never share your GitHub token or commit it to public repositories
3. **Rate limits**: GitHub API has rate limits (5000 requests/hour with token). Checking every 5 minutes uses ~12 requests/hour, so you're well within limits
4. **Private repo**: Your repository stays private - only the bot can access it with the token

## Need Help?

If you encounter any issues:
1. Check the console output for error messages
2. Verify your GitHub token has the correct permissions
3. Ensure the repository name and owner are correct in `constants.py`
