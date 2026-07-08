# CommitsBot

Discord bot that monitors GitHub repositories for new commits and posts formatted, real-time updates to a dedicated Discord channel per project. Watches every branch, backfills missed commits, and deduplicates across branches so merged commits are not posted twice.

Configured projects live in `constants.py` (`PROJECTS`). See `SETUP_GUIDE.md` for setup and how to add a project.
