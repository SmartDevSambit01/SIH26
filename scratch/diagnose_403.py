"""
Diagnostic script to analyze 403 authentication failure.
Traces the HTTP redirect chain from CMR download URL through GES DISC / URS.
Never prints token values.
"""
import os
import requests
from urllib.parse import urlparse

token = os.environ.get("EARTHDATA_TOKEN")
user = os.environ.get("EARTHDATA_USERNAME")

print(f"EARTHDATA_TOKEN present: {bool(token)}, length: {len(token) if token else 0}")
print(f"EARTHDATA_USERNAME present: {bool(user)}")

# --- Step 1: CMR granule search (no auth required) ---
cmr = requests.get(
    "https://cmr.earthdata.nasa.gov/search/granules.json",
    params={
        "short_name": "GPM_3IMERGHHE",
        "version": "07",
        "bounding_box": "92.0,23.0,95.0,26.5",
        "sort_key": "-start_date",
        "page_size": 1,
    },
    timeout=15
)
print(f"\nCMR query status: {cmr.status_code}")

entries = cmr.json().get("feed", {}).get("entry", [])
if not entries:
    print("ERROR: No granules returned from CMR")
    exit(1)

entry = entries[0]
dl_url = None
for l in entry.get("links", []):
    if l.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#" and not l.get("inherited"):
        dl_url = l.get("href")
        break

print(f"Granule title: {entry.get('title')}")
parsed = urlparse(dl_url) if dl_url else None
print(f"Download URL host: {parsed.netloc if parsed else 'N/A'}")
print(f"Download URL scheme: {parsed.scheme if parsed else 'N/A'}")
print(f"Download URL path start: {parsed.path[:80] if parsed else 'N/A'}...")

if not token:
    print("\nNO TOKEN AVAILABLE - cannot proceed with download test")
    exit(0)

if not dl_url:
    print("\nERROR: No download URL from CMR")
    exit(1)

# --- Step 2: Test redirect chain manually, one hop at a time ---
print("\n--- Testing HTTP redirect chain (no auto-follow) ---")

session = requests.Session()
session.headers["Authorization"] = f"Bearer {token}"

url = dl_url
max_hops = 6
for hop in range(max_hops):
    r = session.head(url, allow_redirects=False, timeout=15)
    print(f"\nHop {hop}: {urlparse(url).netloc}{urlparse(url).path[:60]}...")
    print(f"  Status: {r.status_code}")
    auth_sent = "Authorization" in r.request.headers
    print(f"  Auth header sent: {auth_sent}")

    if r.status_code in (301, 302, 303, 307, 308):
        next_loc = r.headers.get("Location", "")
        print(f"  Redirect to: {urlparse(next_loc).netloc}{urlparse(next_loc).path[:60]}...")
        url = next_loc
        # NASA URS redirects strip the Auth header - we need to re-add it
        if "urs.earthdata.nasa.gov" in url or "earthdata.nasa.gov" in url:
            print(f"  [NOTE] Redirected to URS auth endpoint - this may strip Bearer header")
    elif r.status_code == 200:
        print(f"  Final destination - 200 OK")
        break
    elif r.status_code in (401, 403):
        print(f"  AUTH FAILURE at hop {hop}: {r.status_code}")
        print(f"  WWW-Authenticate header: {r.headers.get('WWW-Authenticate', 'none')}")
        break
    else:
        print(f"  Unexpected status at hop {hop}: {r.status_code}")
        break

# --- Step 3: Test with allow_redirects=True to see final outcome ---
print("\n--- Following all redirects automatically ---")
session2 = requests.Session()
session2.headers["Authorization"] = f"Bearer {token}"

def on_redirect(response, *args, **kwargs):
    """Hook to inspect redirect and re-attach auth header."""
    if response.is_redirect:
        next_url = response.headers.get("Location", "")
        print(f"  Redirect: {response.status_code} -> {urlparse(next_url).netloc}{urlparse(next_url).path[:60]}")

session2.hooks["response"] = [on_redirect]

r_final = session2.head(dl_url, allow_redirects=True, timeout=20)
print(f"Final status: {r_final.status_code}")
print(f"Final URL host: {urlparse(r_final.url).netloc}")
print(f"Content-Type: {r_final.headers.get('Content-Type', 'N/A')}")
print(f"Content-Length: {r_final.headers.get('Content-Length', 'N/A')}")
