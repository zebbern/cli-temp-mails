#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# Temp Mail Watcher - A Professional Temporary Email Client
# Copyright © 2024‑2025  zebbern  <https://github.com/zebbern>
# ─────────────────────────────────────────────────────────────────────────────
# A professional CLI utility for managing throw‑away e‑mail inboxes in real‑time.
# Polls the chosen service at customizable intervals and displays incoming 
# messages with rich formatting. Supports multiple temporary email providers.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import random
import string
import sys
import time
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# Clear screen function
def clear_screen():
    """Clear the terminal screen based on the operating system."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

# Clear the screen immediately when script starts
clear_screen()

try:
    import requests
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme
except ImportError:
    print("Required dependencies not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "rich"])
    import requests
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

# Set up rich console with custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "email_from": "bold blue",
    "email_subject": "bold yellow",
    "email_date": "magenta",
    "email_body": "white",
    "header": "bold cyan",
})

console = Console(theme=custom_theme)

# Set up rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)

LOGGER = logging.getLogger("temp-mail-watcher")

##############################################################################
# Configuration and state management
##############################################################################

CONFIG_DIR = Path.home() / ".config" / "tempmail-watcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    if not CONFIG_FILE.exists():
        return {
            "default_provider": "mail.tm",
            "poll_interval": 5,
            "max_history_entries": 50,
            "save_messages": True,
            "display_mode": "rich",
        }
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.warning(f"Failed to load config: {e}. Using defaults.")
        return {
            "default_provider": "mail.tm",
            "poll_interval": 5,
            "max_history_entries": 50,
            "save_messages": True,
            "display_mode": "rich",
        }

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        LOGGER.error(f"Failed to save config: {e}")

def save_message_to_history(provider: str, address: str, message: Dict[str, Any]) -> None:
    """Save a received message to history."""
    config = load_config()
    if not config.get("save_messages", True):
        return
    
    ensure_config_dir()
    
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        else:
            history = []
        
        history.append({
            "provider": provider,
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
        
        # Limit history size
        max_entries = config.get("max_history_entries", 50)
        if len(history) > max_entries:
            history = history[-max_entries:]
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        LOGGER.warning(f"Failed to save message to history: {e}")

##############################################################################
# Utility helpers
##############################################################################

def _rand_string(n: int = 10) -> str:
    """Generate a random alphanumeric string of length n."""
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def _format_timestamp(timestamp: Optional[str]) -> str:
    """Format a timestamp in a human-readable way."""
    if not timestamp:
        return "unknown time"
    
    try:
        # Try different timestamp formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(timestamp, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        
        # If none of the formats match, just return the original
        return timestamp
    except Exception:
        return timestamp

def _print_email_rich(
    provider: str,
    sender: Optional[str],
    subject: Optional[str],
    date_: Optional[str],
    body: Optional[str],
) -> None:
    """Print an email using rich formatting."""
    # Instead of using a Table object, create a simple string representation directly
    email_info = []
    email_info.append(f"[bold]From:[/] [email_from]{sender or '(unknown)'}[/]")
    email_info.append(f"[bold]Subject:[/] [email_subject]{subject or '(no subject)'}[/]")
    if date_:
        email_info.append(f"[bold]Date:[/] [email_date]{_format_timestamp(date_)}[/]")
    
    email_header = "\n".join(email_info)
    
    formatted_body = body.strip() if body else "(no body)"
    
    panel = Panel(
        f"{email_header}\n\n{formatted_body}", 
        title=f"New Email [{provider}]",
        title_align="left",
        border_style="cyan"
    )
    
    console.print(panel)

def _print_email_plain(
    provider: str,
    sender: Optional[str],
    subject: Optional[str],
    date_: Optional[str],
    body: Optional[str],
) -> None:
    """Print an email in plain text format."""
    print("─" * 60)
    print(f"[{provider}] New Email")
    print(f"From:    {sender or '(unknown)'}")
    print(f"Subject: {subject or '(no subject)'}")
    if date_:
        print(f"Date:    {_format_timestamp(date_)}")
    print()
    print(body.strip() if body else "(no body)")
    print(flush=True)

def print_email(
    provider: str,
    address: str,
    sender: Optional[str],
    subject: Optional[str],
    date_: Optional[str],
    body: Optional[str],
    message_data: Dict[str, Any],
) -> None:
    """Print an email message with the configured display format."""
    config = load_config()
    
    if config.get("display_mode", "rich") == "rich":
        _print_email_rich(provider, sender, subject, date_, body)
    else:
        _print_email_plain(provider, sender, subject, date_, body)
    
    # Save message to history
    save_message_to_history(provider, address, {
        "from": sender,
        "subject": subject,
        "date": date_,
        "body": body,
        "raw_data": message_data
    })

##############################################################################
# Provider implementations
##############################################################################

def make_requests_session(timeout: int = 15) -> requests.Session:
    """Create a requests session with proper headers and timeout."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "TempMailWatcher/2.0 (https://github.com/zebbern/temp-mail-watcher)"
    })
    return session

