# Contributing Guidelines

Thank you for wanting to contribute to this project! To maintain a clean and accurate repository history, please follow these guidelines when submitting pull requests.

## 🚫 AI Attribution & Co-Author Policy

We do not allow AI assistant bot accounts (such as Claude, GitHub Copilot, etc.) to be listed as co-authors or contributors in this repository's Git history. 

Before making a commit or opening a Pull Request, you **must disable automatic AI attribution** in your local tools and environments.

### How to configure your tools:

#### 1. Claude CLI / Claude Code
If you use Claude's command-line tools, make sure it is not automatically injecting attribution into your commits. You can also add a `CLAUDE.md` to your own local workspace with the following instruction:
> "Do not include any AI assistant as a co-author or contributor in commit messages."

#### 2. Manual Commit Checks
Ensure your commit descriptions do not contain hidden trailer lines at the very bottom, such as:
`Co-authored-by: Claude <claude@anthropic.com>`

### ⚠️ Note on PR Submissions
Pull Requests containing AI co-author metadata will be closed or rejected. If a commit with AI attribution is merged, it permanently messes up the repository's contributor stats on GitHub due to internal platform caching. Please review your `git log` before pushing!
