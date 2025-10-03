#!/usr/bin/env python3

##################
# IMPORT MODULES #
##################

import importlib
import subprocess
import sys

# Import Python module dynamically. If not installed, attempt to install via pip.
def import_python_module(module_name, package_name=None, from_import=None):
    """
    Dynamically import a module; if missing, attempt to install the package via pip.
    On failure, provide clearer instructions rather than silently exiting.
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        pkg = package_name or module_name.split(".")[0]
        print(f"⚠️  Module '{module_name}' not found. Attempting to install '{pkg}' via pip...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except subprocess.CalledProcessError as exc:
            print(f"❌ Failed to install '{pkg}' automatically: {exc}")
            print("Please install the dependency manually and re-run (recommended inside a virtualenv):")
            print(f"  python -m venv .venv && ./.venv/bin/pip install {pkg}  # macOS/Linux")
            print(f"  py -3 -m venv .venv && .\\.venv\\Scripts\\pip install {pkg}  # Windows (PowerShell/CMD)")
            sys.exit(1)
        
        # try import again
        module = importlib.import_module(module_name)

    if from_import:
        try:
            return getattr(module, from_import)
        except AttributeError:
            print(f"❌ '{from_import}' not found in '{module_name}'.")
            sys.exit(1)

    return module


# Standard library
os = import_python_module("os")
time = import_python_module("time")
argparse = import_python_module("argparse")
ET = import_python_module("xml.etree.ElementTree")
re = import_python_module("re")
unicodedata = import_python_module("unicodedata")
quote_plus = import_python_module("urllib.parse", from_import="quote_plus")

# Third-party
PlexServer = import_python_module("plexapi.server", package_name="plexapi", from_import="PlexServer")
requests = import_python_module("requests")
load_dotenv = import_python_module("dotenv", package_name="python-dotenv", from_import="load_dotenv")

# Load environment variables
load_dotenv()



#############
# VARIABLES #
#############

# Configure your media root structure here
# The script will look for directories inside these (e.g. ".../tv/ShowName" or ".../movies/MovieName")
ROOT_MOVIES_SERIES_DIR = ["tv", "movies"]

# Plex server details (must be in environment or .env file)
PLEX_URL = os.environ.get("PLEX_URL")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN")

if not PLEX_URL or not PLEX_TOKEN:
    print("\nERROR: PLEX_URL and PLEX_TOKEN must be set in a .env file or environment variables.")
    print("Create a .env with:")
    print("  PLEX_URL=http://your-plex:32400")
    print("  PLEX_TOKEN=xxxxxxxxxxxxxxxx")
    sys.exit(1)

# Remove trailing slash from Plex URL (for consistency)
PLEX_URL = PLEX_URL.rstrip("/")

# Connect to Plex
try:
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    print(f"✅ Connected to Plex at {PLEX_URL}\n")
except Exception as e:
    print(f"❌ Failed to connect to Plex at {PLEX_URL}: {e}\n")
    sys.exit(1)

# Parse arguments
parser = argparse.ArgumentParser(description="Plex NFO Manager (Movies/Series)")
parser.add_argument("--dry-run", action="store_true", help="Don't perform edits/uploads; just print intended actions")
args = parser.parse_args()
DRY_RUN = args.dry_run

# Delay after uploading posters
POST_UPLOAD_WAIT = 0.4



#############
# FUNCTIONS #
#############

# Enable auto complete TAB
def enable_tab_completion():
    """
    Try to enable tab completion for input paths.
    On Windows, prefer 'pyreadline3' (if installed). Fall back gracefully.
    """
    try:
        if sys.platform.startswith("win"):
            # Try pyreadline3 first, then pyreadline if available
            try:
                import pyreadline as readline  # may be pyreadline3 exposing pyreadline
            except Exception:
                import pyreadline3 as readline  # pyreadline3 package
        else:
            import readline
    except Exception:
        # Not critical — skip tab completion if imports fail
        return

    # If we reached here, a readline-like API is available
    import readline

    def complete_path(text, state):
        text_expanded = os.path.expanduser(text)
        dirname, rest = os.path.split(text_expanded)
        if dirname == "":
            dirname = "."
        try:
            entries = os.listdir(dirname)
        except Exception:
            entries = []
        matches = []
        for e in entries:
            if e.lower().startswith(rest.lower()):
                full = os.path.join(dirname, e)
                if os.path.isdir(full):
                    matches.append(os.path.join(dirname, e) + os.sep)
                else:
                    matches.append(os.path.join(dirname, e))
        try:
            return matches[state]
        except IndexError:
            return None

    try:
        readline.set_completer_delims(' \t\n;')
        readline.set_completer(complete_path)
        # Different platforms use different binding names; try a couple
        try:
            readline.parse_and_bind("tab: complete")
        except Exception:
            try:
                readline.parse_and_bind("bind ^I rl_complete")
            except Exception:
                pass
    except Exception:
        pass

enable_tab_completion()


# Prompt the user with choices
def prompt_choice(prompt, choices):
    print(prompt)

    for i, c in enumerate(choices, start=1):
        print(f"  {i}. {c}")
    
    while True:
        s = input("Choose number (or 'q' to quit): ").strip()
        
        if s.lower() == "q":
            print("Quitting.")
            sys.exit(0)
        
        if s.isdigit():
            idx = int(s) - 1
            if 0 <= idx < len(choices):
                return idx
        
        print("Invalid choice, try again.")


# Return absolute, normalized path without trailing slashes
def normalize_path(p):
    if not p:
        return p

    # Expand user and make absolute
    p = os.path.expanduser(p)
    p = os.path.abspath(p)
    p = os.path.normpath(p)

    # Remove trailing separator except for root paths like "/" or "C:\"
    if len(p) > len(os.path.abspath(os.sep)) and p.endswith(os.sep):
        p = p.rstrip(os.sep)

    # Normalize case on case-insensitive file systems for stable comparisons
    try:
        p = os.path.normcase(p)
    except Exception:
        pass

    return p


# Recursively scan for all .nfo files inside `scan_path`
def find_all_nfo_files(scan_path):
    nfos = []
    
    for root, _, files in os.walk(scan_path):
        for f in files:
            if os.path.splitext(f)[1].lower() == ".nfo":
                nfos.append(os.path.join(root, f))
    
    return sorted(nfos)


# Return top-level media directory
#   Example: /mnt/media/tv/Show/Season 01/episode1.nfo --> /mnt/media/tv/Show
# Relies on ROOT_MOVIES_SERIES_DIR to detect 'tv' or 'movies' segments.
def get_top_level_media_dirs(nfo_files):
    top_dirs = set()
    root_dirs_lower = [r.lower() for r in ROOT_MOVIES_SERIES_DIR]

    for nfo in nfo_files:
        # Normalize and split using os.path.sep safely
        norm = os.path.normpath(nfo)
        parts = norm.split(os.path.sep)

        # On Windows, parts[0] may be like 'C:' — include it when building the top path
        for idx, part in enumerate(parts):
            if part.lower() in root_dirs_lower:
                # We want everything up to the show name (ROOT + show)
                end_idx = idx + 2  # e.g., [..., 'tv', 'Show']
                # slice parts up to end_idx (handles drive letters automatically)
                top_path = os.path.join(*parts[:end_idx])
                top_path = os.path.normpath(top_path)
                top_dirs.add(top_path)
                break

    return sorted(top_dirs)


# Reduce nested directories, keeping only the highest-level candidate directories
#   Example: Keep /mnt/tv/Show instead of both /mnt/tv/Show and /mnt/tv/Show/Season 01
def reduce_dirs_to_top_level(dirs):
    dirs_sorted = sorted(set(dirs), key=lambda x: len(x))
    
    kept = []
    
    for d in dirs_sorted:
        if not any(os.path.commonpath([d, k]) == k for k in kept):
            kept.append(d)
    
    return kept


# Normalize text by removing diacritics (accents)
def strip_diacritics(text):
    nf = unicodedata.normalize("NFD", text)
    filtered = "".join(ch for ch in nf if not unicodedata.combining(ch))
    
    return unicodedata.normalize("NFC", filtered)


# Remove year patterns
def clean_title_suffix(title):
    return re.sub(r"\s*[\-\(\[\{]\s*\d{4}[\)\]\}]?$", "", title).strip()


# If Plex search returns an episode, map it back to its parent show; otherwise return original item
def map_episode_to_show_if_needed(item):
    try:
        item_type = getattr(item, "type", None) or item.__class__.__name__.lower()
    except Exception:
        item_type = None

    if item_type and "episode" in str(item_type).lower():
        try:
            return item.show()
        except Exception:
            # Fallback if item.show() fails → try fetching by grandparent key
            gkey = getattr(item, "grandparentRatingKey", None) or getattr(item, "grandparentKey", None)
            
            if gkey:
                try:
                    return plex.fetchItem(gkey)
                except Exception:
                    return None
            
            return None
    else:
        return item


# Filter Plex search results to only include those that contain *all words* of the query.
# This avoids irrelevant matches (e.g., "The Big Bang Theory" when searching "The League").
def filter_results_by_title(query, results):
    query_norm = strip_diacritics(query).lower()
    query_words = [w for w in re.findall(r"[a-zA-Z0-9']+", query_norm)]
    filtered = []
    
    for r in results:
        title = getattr(r, "title", "")
        title_norm = strip_diacritics(title).lower()
        
        if all(w in title_norm for w in query_words):
            filtered.append(r)
    
    return filtered


# Search Plex with multiple fallback strategies
def search_plex_for_title(title, search_filter="all"):
    
    # Internal helper to perform search and filter by type
    def do_search(q):
        try:
            raw = plex.search(q)
        except Exception:
            raw = []
        
        by_key = {}
        
        for r in raw:
            mapped = map_episode_to_show_if_needed(r) or r
            
            if not mapped:
                continue
            
            t = getattr(mapped, "type", "").lower()
            
            if search_filter == "tv" and "show" not in t:
                continue
            
            if search_filter == "movies" and "movie" not in t:
                continue
            
            key = getattr(mapped, "ratingKey", None)
            
            if key and key not in by_key:
                by_key[key] = mapped
        
        return list(by_key.values())

    # 1. Try raw
    results = do_search(title)
    results = filter_results_by_title(title, results)
    if results:
        return results

    # 2. Try normalized (strip diacritics)
    title_norm = strip_diacritics(title)
    if title_norm != title:
        print(f"  ⚠️  Normalized title: '{title_norm}'")
        
        results = do_search(title_norm)
        results = filter_results_by_title(title_norm, results)
        if results:
            return results

    # 3. Fallback regex 1
    m1 = re.match(r"^[\w\-\' ]+", title_norm)
    if m1:
        fallback1 = clean_title_suffix(m1.group(0).strip())
        
        if fallback1 and fallback1 != title_norm:
            print(f"  ⚠️  Fallback 1: '{fallback1}'")
            
            results = do_search(fallback1)
            results = filter_results_by_title(fallback1, results)
            if results:
                return results

    # 4. Fallback regex 2
    m2 = re.match(r"^[a-zA-Z\-\' ]+", title_norm)
    if m2:
        fallback2 = clean_title_suffix(m2.group(0).strip())
        if fallback2 and fallback2 not in (title_norm, locals().get("fallback1", "")):
            print(f"  ⚠️  Fallback 2: '{fallback2}'")
            
            results = do_search(fallback2)
            results = filter_results_by_title(fallback2, results)
            if results:
                return results

    return []


# Choose/select a plex item
def choose_plex_item(candidates, hint):
    if not candidates:
        return None
    
    if len(candidates) == 1:
        print(f"One Plex candidate found for '{hint}': {getattr(candidates[0],'title',str(candidates[0]))}")
        return candidates[0]
    
    display = []
    for c in candidates:
        title = getattr(c, "title", str(c))
        typ = getattr(c, "type", getattr(c, "TYPE", "")) or c.__class__.__name__
        lib = getattr(c, "librarySectionTitle", "")
        display.append(f"{title}  [{typ}]  (library: {lib})")
    
    idx = prompt_choice(f"Multiple Plex matches found for '{hint}'. Choose:", display)
    return candidates[idx]


# Safe edit and poster helpers (respect DRY_RUN by printing only)
def safe_edit_item(item, new_title, new_summary):
    if DRY_RUN:
        print(f"    [DRY-RUN] Would edit item '{getattr(item,'title', '')}': title -> '{new_title}', summary length -> {len(new_summary)}")
        return True, "dry-run"
    
    try:
        # Ensure we have a full object (avoid partial-object issues)
        try:
            # ratingKey is the unique id used by the server
            rk = getattr(item, "ratingKey", None)
            if rk:
                item = plex.fetchItem(rk)  # get full item from server
            else:
                item.reload()
        except Exception:
            # fallback to reload if fetchItem fails
            try:
                item.reload()
            except Exception:
                pass

        # Use batchEdits to perform both edits together
        item.batchEdits()
        
        # Pass locked=True to lock field after edit (or locked=False if you prefer unlocked)
        item.editTitle(new_title, locked=True)
        item.editSummary(new_summary, locked=True)
        item.saveEdits()

        # reload/refresh and verify
        try:
            item.reload()
        except Exception:
            pass

        # Verify the change actually occurred
        cur_title = getattr(item, "title", None)
        cur_summary = getattr(item, "summary", None) or ""
        if (cur_title and cur_title.strip() == (new_title or "").strip()) and \
           ((new_summary or "").strip() in (cur_summary or "").strip()):
            print(f"    Edited item (ratingKey={getattr(item,'ratingKey', 'unknown')}): title -> '{cur_title}'")
            return True, "edited"
        else:
            return False, f"Verification failed: server shows title='{cur_title}', summary_len={len(cur_summary)}"

    except Exception as e:
        return False, f"Edit exception: {e}"


# PlexAPI fallback (upload_poster_and_refresh): Use post or server-side URL to upload
def http_upload_poster_fallback(rating_key, image_path):
    # Multipart POST fallback to /library/metadata/{ratingKey}/posters.
    upload_url = f"{PLEX_URL}/library/metadata/{rating_key}/posters"
    headers = {"X-Plex-Token": PLEX_TOKEN, "Accept": "*/*", "User-Agent": "PlexNFOUpdater/1.0"}
    
    try:
        with open(image_path, "rb") as fh:
            files = {"file": (os.path.basename(image_path), fh, "image/jpeg")}
            resp = requests.post(upload_url, headers=headers, files=files, timeout=30)
        if 200 <= resp.status_code < 300:
            return True, f"Multipart OK ({resp.status_code})"
    except Exception as e:
        # fallthrough
        pass
    
    # url-style fallback (server must access path)
    try:
        url_with_param = upload_url + "?url=" + quote_plus(image_path) + "&X-Plex-Token=" + quote_plus(PLEX_TOKEN)
        resp = requests.post(url_with_param, headers=headers, timeout=30)
        
        if 200 <= resp.status_code < 300:
            return True, f"URL upload OK ({resp.status_code})"
        
        return False, f"URL upload status {resp.status_code}"
    except Exception as e:
        return False, f"HTTP upload exception: {e}"


# UsePlex API first (prefered) and fallback to HTTP
def upload_poster_and_refresh(item, image_path):
    """
    Upload poster (plexapi first, then HTTP fallback). Trigger single refresh().
    In DRY_RUN: skip upload/refresh, just print intended actions.
    """
    rk = getattr(item, "ratingKey", None)
    if not rk:
        return False, "No ratingKey"

    if DRY_RUN:
        print(f"    [DRY-RUN] Would upload poster for ratingKey {rk} from '{image_path}' and call refresh().")
        return True, "dry-run"

    # Try plexapi uploadPoster (filepath=... or path)
    try:
        try:
            item.uploadPoster(filepath=image_path)
        except TypeError:
            # older signature
            item.uploadPoster(image_path)
        except Exception:
            # other exception propagate to fallback
            raise
        
        time.sleep(POST_UPLOAD_WAIT)
        
        try:
            item.refresh()
        except Exception:
            try:
                item.reload()
            except Exception:
                pass
        
        print(f"    uploadPoster invoked for ratingKey {rk}; refresh requested.")
        
        return True, "plexapi"
    except Exception as e:
        # fallback to HTTP multipart
        ok, msg = http_upload_poster_fallback(rk, image_path)
        if ok:
            try:
                item.refresh()
            except Exception:
                try:
                    item.reload()
                except Exception:
                    pass
            print(f"    HTTP fallback upload succeeded for ratingKey {rk}: {msg}; refresh requested.")
            return True, "http-fallback"
        else:
            return False, f"Poster upload failed: {msg}"


#-------------
# SERIES/SHOWS
#-------------
# Iterate seasons/episodes, find local metadata files and apply NFO edits and upload poster images
def process_show_directory(show_item, dir_path):
    print(f"\n=== Processing SHOW '{getattr(show_item,'title',dir_path)}' ===")
    
    # count seasons/episodes for user
    try:
        seasons = list(show_item.seasons())
        tot_seasons = len(seasons)
        tot_eps = sum(len(s.episodes()) for s in seasons)
    except Exception:
        tot_seasons = tot_eps = 0
    
    print(f"  Show has ~{tot_seasons} seasons and ~{tot_eps} episodes (Plex estimate).")
    print(f"  Scanning local directory for metadata: {dir_path}")

    # Build mapping of basename -> {nfo,image}
    metadata_files = {}
    for root, _, files in os.walk(dir_path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            
            if ext in (".nfo", ".jpg", ".jpeg", ".png"):
                base = os.path.splitext(fname)[0].lower()
                metadata_files.setdefault(base, {})
                metadata_files[base][('nfo' if ext == ".nfo" else 'image')] = os.path.join(root, fname)

    print(f"  Found {len(metadata_files)} metadata file groups locally (by base filename).")

    failures = []
    updated_count = 0
    poster_count = 0

    for season in show_item.seasons():
        for episode in season.episodes():
            show_name = getattr(show_item,'title')
            
            ep_title = getattr(episode, "title", f"S{season.index}E{episode.index}")
            print(f"\n  Processing Episode: '{ep_title}' (S{season.index}E{episode.index})")
            
            try:
                file_path = episode.media[0].parts[0].file
            except Exception:
                print("    Could not determine media file path for this episode; skipping.")
                failures.append((f"{show_name} --> {ep_title}", "no media"))
                continue
            
            base_file = os.path.splitext(os.path.basename(file_path))[0].lower()
            print(f"    Local file base: {base_file}")

            # Try to match by base filename
            matched_key = None
            for k in metadata_files:
                if k in base_file or base_file in k:
                    matched_key = k
                    break

            if not matched_key:
                print("    No local NFO/image matched for this episode; skipping.")
                continue

            md = metadata_files[matched_key]
            print(f"    Matched metadata base: '{matched_key}' -> {md.keys()}")

            # NFO
            if "nfo" in md:
                nfo_path = md["nfo"]
                print(f"    Found NFO: {nfo_path}")
                
                try:
                    tree = ET.parse(nfo_path)
                    root = tree.getroot()
                    
                    new_title = (root.findtext("title") or episode.title or "").strip()
                    new_summary = (root.findtext("plot") or getattr(episode, "summary", "") or "").strip()
                    print(f"    Will set title: '{new_title}' (len summary: {len(new_summary)})")
                    
                    ok, msg = safe_edit_item(episode, new_title, new_summary)
                    if not ok:
                        print(f"    Edit failed: {msg}")
                        failures.append((nfo_path, f"Edit failed: {msg}"))
                    else:
                        updated_count += 1
                except Exception as e:
                    print(f"    NFO parse error: {e}")
                    failures.append((nfo_path, f"NFO parse error: {e}"))
            else:
                print("    No NFO found for this match.")

            # Image / poster
            if "image" in md:
                image_path = md["image"]
                print(f"    Found image candidate: {image_path}")
                
                if not os.path.exists(image_path):
                    print("    Image file missing on disk.")
                    failures.append((f"{show_name} --> {ep_title}", "image missing"))
                else:
                    ok, msg = upload_poster_and_refresh(episode, image_path)
                    if ok:
                        poster_count += 1
                    else:
                        print(f"    Poster upload failed: {msg}")
                        failures.append((image_path, f"Poster upload failed: {msg}"))
            else:
                print("    No image candidate found for this match.")

    print(f"\n  Show processing complete. Episodes updated: {updated_count}, posters attempted: {poster_count}")
    return failures


#-------
# MOVIES
#-------
def process_movie_directory(movie_item, dir_path):
    print(f"\n=== Processing MOVIE '{getattr(movie_item,'title',dir_path)}' ===")
    print(f"  Scanning directory for NFO/poster: {dir_path}")

    nfo_candidate = None
    image_candidate = None
    
    for root, _, files in os.walk(dir_path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            full = os.path.join(root, fname)
            
            if not nfo_candidate and ext == ".nfo":
                nfo_candidate = full
            
            if not image_candidate and ext in (".jpg", ".jpeg", ".png"):
                image_candidate = full
        
        if nfo_candidate and image_candidate:
            break

    failures = []
    
    if nfo_candidate:
        print(f"  Found NFO: {nfo_candidate}")
        try:
            tree = ET.parse(nfo_candidate)
            root = tree.getroot()
            new_title = (root.findtext("title") or movie_item.title or "").strip()
            new_summary = (root.findtext("plot") or getattr(movie_item, "summary", "") or "").strip()
            print(f"  Will set movie title: '{new_title}' (summary len={len(new_summary)})")
            ok, msg = safe_edit_item(movie_item, new_title, new_summary)
            if not ok:
                print(f"  Edit failed: {msg}")
                failures.append(("movie_edit", msg))
        except Exception as e:
            print(f"  NFO parse error: {e}")
            failures.append(("movie_nfo_parse", str(e)))
    else:
        print("  No NFO found for movie.")

    if image_candidate:
        print(f"  Found poster image: {image_candidate}")
        if not os.path.exists(image_candidate):
            print("  Image file missing.")
            failures.append(("movie_poster", "image missing"))
        else:
            ok, msg = upload_poster_and_refresh(movie_item, image_candidate)
            if not ok:
                print(f"  Poster upload failed: {msg}")
                failures.append(("movie_poster", msg))
    else:
        print("  No image found for movie.")
    
    return failures



###############
# MAIN SCRIPT #
###############

def main():
    print("=== Plex NFO Manager (Movies/Series) ===")
    print("Dry-run mode:", "ON (no changes)" if DRY_RUN else "OFF (changes will be applied)")

    # Ask for search type
    sf_idx = prompt_choice("Limit search to:", ["All (shows + movies)", "TV shows only", "Movies only"])
    search_filter = "all" if sf_idx == 0 else ("tv" if sf_idx == 1 else "movies")

    # Ask for path (tab completion enabled)
    raw_path = input("Enter path (directory) to operate on (TAB for autocompletion): ").strip()
    if not raw_path:
        print("No path provided - exiting.")
        return
    
    base_path = normalize_path(raw_path)
    
    if not os.path.exists(base_path):
        print("Provided path does not exist:", base_path)
        return

    candidate_name = os.path.basename(base_path)
    print(f"Detected candidate name from path: '{candidate_name}'")

    action_idx = prompt_choice("Choose how to proceed with this path:", [
        f"Use detected name: '{candidate_name}' (search Plex for this show/movie)",
        "Provide the proper show/movie name manually",
        "Nothing specific — scan everything under the provided path"
    ])

    processed = []
    failures = []
    skipped = []

    if action_idx in (0, 1):
        if action_idx == 1:
            name_to_lookup = input("Enter the show/movie name as it appears in Plex: ").strip()
            
            if not name_to_lookup:
                print("No name entered; exiting.")
                return
        else:
            name_to_lookup = candidate_name

        print(f"Searching Plex for '{name_to_lookup}' (filter={search_filter}) ...")
        
        candidates = search_plex_for_title(name_to_lookup, search_filter=search_filter)
        print(f"Found {len(candidates)} Plex candidate(s).")
        
        if not candidates:
            print("No candidates found in Plex for that name.")
            return

        chosen = choose_plex_item(candidates, name_to_lookup)
        if not chosen:
            print("No selection made; exiting.")
            return

        # Determine if show or movie
        is_show = hasattr(chosen, "seasons") or getattr(chosen, "type", "").lower() == "show"
        if is_show:
            fails = process_show_directory(chosen, base_path)
            for f in fails:
                failures.append(f)
            processed.append((chosen, base_path, "show"))
        else:
            fails = process_movie_directory(chosen, base_path)
            for f in fails:
                failures.append(f)
            processed.append((chosen, base_path, "movie"))

    else:
        # Scan everything mode
        print(f"\nScanning recursively for .nfo files under: {base_path}")
        
        nfos = find_all_nfo_files(base_path)
        if not nfos:
            print("No .nfo files found under the provided path.")
            return
        
        # Reduce to top-level media directories (e.g., /tv/ShowName, not /tv/ShowName/Season 01)
        candidate_dirs = get_top_level_media_dirs(nfos)
        candidate_dirs = reduce_dirs_to_top_level(candidate_dirs)

        print("\nCandidates to process:")

        for d in candidate_dirs:
            print(" -", d)

        for d in candidate_dirs:
            name_hint = os.path.basename(d)
            print(f"\nCandidate directory: {d}  (name hint: '{name_hint}')")
            
            candidates = search_plex_for_title(name_hint, search_filter=search_filter)
            print(f"  Plex candidates found: {len(candidates)}")
            
            if not candidates:
                print(f"  No Plex match for '{name_hint}' — will report at summary.")
                failures.append(("nomatch", d, name_hint))
                continue
            
            chosen = choose_plex_item(candidates, name_hint)
            if not chosen:
                print("  No selection; skipping.")
                failures.append(("nochoice", d, name_hint))
                continue
            
            if hasattr(chosen, "seasons") or getattr(chosen, "type", "").lower() == "show":
                fails = process_show_directory(chosen, d)
                
                for f in fails:
                    failures.append(f)
                processed.append((chosen, d, "show"))
            else:
                fails = process_movie_directory(chosen, d)
                
                for f in fails:
                    failures.append(f)
                processed.append((chosen, d, "movie"))

    # Summary
    print("\n\n=== SUMMARY ===")
    print(f"Dry-run: {DRY_RUN}")
    print(f"Processed items: {len(processed)}")
    
    for it, p, typ in processed:
        print(f" - {getattr(it,'title',str(it))} ({typ}) from {p}")
    
    if failures:
        print("\nFailures / items needing attention:")
        for f in failures:
            print(" -", f)
    else:
        print("No failures reported.")
    
    print("\nDone.")


if __name__ == "__main__":
    main()