class ProviderError(Exception):
    """Base exception for provider errors."""
    pass

class NetworkError(ProviderError):
    """Network-related errors."""
    pass

class APIError(ProviderError):
    """API response errors."""
    pass

##############################################################################
# Provider 1 – GuerrillaMail
##############################################################################

def run_guerrillamail(poll: int = 5) -> None:
    """Run the GuerrillaMail provider listener."""
    GM_API = "https://api.guerrillamail.com/ajax.php"
    GM_UA = "Mozilla/5.0 (TempMailWatcher/2.0 by zebbern)"
    
    sess = make_requests_session()
    sess.headers.update({"User-Agent": GM_UA})
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Setting up GuerrillaMail account..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("setup", total=None)
        
        try:
            # Get address & sid token
            params = {"f": "get_email_address", "ip": "127.0.0.1", "agent": GM_UA}
            res = sess.get(GM_API, params=params, timeout=15)
            res.raise_for_status()
            init = res.json()
            
            sid = init["sid_token"]
            address = init["email_addr"]
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {e}") from e
        except Exception as e:
            raise APIError(f"API error: {e}") from e
    
    console.print(f"[success]✓[/] Email address ready: [bold]{address}[/]")
    console.print(f"Polling every [bold]{poll}s[/] for new messages. Press [bold]Ctrl+C[/] to stop.\n")
    
    seen: Set[str] = set()
    try:
        while True:
            try:
                params = {"f": "check_email", "sid_token": sid, "seq": 0}
                box_res = sess.get(GM_API, params=params, timeout=15)
                box_res.raise_for_status()
                box = box_res.json()
                
                for m in box.get("list", []):
                    if m["mail_id"] in seen:
                        continue
                    
                    seen.add(m["mail_id"])
                    
                    params = {"f": "fetch_email", "sid_token": sid, "email_id": m["mail_id"]}
                    full_res = sess.get(GM_API, params=params, timeout=15)
                    full_res.raise_for_status()
                    full = full_res.json()
                    
                    print_email(
                        "guerrillamail",
                        address,
                        full.get("mail_from"),
                        full.get("mail_subject"),
                        full.get("mail_date"),
                        full.get("mail_body", ""),
                        full,
                    )
            except requests.RequestException as e:
                LOGGER.warning(f"Network error during polling: {e}")
            except Exception as e:
                LOGGER.warning(f"Error during polling: {e}")
            
            time.sleep(poll)
    except KeyboardInterrupt:
        console.print("[info]Stopped listening; goodbye![/]")

##############################################################################
# Provider 2 – mail.tm
##############################################################################

