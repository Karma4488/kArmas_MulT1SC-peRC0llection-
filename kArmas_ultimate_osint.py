import asyncio
import aiohttp
import json
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import random
import time
import re

# Username sites (from previous version)
USERNAME_SITES = {
    "GitHub": {
        "url": "https://github.com/{}",
        "not_found_indicators": ["Not Found", "404"],
    },
    "Twitter/X": {
        "url": "https://x.com/{}",
        "not_found_indicators": ["This account doesn’t exist", "Something went wrong"],
    },
    "Reddit": {
        "url": "https://www.reddit.com/user/{}",
        "not_found_indicators": ["page not found", "sorry, nobody on Reddit goes by that name"],
    },
    "Instagram": {
        "url": "https://www.instagram.com/{}/",
        "not_found_indicators": ["Sorry, this page isn't available", "The link you followed may be broken"],
    },
    "LinkedIn": {
        "url": "https://www.linkedin.com/in/{}",
        "not_found_indicators": ["Page not found", "profile not found"],
    },
    "YouTube": {
        "url": "https://www.youtube.com/@{}",
        "not_found_indicators": ["404 Not Found", "This channel does not exist"],
    },
}

# Email registration check sites (inspired by Holehe - small sample; expand for 100+)
EMAIL_SITES = {
    "Twitter/X": {
        "url": "https://x.com/account/begin_password_reset",
        "method": "POST",
        "data": {"account_identifier": "{email}"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "exists_indicators": ["We'll send you an email"],  # If exists, offers reset
        "not_exists_indicators": ["We couldn't find your account"],
    },
    "Instagram": {
        "url": "https://www.instagram.com/accounts/password/reset/",
        "method": "POST",
        "data": {"enc_password": "", "email_or_username": "{email}"},  # Simplified
        "exists_indicators": ["we'll send you an email"],
        "not_exists_indicators": ["Can't find this account"],
    },
    "Spotify": {
        "url": "https://www.spotify.com/api/account/v1/password-reset/initiate",
        "method": "POST",
        "json": {"email": "{email}"},
        "exists_indicators": ["true"],  # Response often boolean
        "not_exists_indicators": ["false"],
    },
    # Add more from Holehe modules for full power (GitHub, Reddit, etc.)
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}

async def check_username_site(session, target, site_name, site_info):
    # (Same as previous version)
    url = site_info["url"].format(target)
    indicators = site_info.get("not_found_indicators", [])

    try:
        async with session.get(url, timeout=15, headers=HEADERS) as response:
            status = response.status
            if status == 404:
                exists = False
            elif status != 200:
                exists = False
            else:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                page_text = soup.get_text(lower=True)
                exists = not any(ind.lower() in page_text for ind in indicators if ind)
                if not indicators:
                    exists = True

            return {
                "site": site_name,
                "url": url,
                "exists": exists,
                "status_code": status,
            }
    except Exception as e:
        return {"site": site_name, "url": url, "exists": False, "error": str(e)}

async def check_email_registration(session, email, site_name, site_info):
    url = site_info["url"]
    method = site_info.get("method", "GET")
    exists_inds = site_info.get("exists_indicators", [])
    not_exists_inds = site_info.get("not_exists_indicators", [])

    payload = None
    if "{email}" in str(site_info.get("data", "")) or "{email}" in str(site_info.get("json", "")):
        if "data" in site_info:
            payload = {k: v.format(email=email) for k, v in site_info["data"].items()}
        elif "json" in site_info:
            payload = {k: v.format(email=email) for k, v in site_info["json"].items()}

    try:
        if method == "POST":
            if "json" in site_info:
                async with session.post(url, json=payload, timeout=15, headers={**HEADERS, **site_info.get("headers", {})}) as resp:
                    text = await resp.text()
                    status = resp.status
            else:
                async with session.post(url, data=payload, timeout=15, headers={**HEADERS, **site_info.get("headers", {})}) as resp:
                    text = await resp.text()
                    status = resp.status
        else:
            async with session.get(url, timeout=15, headers=HEADERS) as resp:
                text = await resp.text()
                status = resp.status

        soup = BeautifulSoup(text, 'html.parser')
        page_text = soup.get_text(lower=True)
        json_resp = None
        try:
            json_resp = await resp.json()
        except:
            pass

        exists = False
        if json_resp:
            exists = any(ind.lower() in str(json_resp).lower() for ind in exists_inds)
            exists = exists or not any(ind.lower() in str(json_resp).lower() for ind in not_exists_inds)
        else:
            exists = any(ind.lower() in page_text for ind in exists_inds)
            exists = exists or not any(ind.lower() in page_text for ind in not_exists_inds)

        return {
            "site": site_name,
            "exists": exists,
            "status_code": status,
            "response_snippet": text[:200] if not json_resp else json_resp,
        }
    except Exception as e:
        return {"site": site_name, "exists": False, "error": str(e)}

async def email_reputation(session, email):
    url = f"https://emailrep.io/{email}"
    try:
        async with session.get(url, timeout=15, headers=HEADERS) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "reputation": data.get("reputation"),
                    "suspicious": data.get("suspicious"),
                    "references": data.get("references"),
                    "known_profiles": data.get("details", {}).get("profiles", []),
                    "blacklisted": data.get("details", {}).get("blacklisted"),
                    "data_breach": data.get("details", {}).get("data_breach"),
                    "credentials_leaked": data.get("details", {}).get("credentials_leaked"),
                    "summary": data.get("summary", ""),
                }
            else:
                return {"error": f"Status {resp.status}"}
    except Exception as e:
        return {"error": str(e)}

async def main(target, proxies=None, max_concurrent=30):
    is_email = re.match(r"^[^@]+@[^@]+\.[^@]+$", target)

    results = {"target": target, "type": "email" if is_email else "username"}

    connector = aiohttp.TCPConnector(limit=max_concurrent)
    timeout = aiohttp.ClientTimeout(total=40)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=HEADERS) as session:
        if proxies:
            session.proxy = random.choice(proxies)

        tasks = []

        if not is_email:
            # Username checks
            for site_name, site_info in USERNAME_SITES.items():
                tasks.append(check_username_site(session, target, site_name, site_info))
        else:
            # Email registration checks
            email_tasks = []
            for site_name, site_info in EMAIL_SITES.items():
                email_tasks.append(check_email_registration(session, target, site_name, site_info))
            email_results = await asyncio.gather(*email_tasks)

            # Email reputation
            rep_task = email_reputation(session, target)

            rep_result = await rep_task

            results["email_registration"] = [r for r in email_results if r["exists"]]
            results["email_not_registered"] = [r for r in email_results if not r["exists"]]
            results["email_reputation"] = rep_result

        if not is_email:
            username_results = await asyncio.gather(*tasks)
            found = [r for r in username_results if r.get("exists", False)]
            not_found = [r for r in username_results if not r.get("exists", False)]
            results["username_profiles_found"] = sorted(found, key=lambda x: x["site"])
            results["username_profiles_not_found"] = sorted(not_found, key=lambda x: x["site"])

    print(json.dumps(results, indent=4))

    filename = f"{target.replace('@', '_at_')}_osint_report.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nFull report saved to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ultimate Async Username & Email OSINT Tool")
    parser.add_argument("target", help="Username or Email to investigate")
    parser.add_argument("--proxies", nargs="*", help="List of proxies (e.g. http://127.0.0.1:8080)")
    args = parser.parse_args()

    asyncio.run(main(args.target, proxies=args.proxies))
