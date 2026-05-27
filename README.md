# Scripts

A collection of local utility scripts, desktop environment tweaks, and automation tools.

## Structure

- `desktop/`: Hardware configurations and desktop environment wrappers.
- `dev/`: Development utilities and code analysis tools.
- `multimedia/`: Audio and video download/extraction tools.
- `services/`: Background monitors and systemd service files.
- `tests/`: Automated test suites (using pytest).
- `utils/`: Generic command-line utility scripts.

## Installation

This repository uses a centralized installer that deploys virtual environment-isolated binary wrappers straight to your local path (`~/.local/bin`):

```bash
./setup.py
```

## Testing

To run the test suite inside the local environment:

```
.venv/bin/pytest tests/
```