def run_mail_tm(poll: int = 5) -> None:
    """Run the mail.tm provider listener."""
    BASE = "https://api.mail.tm"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Setting up mail.tm account..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("setup", total=None)
        
        try:
            # Get available domains
            domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
            domains_res.raise_for_status()
            domain = domains_res.json()["hydra:member"][0]["domain"]
            
            # Create random account
            address = f"{_rand_string()}@{domain}"
            password = _rand_string(12)
            
            account_res = requests.post(
                f"{BASE}/accounts", 
                json={"address": address, "password": password},
                timeout=15
            )
            account_res.raise_for_status()
            
            # Get authentication token
            token_res = requests.post(
                f"{BASE}/token", 
                json={"address": address, "password": password},
                timeout=15
            )
            token_res.raise_for_status()
            auth = token_res.json()["token"]
            
            headers = {"Authorization": f"Bearer {auth}"}
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {e}") from e
        except Exception as e:
            raise APIError(f"API error: {e}") from e
    
    console.print(f"[success]✓[/] Email address ready: [bold]{address}[/]")
    console.print(f"Polling every [bold]{poll}s[/] for new messages. Press [bold]Ctrl+C[/] to stop.\n")
    
    seen: Set[str] = set()
    try:
        while True:
            try:
                inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
                inbox_res.raise_for_status()
                inbox = inbox_res.json()["hydra:member"]
                
                for m in inbox:
                    if m["id"] in seen:
                        continue
                    
                    seen.add(m["id"])
                    
                    full_res = requests.get(f"{BASE}/messages/{m['id']}", headers=headers, timeout=15)
                    full_res.raise_for_status()
                    full = full_res.json()
                    
                    print_email(
                        "mail.tm",
                        address,
                        full.get("from", {}).get("address"),
                        full.get("subject"),
                        full.get("createdAt"),
                        full.get("text", ""),
                        full,
                    )
            except requests.RequestException as e:
                LOGGER.warning(f"Network error during polling: {e}")
            except Exception as e:
                LOGGER.warning(f"Error during polling: {e}")
            
            time.sleep(poll)
    except KeyboardInterrupt:
        console.print("[info]Stopped listening; goodbye![/]")

##############################################################################
# Provider 3 – tempmail.lol
##############################################################################

def run_tempmail_lol(poll: int = 5, rush: bool = False) -> None:
    """Run the tempmail.lol provider listener."""
    BASE = "https://api.tempmail.lol"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Setting up tempmail.lol account..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("setup", total=None)
        
        try:
            # Get address (optionally use rush endpoint)
            endpoint = f"{BASE}/generate/rush" if rush else f"{BASE}/generate"
            gen_res = requests.get(endpoint, timeout=15)
            gen_res.raise_for_status()
            
            data = gen_res.json()
            address = data["address"]
            token = data["token"]
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {e}") from e
        except Exception as e:
            raise APIError(f"API error: {e}") from e
    
    console.print(f"[success]✓[/] Email address ready: [bold]{address}[/]")
    console.print(f"Polling every [bold]{poll}s[/] for new messages. Press [bold]Ctrl+C[/] to stop.\n")
    
    seen: Set[str] = set()
    try:
        while True:
            try:
                inbox_res = requests.get(f"{BASE}/auth/{token}", timeout=15)
                inbox_res.raise_for_status()
                
                msgs = inbox_res.json().get("email", [])
                
                for m in msgs:
                    # Create a message ID from content to track seen messages
                    msg_id = f"{m.get('from')}_{m.get('subject')}_{len(m.get('body', ''))}"
                    
                    if msg_id in seen:
                        continue
                    
                    seen.add(msg_id)
                    
                    print_email(
                        "tempmail.lol",
                        address,
                        m.get("from"),
                        m.get("subject"),
                        None,  # No date provided by this API
                        m.get("body", ""),
                        m,
                    )
            except requests.RequestException as e:
                LOGGER.warning(f"Network error during polling: {e}")
            except Exception as e:
                LOGGER.warning(f"Error during polling: {e}")
            
            time.sleep(poll)
    except KeyboardInterrupt:
        console.print("[info]Stopped listening; goodbye![/]")

##############################################################################
# Provider 4 – mail.gw (identical API to mail.tm, hosted elsewhere)
##############################################################################

