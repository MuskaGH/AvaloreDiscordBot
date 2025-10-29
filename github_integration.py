import aiohttp
import constants
from datetime import datetime
from typing import Optional, Dict, Any
import os

class GitHubMonitor:
    """Monitors GitHub repository for new commits and formats update messages."""
    
    def __init__(self):
        self.api_base = "https://api.github.com"
        self.repo_url = f"{self.api_base}/repos/{constants.GITHUB_REPO_OWNER}/{constants.GITHUB_REPO_NAME}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {constants.GITHUB_TOKEN}" if constants.GITHUB_TOKEN else None
        }
        # Remove Authorization header if no token is provided
        if not constants.GITHUB_TOKEN:
            del self.headers["Authorization"]
    
    def get_last_processed_commit(self) -> Optional[str]:
        """Read the last processed commit SHA from file."""
        try:
            if os.path.exists(constants.LAST_COMMIT_FILE):
                with open(constants.LAST_COMMIT_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error reading last commit file: {e}")
        return None
    
    def save_last_processed_commit(self, commit_sha: str) -> None:
        """Save the last processed commit SHA to file."""
        try:
            with open(constants.LAST_COMMIT_FILE, 'w') as f:
                f.write(commit_sha)
        except Exception as e:
            print(f"Error saving last commit file: {e}")
    
    async def get_latest_commit(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest commit from the GitHub repository."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.repo_url}/commits",
                    headers=self.headers,
                    params={"per_page": 1}
                ) as response:
                    if response.status == 200:
                        commits = await response.json()
                        if commits:
                            return commits[0]
                    elif response.status == 401:
                        print("GitHub API authentication failed. Please check your token.")
                    elif response.status == 404:
                        print("Repository not found. Please check the repository name and your access.")
                    else:
                        print(f"GitHub API error: {response.status}")
        except Exception as e:
            print(f"Error fetching latest commit: {e}")
        return None
    
    async def get_commit_details(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information about a specific commit."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.repo_url}/commits/{commit_sha}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            print(f"Error fetching commit details: {e}")
        return None
    
    def format_commit_message(self, commit_data: Dict[str, Any]) -> str:
        """Format commit data into a Discord-friendly message."""
        try:
            # Extract commit information
            commit_info = commit_data.get('commit', {})
            author_name = commit_info.get('author', {}).get('name', 'Unknown')
            commit_message = commit_info.get('message', 'No message')
            commit_sha = commit_data.get('sha', '')[:7]  # Short SHA
            
            # Split commit message into title and body
            message_lines = commit_message.split('\n', 1)
            title = message_lines[0]
            body = message_lines[1].strip() if len(message_lines) > 1 else ""
            
            # Get current time
            now = datetime.now()
            
            # Format the message
            formatted_lines = [
                "**New commit to Avalore's GitHub repository detected!**",
                "```ini",
                f"Date: {now.strftime('%d/%m/%Y (CET)')}",
                f"Time: {now.strftime('%I:%M %p (CET)')}",
                "",
                f"[Author] {author_name}",
                f"[Commit] {commit_sha}",
                f"[Title] {title}",
                ""
            ]
            
            # Add commit body if present (renamed to "Changes")
            if body:
                formatted_lines.append("[Changes]")
                # Split by sentences (periods followed by space or end of string)
                import re
                sentences = re.split(r'\.\s+', body)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        # Add period back if it doesn't end with one
                        if not sentence.endswith('.'):
                            sentence += '.'
                        formatted_lines.append(f"- {sentence}")
            
            formatted_lines.append("```")
            
            return "\n".join(formatted_lines)
        except Exception as e:
            print(f"Error formatting commit message: {e}")
            return "Failed to format commit message."
    
    def _format_file_changes(self, files: list) -> list:
        """Format the list of changed files into a readable summary."""
        if not files:
            return ["- No file information available"]
        
        summary = []
        
        # Group files by change type
        added = [f for f in files if f.get('status') == 'added']
        modified = [f for f in files if f.get('status') == 'modified']
        removed = [f for f in files if f.get('status') == 'removed']
        renamed = [f for f in files if f.get('status') == 'renamed']
        
        if added:
            summary.append(f"- Added {len(added)} file(s): {', '.join([f['filename'] for f in added[:3]])}")
            if len(added) > 3:
                summary.append(f"  ... and {len(added) - 3} more")
        
        if modified:
            summary.append(f"- Modified {len(modified)} file(s): {', '.join([f['filename'] for f in modified[:3]])}")
            if len(modified) > 3:
                summary.append(f"  ... and {len(modified) - 3} more")
        
        if removed:
            summary.append(f"- Removed {len(removed)} file(s): {', '.join([f['filename'] for f in removed[:3]])}")
            if len(removed) > 3:
                summary.append(f"  ... and {len(removed) - 3} more")
        
        if renamed:
            summary.append(f"- Renamed {len(renamed)} file(s)")
        
        # Add total changes summary
        total_additions = sum(f.get('additions', 0) for f in files)
        total_deletions = sum(f.get('deletions', 0) for f in files)
        summary.append(f"- Total: +{total_additions} additions, -{total_deletions} deletions")
        
        return summary
    
    async def check_for_new_commits(self) -> Optional[str]:
        """Check for new commits and return formatted message if found."""
        print("Checking GitHub for new commits...")
        
        latest_commit = await self.get_latest_commit()
        
        if not latest_commit:
            print("Failed to fetch latest commit from GitHub")
            return None
        
        latest_sha = latest_commit.get('sha')
        if not latest_sha:
            print("No commit SHA found in response")
            return None
        
        latest_sha_short = latest_sha[:7]
        last_processed_sha = self.get_last_processed_commit()
        
        # If this is a new commit (different from last processed)
        if latest_sha != last_processed_sha:
            print(f"New commit detected: {latest_sha_short}")
            
            # Get detailed commit information
            commit_details = await self.get_commit_details(latest_sha)
            
            if commit_details:
                # Save this commit as processed
                self.save_last_processed_commit(latest_sha)
                
                # Format and return the message
                return self.format_commit_message(commit_details)
        else:
            if last_processed_sha:
                print(f"No new commits (latest: {latest_sha_short})")
            else:
                print(f"First check - tracking commit: {latest_sha_short}")
                # Save this as the starting point
                self.save_last_processed_commit(latest_sha)
        
        return None
