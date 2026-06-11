import aiohttp
import constants
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import os

class GitHubMonitor:
    """Monitors GitHub repository for new commits and formats update messages."""

    _bullet_prefix_pattern = re.compile(r"^\s*(?:(?:[-*\u2022\u2013\u2014])\s+|\d+[\.)]\s+)")
    
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
        branch_state, _, legacy_sha, _ = self.get_processed_commit_state()

        if legacy_sha:
            return legacy_sha

        if branch_state:
            return next(iter(branch_state.values()))

        return None
    
    def save_last_processed_commit(self, commit_sha: str) -> None:
        """Save the last processed commit SHA to file."""
        normalized_sha = self._normalize_commit_sha(commit_sha)

        if normalized_sha:
            self.save_processed_commits({"main": normalized_sha}, [normalized_sha])

    def get_processed_commits(self) -> Tuple[Dict[str, str], Optional[str]]:
        """Read branch-aware commit state, including old single-SHA files."""
        branch_state, _, legacy_sha, _ = self.get_processed_commit_state()
        return branch_state, legacy_sha

    def get_processed_commit_state(self) -> Tuple[Dict[str, str], List[str], Optional[str], bool]:
        """Read branch-aware state, posted SHA history, and legacy single-SHA files."""
        try:
            if not os.path.exists(constants.LAST_COMMIT_FILE):
                return {}, [], None, False

            with open(constants.LAST_COMMIT_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                return {}, [], None, False

            try:
                state = json.loads(content)
            except json.JSONDecodeError:
                return {}, [], self._normalize_commit_sha(content) or None, False

            if isinstance(state, str):
                return {}, [], self._normalize_commit_sha(state) or None, False

            if not isinstance(state, dict):
                return {}, [], None, False

            raw_branches = state.get("branches")
            if raw_branches is None:
                raw_branches = {
                    branch_name: commit_sha
                    for branch_name, commit_sha in state.items()
                    if branch_name != "posted_commits"
                }

            if not isinstance(raw_branches, dict):
                raw_branches = {}

            branch_state = {}
            for branch_name, commit_sha in raw_branches.items():
                if not isinstance(branch_name, str) or not isinstance(commit_sha, str):
                    continue

                branch_name = branch_name.strip()
                commit_sha = self._normalize_commit_sha(commit_sha)

                if branch_name and commit_sha:
                    branch_state[branch_name] = commit_sha

            posted_commits_present = isinstance(state.get("posted_commits"), list)
            posted_commits = self._normalize_posted_commits(state.get("posted_commits", []))

            return branch_state, posted_commits, None, posted_commits_present
        except Exception as e:
            print(f"Error reading last commit file: {e}")
            return {}, [], None, False

    def save_processed_commits(
        self,
        branch_state: Dict[str, str],
        posted_commits: Optional[List[str]] = None,
    ) -> None:
        """Save branch-aware commit state to file."""
        try:
            normalized_state = {
                branch_name: self._normalize_commit_sha(commit_sha)
                for branch_name, commit_sha in sorted(branch_state.items())
                if branch_name and self._normalize_commit_sha(commit_sha)
            }
            state = {
                "branches": normalized_state,
                "posted_commits": self._normalize_posted_commits(posted_commits or []),
            }

            with open(constants.LAST_COMMIT_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving last commit file: {e}")

    def _normalize_commit_sha(self, commit_sha: Any) -> str:
        """Return a normalized commit SHA for exact-match dedupe."""
        if not isinstance(commit_sha, str):
            return ""

        return commit_sha.strip().lower()

    def _normalize_posted_commits(self, posted_commits: Any) -> List[str]:
        """Return unique posted commit SHAs, preserving order and applying the state cap."""
        if not isinstance(posted_commits, list):
            return []

        normalized_commits = []
        seen_commits = set()

        for commit_sha in posted_commits:
            normalized_sha = self._normalize_commit_sha(commit_sha)

            if not normalized_sha or normalized_sha in seen_commits:
                continue

            normalized_commits.append(normalized_sha)
            seen_commits.add(normalized_sha)

        commit_limit = max(0, int(constants.GITHUB_POSTED_COMMITS_LIMIT))

        if not commit_limit:
            return []

        return normalized_commits[-commit_limit:]

    async def _fetch_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        context: str = "GitHub API",
    ) -> Optional[Any]:
        """Fetch JSON from GitHub and print consistent diagnostics."""
        try:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()

                if response.status == 401:
                    print("GitHub API authentication failed. Please check your token.")
                elif response.status == 404:
                    print("Repository not found. Please check the repository name and your access.")
                else:
                    print(f"{context} error: {response.status}")
        except Exception as e:
            print(f"Error during {context}: {e}")

        return None
    
    async def get_latest_commit(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest commit from the GitHub repository."""
        try:
            async with aiohttp.ClientSession() as session:
                commits = await self._fetch_json(
                    session,
                    f"{self.repo_url}/commits",
                    params={"per_page": 1},
                    context="fetching latest commit",
                )

                if commits:
                    return commits[0]
        except Exception as e:
            print(f"Error fetching latest commit: {e}")
        return None

    async def get_branches(self) -> List[Dict[str, Any]]:
        """Fetch all repository branches."""
        branches = []
        page = 1

        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    branch_page = await self._fetch_json(
                        session,
                        f"{self.repo_url}/branches",
                        params={"per_page": 100, "page": page},
                        context="fetching branches",
                    )

                    if not branch_page:
                        break

                    branches.extend(branch_page)

                    if len(branch_page) < 100:
                        break

                    page += 1
        except Exception as e:
            print(f"Error fetching branches: {e}")

        return branches
    
    async def get_commit_details(
        self,
        commit_sha: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch detailed information about a specific commit."""
        if session:
            return await self._fetch_json(
                session,
                f"{self.repo_url}/commits/{commit_sha}",
                context=f"fetching commit {commit_sha[:7]}",
            )

        try:
            async with aiohttp.ClientSession() as new_session:
                return await self._fetch_json(
                    new_session,
                    f"{self.repo_url}/commits/{commit_sha}",
                    context=f"fetching commit {commit_sha[:7]}",
                )
        except Exception as e:
            print(f"Error fetching commit details: {e}")
        return None

    async def get_branch_commits_since(
        self,
        session: aiohttp.ClientSession,
        branch_name: str,
        last_processed_sha: str,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch branch commits newer than the saved SHA."""
        commits = []
        page = 1
        max_commits = constants.GITHUB_MAX_COMMITS_PER_BRANCH

        while len(commits) < max_commits:
            per_page = min(100, max_commits - len(commits))
            commit_page = await self._fetch_json(
                session,
                f"{self.repo_url}/commits",
                params={"sha": branch_name, "per_page": per_page, "page": page},
                context=f"fetching commits for branch {branch_name}",
            )

            if not commit_page:
                break

            for commit_data in commit_page:
                commit_sha = self._normalize_commit_sha(commit_data.get('sha'))

                if commit_sha == last_processed_sha:
                    return commits, True

                commits.append(commit_data)

                if len(commits) >= max_commits:
                    break

            if len(commit_page) < per_page:
                break

            page += 1

        return commits, False

    async def get_recent_commits_for_ref(
        self,
        session: aiohttp.ClientSession,
        git_ref: str,
    ) -> List[Dict[str, Any]]:
        """Fetch recent commits reachable from a branch name or commit SHA."""
        commits = []
        page = 1
        max_commits = constants.GITHUB_MAX_COMMITS_PER_BRANCH

        while len(commits) < max_commits:
            per_page = min(100, max_commits - len(commits))
            commit_page = await self._fetch_json(
                session,
                f"{self.repo_url}/commits",
                params={"sha": git_ref, "per_page": per_page, "page": page},
                context=f"fetching recent commits for {git_ref[:7]}",
            )

            if not commit_page:
                break

            commits.extend(commit_page)

            if len(commit_page) < per_page:
                break

            page += 1

        return commits[:max_commits]

    async def seed_posted_commits_from_branch_state(
        self,
        session: aiohttp.ClientSession,
        branch_state: Dict[str, str],
        legacy_sha: Optional[str] = None,
    ) -> List[str]:
        """Build initial posted-SHA history from existing tracked branch heads."""
        seeded_commits = []
        seen_commits = set()

        def add_commit_sha(commit_sha: Any) -> None:
            normalized_sha = self._normalize_commit_sha(commit_sha)

            if not normalized_sha or normalized_sha in seen_commits:
                return

            seeded_commits.append(normalized_sha)
            seen_commits.add(normalized_sha)

        add_commit_sha(legacy_sha)

        for branch_name, head_sha in sorted(branch_state.items()):
            normalized_head_sha = self._normalize_commit_sha(head_sha)

            if not normalized_head_sha:
                continue

            commits = await self.get_recent_commits_for_ref(session, normalized_head_sha)

            # GitHub returns newest first; store oldest first so trimming keeps newest history.
            for commit_data in reversed(commits):
                add_commit_sha(commit_data.get('sha'))

            if commits:
                print(
                    f"Seeded {len(commits)} recent posted commit SHA(s) "
                    f"from tracked branch {branch_name}."
                )
            else:
                add_commit_sha(normalized_head_sha)

        return self._normalize_posted_commits(seeded_commits)
    
    def format_commit_message(self, commit_data: Dict[str, Any], branch_name: Optional[str] = None) -> str:
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
            ]

            if branch_name:
                formatted_lines.append(f"[Branch] {branch_name}")

            formatted_lines.extend([
                f"[Title] {title}",
                ""
            ])
            
            # Add commit body if present (renamed to "Changes")
            if body:
                formatted_lines.append("[Changes]")
                formatted_lines.extend(self._format_commit_body(body))
            
            formatted_lines.append("```")
            
            return "\n".join(formatted_lines)
        except Exception as e:
            print(f"Error formatting commit message: {e}")
            return "Failed to format commit message."

    def _format_commit_body(self, body: str) -> List[str]:
        """Format a commit body into Discord-friendly bullet lines."""
        formatted_lines = []
        plain_text_lines = []

        def flush_plain_text_lines():
            if not plain_text_lines:
                return

            plain_text = " ".join(plain_text_lines).strip()
            formatted_lines.extend(self._format_plain_text_as_bullets(plain_text))
            plain_text_lines.clear()

        for raw_line in body.splitlines():
            line = raw_line.strip()

            if not line:
                flush_plain_text_lines()
                continue

            if self._bullet_prefix_pattern.match(line):
                flush_plain_text_lines()
                bullet_text = self._bullet_prefix_pattern.sub("", line, count=1).strip()

                if bullet_text:
                    formatted_lines.append(f"- {bullet_text}")
                continue

            plain_text_lines.append(line)

        flush_plain_text_lines()
        return formatted_lines

    def _format_plain_text_as_bullets(self, text: str) -> List[str]:
        """Split plain prose into bullets without touching existing bullet lines."""
        bullet_lines = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if not sentence.endswith((".", "!", "?", ":", ";")):
                sentence += "."

            bullet_lines.append(f"- {sentence}")

        return bullet_lines
    
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

    def _get_commit_timestamp(self, commit_data: Dict[str, Any]) -> str:
        """Return an ISO timestamp suitable for sorting commit messages."""
        commit_info = commit_data.get('commit', {})
        return (
            commit_info.get('committer', {}).get('date')
            or commit_info.get('author', {}).get('date')
            or ""
        )
    
    async def check_for_new_commits(self) -> List[str]:
        """Check every branch for new commits and return formatted messages."""
        print("Checking GitHub for new commits...")

        branches = await self.get_branches()

        if not branches:
            print("Failed to fetch branches from GitHub")
            return []

        branch_state, posted_commits, legacy_sha, posted_commits_present = self.get_processed_commit_state()
        next_branch_state = {}
        pending_updates = []
        update_order = 0

        async with aiohttp.ClientSession() as session:
            if not posted_commits_present:
                posted_commits = await self.seed_posted_commits_from_branch_state(
                    session,
                    branch_state,
                    legacy_sha=legacy_sha,
                )

            posted_commit_shas = set(posted_commits)

            for branch in branches:
                branch_name = branch.get('name')
                head_sha = self._normalize_commit_sha(branch.get('commit', {}).get('sha'))

                if not branch_name or not head_sha:
                    continue

                last_processed_sha = branch_state.get(branch_name)
                baseline_sha = last_processed_sha or legacy_sha
                next_branch_state[branch_name] = head_sha

                if not baseline_sha:
                    print(f"First check - tracking branch {branch_name}: {head_sha[:7]}")
                    continue

                if head_sha == baseline_sha:
                    print(f"No new commits on {branch_name} (latest: {head_sha[:7]})")
                    continue

                commits, found_baseline = await self.get_branch_commits_since(
                    session,
                    branch_name,
                    baseline_sha,
                )

                if not commits:
                    print(f"No new commits on {branch_name} (latest: {head_sha[:7]})")
                    continue

                if not found_baseline and last_processed_sha is None:
                    print(
                        f"Branch {branch_name} does not contain the legacy starting commit; "
                        f"tracking from current head: {head_sha[:7]}"
                    )
                    continue

                if not found_baseline:
                    print(
                        f"Saved commit for {branch_name} was not found within "
                        f"{constants.GITHUB_MAX_COMMITS_PER_BRANCH} commits; posting fetched commits."
                    )

                print(f"New commits detected on {branch_name}: {len(commits)}")

                # GitHub returns newest first. Discord should receive oldest first.
                for commit_data in reversed(commits):
                    commit_sha = self._normalize_commit_sha(commit_data.get('sha'))
                    commit_details = None

                    if not commit_sha:
                        continue

                    if commit_sha in posted_commit_shas:
                        print(f"Skipping already posted commit {commit_sha[:7]} on {branch_name}.")
                        continue

                    commit_details = await self.get_commit_details(commit_sha, session=session)

                    formatted_commit = self.format_commit_message(
                        commit_details or commit_data,
                        branch_name=branch_name,
                    )
                    pending_updates.append((
                        self._get_commit_timestamp(commit_details or commit_data),
                        update_order,
                        formatted_commit,
                    ))
                    update_order += 1
                    posted_commits.append(commit_sha)
                    posted_commit_shas.add(commit_sha)

        self.save_processed_commits(next_branch_state, posted_commits)
        pending_updates.sort(key=lambda update: (update[0], update[1]))

        return [message for _, _, message in pending_updates]