def run_mail_gw(poll: int = 5) -> None:
    """Run the mail.gw provider listener."""
    BASE = "https://api.mail.gw"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Setting up mail.gw account..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("setup", total=None)
        
        try:
            # Get available domains
            domains_res = requests.get(f"{BASE}/domains?page=1", timeout=15)
            domains_res.raise_for_status()
            domain = domains_res.json()["hydra:member"][0]["domain"]
            
            # Create random account
            address = f"{_rand_string()}@{domain}"
            password = _rand_string(12)
            
            account_res = requests.post(
                f"{BASE}/accounts", 
                json={"address": address, "password": password},
                timeout=15
            )
            account_res.raise_for_status()
            
            # Get authentication token
            token_res = requests.post(
                f"{BASE}/token", 
                json={"address": address, "password": password},
                timeout=15
            )
            token_res.raise_for_status()
            auth = token_res.json()["token"]
            
            headers = {"Authorization": f"Bearer {auth}"}
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {e}") from e
        except Exception as e:
            raise APIError(f"API error: {e}") from e
    
    console.print(f"[success]✓[/] Email address ready: [bold]{address}[/]")
    console.print(f"Polling every [bold]{poll}s[/] for new messages. Press [bold]Ctrl+C[/] to stop.\n")
    
    seen: Set[str] = set()
    try:
        while True:
            try:
                inbox_res = requests.get(f"{BASE}/messages", headers=headers, timeout=15)
                inbox_res.raise_for_status()
                inbox = inbox_res.json()["hydra:member"]
                
                for m in inbox:
                    if m["id"] in seen:
                        continue
                    
                    seen.add(m["id"])
                    
                    full_res = requests.get(f"{BASE}/messages/{m['id']}", headers=headers, timeout=15)
                    full_res.raise_for_status()
                    full = full_res.json()
                    
                    print_email(
                        "mail.gw",
                        address,
                        full.get("from", {}).get("address"),
                        full.get("subject"),
                        full.get("createdAt"),
                        full.get("text", ""),
                        full,
                    )
            except requests.RequestException as e:
                LOGGER.warning(f"Network error during polling: {e}")
            except Exception as e:
                LOGGER.warning(f"Error during polling: {e}")
            
            time.sleep(poll)
    except KeyboardInterrupt:
        console.print("[info]Stopped listening; goodbye![/]")

##############################################################################
# Provider 5 – dropmail.me
##############################################################################

