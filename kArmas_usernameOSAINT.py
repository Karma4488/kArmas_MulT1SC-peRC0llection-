#!/usr/bin/env python3
"""
kArmas_usernameOSINT
Advanced OSINT username reconnaissance with Tor proxy support.
Zero auth. HTTP + content forensics. Ghost mode via Tor.
Made in l0v3 by kArmasec
"""

import sys
import time
import requests
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Matrix theme ANSI
GREEN   = "\u001B[32m"
BLUE    = "\u001B[34m"
CYAN    = "\u001B[36m"
BOLD    = "\u001B[1m"
DIM     = "\u001B[2m"
RESET   = "\u001B[0m"

def vprint(verbose, *args, **kwargs):
    if verbose:
        print(*args, **kwargs)

def get_session(use_tor=False, tor_port=9050, verbose=False):
    session = requests.Session()
    retry_strategy = Retry(total=2, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (kArmas_usernameOSINT v2)'
    }
    session.headers.update(headers)

    if use_tor:
        proxy_url = f"socks5h://127.0.0.1:{tor_port}"
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        vprint(verbose, f"{GREEN}{DIM}Tor proxy activated → socks5h://127.0.0.1:{tor_port}{RESET}")

    return session

def check_profile_exists(url, session, verbose=False):
    not_found_indicators = [
        "not found", "doesn't exist", "page isn't available", "sorry, this page",
        "this content isn't available", "user not found", "profile not found",
        "account doesn't exist", "oops", "error", "unavailable", "404", "gone",
        "no results", "invalid username", "this channel does not exist",
        "unless you’ve got a time machine", "sorry. unless", "page not found"
    ]

    try:
        head_resp = session.head(url, allow_redirects=True, timeout=12)
        final_url = head_resp.url.rstrip('/')

        vprint(verbose, f"{DIM}HEAD → {head_resp.status_code} | Final: {final_url}{RESET}")

        if head_resp.status_code != 200:
            vprint(verbose, f"{DIM}Rejected: Non-200{RESET}")
            return False

        get_resp = session.get(final_url, timeout=15, allow_redirects=True)
        final_url_get = get_resp.url.rstrip('/')
        text_lower = get_resp.text.lower()
        text_snippet = get_resp.text[:200].replace('\n', ' ').strip()

        vprint(verbose, f"{DIM}GET → {get_resp.status_code} | Len: {len(get_resp.text)} | Snippet: {text_snippet}...{RESET}")

        orig_clean = url.rstrip('/')
        if final_url_get != orig_clean and any(x in final_url_get.lower() for x in ['login', 'search', 'error', 'notfound', 'signup']):
            vprint(verbose, f"{DIM}Rejected: Redirect trap → {final_url_get}{RESET}")
            return False

        found_fp = next((ind for ind in not_found_indicators if ind in text_lower), None)
        if found_fp:
            vprint(verbose, f"{DIM}Rejected: FP '{found_fp}' detected{RESET}")
            return False

        if len(get_resp.text) < 500 and "profile" not in text_lower:
            vprint(verbose, f"{DIM}Rejected: Stub page (<500 chars, no profile){RESET}")
            return False

        vprint(verbose, f"{DIM}PASSED → Valid profile{RESET}")
        return True

    except Exception as e:
        vprint(verbose, f"{DIM}Error: {str(e)}{RESET}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="kArmas_usernameOSINT - Elite username recon with optional Tor anonymity",
        epilog="Made in l0v3 by kArmasec | We are Legion"
    )
    parser.add_argument("username", help="Target username")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("-t", "--tor", action="store_true", help="Route all requests through Tor SOCKS5 (127.0.0.1:9050)")
    parser.add_argument("--tor-port", type=int, default=9050, help="Tor SOCKS port (default 9050, Orbot often 9150)")

    args = parser.parse_args()
    username = args.username.strip()
    verbose = args.verbose
    use_tor = args.tor
    tor_port = args.tor_port

    # Banner
    print(f"{GREEN}{BOLD}")
    print("   __ __              _                        ")
    print("  / // /__ _  ___ ___(_)__ _  _____ _______    ")
    print(" / _  / _ `/ (_-</ _ / / _ \\ / __/(_-<(_-<    ")
    print("/_//_/\\_,_/ /___/\\___/_/ .__/_/  /___/___/    ")
    print("                       /_/                     ")
    print(f"{RESET}")

    print(f"{BLUE}{BOLD}      Anonymous. We are Legion.{RESET}")
    print(f"{CYAN}      kArmas_usernameOSINT v2 | made in l0v3 by kArmasec{RESET}")
    if verbose:
        print(f"{GREEN}{BOLD}VERBOSE MODE ACTIVE{RESET}")
    if use_tor:
        print(f"{GREEN}{BOLD}TOR MODE ACTIVE (port {tor_port}) - Ghost protocol engaged{RESET}")
    print("")

    print(f"{GREEN}{DIM}>>> 01001011 01000001 01010010 01001101 01000001 01010011  <<<{RESET}\n")

    print(f"{BLUE}{DIM}Target:{RESET} {BOLD}{GREEN}{username}{RESET}\n")

    session = get_session(use_tor=use_tor, tor_port=tor_port, verbose=verbose)

    sites = {
        'Twitter/X':    f"https://x.com/{username}",
        'Instagram':    f"https://www.instagram.com/{username}/",
        'GitHub':       f"https://github.com/{username}",
        'TikTok':       f"https://www.tiktok.com/@{username}",
        'Reddit':       f"https://www.reddit.com/user/{username}/",
        'YouTube':      f"https://www.youtube.com/@{username}",
        'Facebook':     f"https://www.facebook.com/{username}",
        'LinkedIn':     f"https://www.linkedin.com/in/{username}",
        'Pinterest':    f"https://www.pinterest.com/{username}/",
        'Snapchat':     f"https://www.snapchat.com/add/{username}",
        'Twitch':       f"https://www.twitch.tv/{username}",
        'Threads':      f"https://www.threads.net/@{username}",
        'Bluesky':      f"https://bsky.app/profile/{username}.bsky.social",
    }

    for site, url in sites.items():
        vprint(verbose, f"{DIM}--- {site} ---{RESET}")
        exists = check_profile_exists(url, session, verbose=verbose)

        if exists:
            print(f"{GREEN}{BOLD}[FOUND]{RESET} {GREEN}{site:<12}{RESET}: {CYAN}{url}{RESET}")
        else:
            print(f"{BLUE}{BOLD}[MISS]{RESET}  {BLUE}{site:<12}{RESET}: {DIM}{url}{RESET}")

        time.sleep(0.8 if use_tor or verbose else 0.3)  # Slower on Tor to avoid circuit overload

    print(f"\n{GREEN}{DIM}Operation complete. White rabbit followed.{RESET}")
