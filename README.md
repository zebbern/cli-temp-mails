# TempMail Watcher

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

A professional CLI utility for managing temporary email inboxes in real-time. Polls your chosen service and displays incoming messages with rich formatting.

![temp watcher](https://github.com/user-attachments/assets/c016d682-ede9-4619-853a-3ed90df97cae)

## Features

- **Multiple Service Support** - Works with GuerrillaMail, mail.tm, tempmail.lol, mail.gw, and dropmail.me
- **Rich Terminal UI** - Beautiful, colorful display with clear message formatting
- **Message History** - Save and review past messages
- **Configuration System** - Save your preferences between sessions
- **Cross-Platform** - Works on Windows, macOS, and Linux

## Installation

```bash
# Clone the repository
git clone https://github.com/zebbern/tempmail-watcher.git
cd tempmail-watcher

# Install dependencies
pip install -r requirements.txt

# Make the script executable (Unix-like systems)
chmod +x tempmail.py
```

## Usage

### Basic Usage

```bash
# Launch with interactive menu
python tempmail.py

# Specify a provider directly
python tempmail.py mail.tm

# Change polling interval (seconds)
python tempmail.py --poll 10 guerrillamail
```

### Advanced Options

```bash
# Use rush mode for tempmail.lol (faster address generation)
python tempmail.py tempmail.lol --rush

# Use plain text display mode
python tempmail.py --display plain

# Don't save messages to history
python tempmail.py --no-save

# View help information
python tempmail.py --help
```

## Supported Providers

| Provider | Features | Notes |
|----------|----------|-------|
| mail.tm | Full body text, HTML support | Fast, reliable |
| mail.gw | Full body text, HTML support | Alternative to mail.tm |
| GuerrillaMail | Text & HTML, attachments | Well-established service |
| tempmail.lol | Basic text messages | Fast with rush option |
| dropmail.me | Text & HTML messages | GraphQL API |

## Configuration

TempMail Watcher saves your preferences in `~/.config/tempmail-watcher/config.json`. Settings include:

- Default provider
- Polling interval
- Display mode (rich/plain)
- Message history options

## History & Message Export

Received messages are saved to `~/.config/tempmail-watcher/history.json`.

---

<p align="center">
  Developed with ❤️ by <a href="https://github.com/zebbern">zebbern</a>
</p>