def run_dropmail_me(poll: int = 5) -> None:
    """Run the dropmail.me provider listener."""
    BASE = "https://dropmail.me/api/graphql"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Setting up dropmail.me account..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("setup", total=None)
        
        try:
            # Create a new session with a random token
            token = _rand_string(12)
            query = """
            mutation {
              introduceSession {
                id
                expiresAt
                addresses {
                  address
                }
              }
            }
            """
            
            res = requests.post(
                f"{BASE}/{token}",
                json={"query": query},
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            res.raise_for_status()
            
            data = res.json().get("data", {})
            session = data.get("introduceSession", {})
            session_id = session.get("id")
            address = session.get("addresses", [{}])[0].get("address")
            
            if not session_id or not address:
                raise APIError("Failed to get valid session or address")
        except requests.RequestException as e:
            raise NetworkError(f"Network error: {e}") from e
        except Exception as e:
            raise APIError(f"API error: {e}") from e
    
    console.print(f"[success]✓[/] Email address ready: [bold]{address}[/]")
    console.print(f"Polling every [bold]{poll}s[/] for new messages. Press [bold]Ctrl+C[/] to stop.\n")
    
    seen: Set[str] = set()
    try:
        query = """
        query($id: ID!){
          session(id: $id){
            mails{
              id
              fromAddr
              headerSubject
              text
              receivedAt
            }
          }
        }
        """
        
        while True:
            try:
                res = requests.post(
                    f"{BASE}/{token}",
                    json={"query": query, "variables": {"id": session_id}},
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                res.raise_for_status()
                
                data = res.json().get("data", {})
                session_data = data.get("session", {})
                
                if not session_data:
                    LOGGER.warning("Session expired or not found")
                    break
                
                mails = session_data.get("mails", [])
                
                for m in mails:
                    if m["id"] in seen:
                        continue
                    
                    seen.add(m["id"])
                    
                    print_email(
                        "dropmail.me",
                        address,
                        m.get("fromAddr"),
                        m.get("headerSubject"),
                        m.get("receivedAt"),
                        m.get("text", ""),
                        m,
                    )
            except requests.RequestException as e:
                LOGGER.warning(f"Network error during polling: {e}")
            except Exception as e:
                LOGGER.warning(f"Error during polling: {e}")
            
            time.sleep(poll)
    except KeyboardInterrupt:
        console.print("[info]Stopped listening; goodbye![/]")

##############################################################################
# CLI - argument parsing, interactive menu, dispatcher
##############################################################################

PROVIDERS: Dict[str, Callable[[int], None]] = {
    "guerrillamail": run_guerrillamail,
    "mail.tm": run_mail_tm,
    "tempmail.lol": run_tempmail_lol,
    "mail.gw": run_mail_gw,
    "dropmail.me": run_dropmail_me,
}

def print_ascii_banner() -> None:
    """Print the ASCII art banner."""
    # Clear the screen before printing banner
    clear_screen()
    
    banner = r"""
 _____                   __  __       _ _    __        __    _       _               
|_   _|__ _ __ ___  _ __|  \/  | __ _(_) |   \ \      / /_ _| |_ ___| |__   ___ _ __ 
  | |/ _ \ '_ ` _ \| '_ \ |\/| |/ _` | | |____\ \ /\ / / _` | __/ __| '_ \ / _ \ '__|
  | |  __/ | | | | | |_) | |  | | (_| | | |_____\ V  V / (_| | || (__| | | |  __/ |   
  |_|\___|_| |_| |_| .__/|_|  |_|\__,_|_|_|      \_/\_/ \__,_|\__\___|_| |_|\___|_|   
                   |_|                                                               
    """
    console.print(banner, style="bold cyan")
    console.print("Developed by [link=https://github.com/zebbern]zebbern[/link]", style="cyan")
    console.print("─" * 80 + "\n")

def interactive_menu() -> Tuple[str, int]:
    """Display an interactive menu for provider selection."""
    print_ascii_banner()
    
    config = load_config()
    default_provider = config.get("default_provider", "mail.tm")
    default_poll = config.get("poll_interval", 5)
    
    # Display provider options
    console.print("[header]Choose a temporary email provider:[/]")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan bold")
    table.add_column()
    
    for idx, name in enumerate(PROVIDERS, 1):
        default_marker = " [yellow](default)[/]" if name == default_provider else ""
        table.add_row(f"{idx})", f"{name}{default_marker}")
    
    console.print(table)
    
    # Get provider selection
    providers_list = list(PROVIDERS.keys())
    default_index = providers_list.index(default_provider) if default_provider in providers_list else 0
    
    while True:
        choice = console.input(f"[bold]Provider[/] [1-{len(PROVIDERS)}] [{default_index + 1}]: ")
        choice = choice.strip() or str(default_index + 1)
        
        if choice.isdigit() and 1 <= int(choice) <= len(PROVIDERS):
            provider = providers_list[int(choice) - 1]
            break
        console.print("[warning]Invalid selection. Please enter a number between " 
                      f"1 and {len(PROVIDERS)}.[/]")
    
    # Get polling interval
    while True:
        poll_str = console.input(f"[bold]Polling interval[/] (seconds) [{default_poll}]: ")
        poll_str = poll_str.strip() or str(default_poll)
        
        if poll_str.isdigit() and int(poll_str) > 0:
            poll = int(poll_str)
            break
        console.print("[warning]Invalid polling interval. Please enter a positive number.[/]")
    
    # Save selections as defaults for next time
    config["default_provider"] = provider
    config["poll_interval"] = poll
    save_config(config)
    
    return provider, poll

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    config = load_config()
    
    parser = argparse.ArgumentParser(
        description="Temp Mail Watcher - A professional CLI for temporary email inboxes."
    )
    parser.add_argument(
        "provider",
        nargs="?",
        choices=list(PROVIDERS.keys()),
        help="Temp-mail provider to use. If omitted, an interactive menu is shown.",
    )
    parser.add_argument(
        "--poll", "-p",
        type=int,
        default=config.get("poll_interval", 5),
        help=f"Polling interval in seconds (default: {config.get('poll_interval', 5)}).",
    )
    parser.add_argument(
        "--rush", "-r",
        action="store_true",
        help="Use rush mode for tempmail.lol (faster address generation).",
    )
    parser.add_argument(
        "--display", "-d",
        choices=["rich", "plain"],
        default=config.get("display_mode", "rich"),
        help="Display mode (default: rich).",
    )
    parser.add_argument(
        "--no-save", "-n",
        action="store_true",
        help="Don't save received messages to history.",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Temp Mail Watcher v2.0 by zebbern (https://github.com/zebbern)",
    )
    
    args = parser.parse_args(argv)
    
    # Update config with CLI options
    config["poll_interval"] = args.poll
    config["display_mode"] = args.display
    config["save_messages"] = not args.no_save
    save_config(config)
    
    return args

def main() -> None:
    """Main entry point for the application."""
    try:
        # Clear the screen
        clear_screen()
        
        # Parse arguments
        args = parse_args()
        
        # If no provider specified, show interactive menu
        if not args.provider:
            provider_name, poll_interval = interactive_menu()
        else:
            provider_name = args.provider
            poll_interval = args.poll
        
        # Print banner for non-interactive mode
        if args.provider:
            print_ascii_banner()
        
        # Run the selected provider
        if provider_name == "tempmail.lol" and args.rush:
            run_tempmail_lol(poll=poll_interval, rush=True)
        else:
            PROVIDERS[provider_name](poll=poll_interval)
    except NetworkError as e:
        LOGGER.error(f"Network error: {e}")
        console.print("[error]Failed to connect to the service. Please check your internet connection.[/]")
        sys.exit(1)
    except APIError as e:
        LOGGER.error(f"API error: {e}")
        console.print("[error]The service API returned an error. The service might be down or has changed.[/]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[info]Stopped by user. Goodbye![/]")
        sys.exit(0)
    except Exception as e:
        LOGGER.error(f"Unexpected error: {e}")
        console.print(f"[error]An unexpected error occurred: {e}[/]")
        if os.environ.get("DEBUG"):
            console.print_exception()
        sys.exit(1)

##############################################################################
# Additional features
##############################################################################

def view_history() -> None:
    """View email history from saved messages."""
    if not HISTORY_FILE.exists():
        console.print("[warning]No message history found.[/]")
        return
    
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        if not history:
            console.print("[warning]Message history is empty.[/]")
            return
        
        console.print(f"[header]Message History[/] ({len(history)} entries)")
        
        for idx, entry in enumerate(history, 1):
            provider = entry.get("provider", "unknown")
            address = entry.get("address", "unknown")
            timestamp = entry.get("timestamp", "unknown")
            message = entry.get("message", {})
            
            panel = Panel(
                f"Provider: [bold]{provider}[/]\n"
                f"Address: [bold]{address}[/]\n"
                f"Time: [bold]{_format_timestamp(timestamp)}[/]\n"
                f"From: [email_from]{message.get('from', '(unknown)')}[/]\n"
                f"Subject: [email_subject]{message.get('subject', '(no subject)')}[/]\n\n"
                f"{message.get('body', '(no body)').strip()[:500]}",
                title=f"Message #{idx}",
                title_align="left",
                border_style="cyan"
            )
            console.print(panel)
            
            if idx < len(history):
                continue_viewing = console.input(
                    f"[bold]Press Enter to view next message or 'q' to quit[/] [{idx}/{len(history)}]: "
                )
                if continue_viewing.lower() == 'q':
                    break
    except Exception as e:
        console.print(f"[error]Error viewing history: {e}[/]")

def export_emails(output_file: str = "email_export.json") -> None:
    """Export emails to a JSON file."""
    if not HISTORY_FILE.exists():
        console.print("[warning]No message history to export.[/]")
        return
    
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        with open(output_file, "w") as f:
            json.dump(history, f, indent=2)
        
        console.print(f"[success]Successfully exported {len(history)} messages to {output_file}[/]")
    except Exception as e:
        console.print(f"[error]Error exporting emails: {e}[/]")

def clear_history() -> None:
    """Clear email history."""
    if not HISTORY_FILE.exists():
        console.print("[warning]No message history to clear.[/]")
        return
    
    confirm = console.input("[bold red]This will permanently delete all saved messages. Continue? (y/N): [/]")
    if confirm.lower() != 'y':
        console.print("[info]Operation cancelled.[/]")
        return
    
    try:
        os.remove(HISTORY_FILE)
        console.print("[success]Message history cleared successfully.[/]")
    except Exception as e:
        console.print(f"[error]Error clearing history: {e}[/]")

##############################################################################
# Entry point
##############################################################################

if __name__ == "__main__":
    main()