# Scripts

A collection of local utility scripts, desktop environment tweaks, and automation tools.

## Structure

- `desktop/`: Hardware configurations and desktop environment wrappers.
- `dev/`: Development utilities and code analysis tools (including `hx-find` and `hx-jump`).
- `multimedia/`: Audio and video download/extraction tools.
- `services/`: Background monitors and systemd service files.
- `tests/`: Automated test suites (using pytest).
- `utils/`: Generic command-line utility scripts.

## Prerequisites

Some tools require the following system packages to be installed:
- `ripgrep` (`rg`): For fast code searching.
- `fzf`: For fuzzy selection in the CLI.

## Installation

This repository uses a centralized installer that deploys virtual environment-isolated binary wrappers straight to your local path (`~/.local/bin`):

./setup.py

## Usage: Developer Bridge

The `dev/` tools allow seamless navigation from your terminal directly into a running `hx` instance within `tmux`:

- `hx-find <pattern>`: Search code using `ripgrep` and `fzf`, then jump to the selected result in Helix.
- `hx-jump <file:line>`: Directly command a `tmux` pane running Helix to open a specific file and line.

## Testing

To run the test suite inside the local environment:

.venv/bin/pytest tests/
