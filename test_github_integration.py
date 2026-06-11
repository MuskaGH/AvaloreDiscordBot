import json
import os
import tempfile
import unittest

import constants
from github_integration import GitHubMonitor


def make_branch(name, commit_sha):
    return {"name": name, "commit": {"sha": commit_sha}}


def make_commit(commit_sha, title, date):
    return {
        "sha": commit_sha,
        "commit": {
            "message": title,
            "author": {"name": "Martin", "date": date},
            "committer": {"date": date},
        },
    }


class TempStateMixin:
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_last_commit_file = constants.LAST_COMMIT_FILE
        self.old_posted_commits_limit = constants.GITHUB_POSTED_COMMITS_LIMIT
        constants.LAST_COMMIT_FILE = os.path.join(self.temp_dir.name, "last_commit.txt")
        constants.GITHUB_POSTED_COMMITS_LIMIT = 5000

    def tearDown(self):
        constants.LAST_COMMIT_FILE = self.old_last_commit_file
        constants.GITHUB_POSTED_COMMITS_LIMIT = self.old_posted_commits_limit
        self.temp_dir.cleanup()

    def write_raw_state(self, content):
        with open(constants.LAST_COMMIT_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def write_json_state(self, state):
        with open(constants.LAST_COMMIT_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def read_json_state(self):
        with open(constants.LAST_COMMIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


class FakeGitHubMonitor(GitHubMonitor):
    def __init__(
        self,
        branches=None,
        branch_commits=None,
        commit_details=None,
        recent_commits=None,
    ):
        super().__init__()
        self.branches = branches or []
        self.branch_commits = branch_commits or {}
        self.commit_details = commit_details or {}
        self.recent_commits = recent_commits or {}

    async def get_branches(self):
        return self.branches

    async def get_branch_commits_since(self, session, branch_name, last_processed_sha):
        return self.branch_commits.get(branch_name, ([], True))

    async def get_commit_details(self, commit_sha, session=None):
        return self.commit_details.get(commit_sha)

    async def get_recent_commits_for_ref(self, session, git_ref):
        return self.recent_commits.get(git_ref, [])


class GitHubMonitorStateTests(TempStateMixin, unittest.TestCase):
    def test_reads_legacy_branch_and_posted_commit_state(self):
        monitor = GitHubMonitor()

        self.write_raw_state(" ABC123 ")
        branch_state, posted_commits, legacy_sha, posted_commits_present = (
            monitor.get_processed_commit_state()
        )

        self.assertEqual({}, branch_state)
        self.assertEqual([], posted_commits)
        self.assertEqual("abc123", legacy_sha)
        self.assertFalse(posted_commits_present)

        self.write_json_state(
            {
                "branches": {"main": " AAA111 ", "bad": 12},
                "posted_commits": ["BBB222", "bbb222", "", "CCC333", 7],
            }
        )
        branch_state, posted_commits, legacy_sha, posted_commits_present = (
            monitor.get_processed_commit_state()
        )

        self.assertEqual({"main": "aaa111"}, branch_state)
        self.assertEqual(["bbb222", "ccc333"], posted_commits)
        self.assertIsNone(legacy_sha)
        self.assertTrue(posted_commits_present)

        self.write_json_state({"branches": {"main": "DDD444"}})
        branch_state, posted_commits, legacy_sha, posted_commits_present = (
            monitor.get_processed_commit_state()
        )

        self.assertEqual({"main": "ddd444"}, branch_state)
        self.assertEqual([], posted_commits)
        self.assertIsNone(legacy_sha)
        self.assertFalse(posted_commits_present)


class GitHubMonitorScanTests(TempStateMixin, unittest.IsolatedAsyncioTestCase):
    async def test_missing_posted_history_is_seeded_from_tracked_branch_heads(self):
        sha_a = "a" * 40
        sha_b = "b" * 40
        sha_c = "c" * 40
        self.write_json_state({"branches": {"feature": sha_c}})

        monitor = FakeGitHubMonitor(
            branches=[make_branch("feature", sha_c)],
            recent_commits={
                sha_c: [
                    make_commit(sha_c, "Feature head", "2026-01-03T00:00:00Z"),
                    make_commit(sha_b, "Feature middle", "2026-01-02T00:00:00Z"),
                    make_commit(sha_a, "Feature base", "2026-01-01T00:00:00Z"),
                ]
            },
        )

        messages = await monitor.check_for_new_commits()
        saved_state = self.read_json_state()

        self.assertEqual([], messages)
        self.assertEqual([sha_a, sha_b, sha_c], saved_state["posted_commits"])

    async def test_exact_sha_is_queued_once_across_branches_in_same_scan(self):
        feature_base = "0" * 40
        main_base = "1" * 40
        shared_one = "2" * 40
        shared_two = "3" * 40
        merge_commit = "4" * 40
        self.write_json_state(
            {
                "branches": {"feature": feature_base, "main": main_base},
                "posted_commits": [],
            }
        )

        shared_one_commit = make_commit(shared_one, "Shared one", "2026-01-01T00:00:00Z")
        shared_two_commit = make_commit(shared_two, "Shared two", "2026-01-02T00:00:00Z")
        merge_commit_data = make_commit(merge_commit, "Merge feature", "2026-01-03T00:00:00Z")
        monitor = FakeGitHubMonitor(
            branches=[
                make_branch("feature", shared_two),
                make_branch("main", merge_commit),
            ],
            branch_commits={
                "feature": ([shared_two_commit, shared_one_commit], True),
                "main": ([merge_commit_data, shared_two_commit, shared_one_commit], True),
            },
            commit_details={
                shared_one: shared_one_commit,
                shared_two: shared_two_commit,
                merge_commit: merge_commit_data,
            },
        )

        messages = await monitor.check_for_new_commits()
        saved_state = self.read_json_state()

        self.assertEqual(3, len(messages))
        self.assertEqual(1, sum("[Commit] 2222222" in message for message in messages))
        self.assertEqual(1, sum("[Commit] 3333333" in message for message in messages))
        self.assertEqual(1, sum("[Commit] 4444444" in message for message in messages))
        self.assertIn("[Branch] feature", messages[0])
        self.assertIn("[Branch] feature", messages[1])
        self.assertIn("[Branch] main", messages[2])
        self.assertEqual(shared_two, saved_state["branches"]["feature"])
        self.assertEqual(merge_commit, saved_state["branches"]["main"])
        self.assertEqual(
            [shared_one, shared_two, merge_commit],
            saved_state["posted_commits"],
        )

    async def test_already_posted_commit_updates_branch_head_without_message(self):
        old_main = "5" * 40
        already_posted = "6" * 40
        already_posted_commit = make_commit(
            already_posted,
            "Already posted",
            "2026-01-04T00:00:00Z",
        )
        self.write_json_state(
            {
                "branches": {"main": old_main},
                "posted_commits": [already_posted],
            }
        )
        monitor = FakeGitHubMonitor(
            branches=[make_branch("main", already_posted)],
            branch_commits={"main": ([already_posted_commit], True)},
            commit_details={already_posted: already_posted_commit},
        )

        messages = await monitor.check_for_new_commits()
        saved_state = self.read_json_state()

        self.assertEqual([], messages)
        self.assertEqual(already_posted, saved_state["branches"]["main"])
        self.assertEqual([already_posted], saved_state["posted_commits"])


if __name__ == "__main__":
    unittest.main()
