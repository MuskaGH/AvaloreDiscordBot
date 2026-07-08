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
        self.project = constants.ProjectConfig(
            key="test",
            display_name="Avalore",
            repo_owner="MuskaGH",
            repo_name="Avalore",
            channel_id=123,
            state_file=os.path.join(self.temp_dir.name, "last_commit.txt"),
        )
        self.old_posted_commits_limit = constants.GITHUB_POSTED_COMMITS_LIMIT
        self.old_discord_message_limit = constants.DISCORD_MESSAGE_LIMIT
        constants.GITHUB_POSTED_COMMITS_LIMIT = 5000
        constants.DISCORD_MESSAGE_LIMIT = 2000

    def tearDown(self):
        constants.GITHUB_POSTED_COMMITS_LIMIT = self.old_posted_commits_limit
        constants.DISCORD_MESSAGE_LIMIT = self.old_discord_message_limit
        self.temp_dir.cleanup()

    def write_raw_state(self, content):
        with open(self.project.state_file, "w", encoding="utf-8") as f:
            f.write(content)

    def write_json_state(self, state):
        with open(self.project.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def read_json_state(self):
        with open(self.project.state_file, "r", encoding="utf-8") as f:
            return json.load(f)


class FakeGitHubMonitor(GitHubMonitor):
    def __init__(
        self,
        project=None,
        branches=None,
        branch_commits=None,
        commit_details=None,
        recent_commits=None,
    ):
        super().__init__(project)
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
        monitor = GitHubMonitor(self.project)

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


class GitHubMonitorFormattingTests(TempStateMixin, unittest.TestCase):
    def test_commit_message_is_truncated_to_discord_limit(self):
        monitor = GitHubMonitor(self.project)
        long_body = "\n".join(f"- Change item {index} with detailed explanation." for index in range(200))
        commit_data = make_commit(
            "9" * 40,
            f"Large commit\n{long_body}",
            "2026-01-06T00:00:00Z",
        )

        message = monitor.format_commit_message(commit_data, branch_name="main")

        self.assertLessEqual(len(message), constants.DISCORD_MESSAGE_LIMIT)
        self.assertIn("Changes truncated to fit Discord's 2000-character message limit.", message)
        self.assertTrue(message.endswith("```"))


class MultiProjectTests(TempStateMixin, unittest.TestCase):
    def test_duplicate_project_state_files_are_rejected(self):
        colliding_project = constants.ProjectConfig(
            key="colliding",
            display_name="Colliding",
            repo_owner="MuskaGH",
            repo_name="Colliding",
            channel_id=456,
            state_file=self.project.state_file,
        )

        with self.assertRaises(ValueError):
            constants.validate_projects([self.project, colliding_project])

        with self.assertRaises(ValueError):
            constants.validate_projects([self.project, self.project])


    def test_monitors_use_per_project_state_and_message_header(self):
        second_project = constants.ProjectConfig(
            key="second",
            display_name="ThatsIllegalNow",
            repo_owner="MuskaGH",
            repo_name="ThatsIllegalNow",
            channel_id=456,
            state_file=os.path.join(self.temp_dir.name, "last_commit_second.txt"),
        )
        first_monitor = GitHubMonitor(self.project)
        second_monitor = GitHubMonitor(second_project)

        first_monitor.save_processed_commits({"main": "a" * 40}, ["a" * 40])
        second_monitor.save_processed_commits({"main": "b" * 40}, ["b" * 40])

        first_state, first_posted, _, _ = first_monitor.get_processed_commit_state()
        second_state, second_posted, _, _ = second_monitor.get_processed_commit_state()

        self.assertEqual({"main": "a" * 40}, first_state)
        self.assertEqual(["a" * 40], first_posted)
        self.assertEqual({"main": "b" * 40}, second_state)
        self.assertEqual(["b" * 40], second_posted)

        message = second_monitor.format_commit_message(
            make_commit("c" * 40, "Title", "2026-01-01T00:00:00Z"),
            branch_name="main",
        )
        self.assertIn("New commit to ThatsIllegalNow's GitHub repository detected!", message)


class GitHubMonitorScanTests(TempStateMixin, unittest.IsolatedAsyncioTestCase):
    async def test_missing_posted_history_is_seeded_from_tracked_branch_heads(self):
        sha_a = "a" * 40
        sha_b = "b" * 40
        sha_c = "c" * 40
        self.write_json_state({"branches": {"feature": sha_c}})

        monitor = FakeGitHubMonitor(
            project=self.project,
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
            project=self.project,
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
            project=self.project,
            branches=[make_branch("main", already_posted)],
            branch_commits={"main": ([already_posted_commit], True)},
            commit_details={already_posted: already_posted_commit},
        )

        messages = await monitor.check_for_new_commits()
        saved_state = self.read_json_state()

        self.assertEqual([], messages)
        self.assertEqual(already_posted, saved_state["branches"]["main"])
        self.assertEqual([already_posted], saved_state["posted_commits"])

    async def test_collecting_updates_does_not_advance_state_before_delivery(self):
        old_main = "7" * 40
        new_main = "8" * 40
        new_main_commit = make_commit(
            new_main,
            "Needs Discord delivery first",
            "2026-01-05T00:00:00Z",
        )
        initial_state = {
            "branches": {"main": old_main},
            "posted_commits": [],
        }
        self.write_json_state(initial_state)
        monitor = FakeGitHubMonitor(
            project=self.project,
            branches=[make_branch("main", new_main)],
            branch_commits={"main": ([new_main_commit], True)},
            commit_details={new_main: new_main_commit},
        )

        check_result = await monitor.check_for_new_commit_updates()
        saved_state = self.read_json_state()

        self.assertEqual(1, len(check_result.updates))
        self.assertEqual(new_main, check_result.updates[0].commit_sha)
        self.assertEqual(initial_state, saved_state)


if __name__ == "__main__":
    unittest.main()
