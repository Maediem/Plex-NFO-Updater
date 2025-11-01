#!/usr/bin/env python3

##################
# IMPORT MODULES #
##################

import importlib
import subprocess
import sys

def import_python_module(module_name, package_name=None, from_import=None):
    # ===============================================================================
    # Dynamically import a module; if missing, attempt to install the package via pip
    # On failure, provide clearer instructions rather than silently exiting
    # ===============================================================================
    try:
        module = importlib.import_module(module_name)

    except ImportError:
        pkg = package_name or module_name.split(".")[0]
        print(f"WARNING: Module '{module_name}' not found. Attempting to install '{pkg}' via pip...")

        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

        except subprocess.CalledProcessError as exc:
            print(f"ERROR: Failed to install '{pkg}' automatically: {exc}")
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
            print(f"ERROR: '{from_import}' not found in '{module_name}'.")
            sys.exit(1)

    return module


# Standard library (loaded via helper for consistency with your pattern)
os = import_python_module("os")
time = import_python_module("time")
argparse = import_python_module("argparse")
ET = import_python_module("xml.etree.ElementTree")
re = import_python_module("re")
unicodedata = import_python_module("unicodedata")
quote_plus = import_python_module("urllib.parse", from_import="quote_plus")
datetime = import_python_module("datetime")

# Third-party
PlexServer = import_python_module("plexapi.server", package_name="plexapi", from_import="PlexServer")
load_dotenv = import_python_module("dotenv", package_name="python-dotenv", from_import="load_dotenv")

# Load environment variables
load_dotenv()



#############
# VARIABLES #
#############

# ==== CONFIGURATIONS ====
SCRIPT_NAME = "Plex NFO Updater" # Used in some prints/logs
LOG_FILE = f"{SCRIPT_NAME.lower().replace(' ', '_')}-{datetime.date.today():%Y-%m-%d}.log" # Log file path

CUSTOM_DELAY = 0.4 # Used to wait after an edit/upload

PLEX_URL = None     # If you don't want to use .env file, change this value to: http://your-plex:32400
PLEX_TOKEN = None   # If you don't want to use .env file, change this value to your Plex Token

# The script will look for directories inside these (e.g. ".../tv/<show name>" or ".../movies/<movie name>")
ROOT_PLEX_SHOW_DIR = ["tv", "serie", "series", "show", "shows", "tvshow", "tvshows"]
ROOT_PLEX_MOVIE_DIR = ["movie", "movies"]
ALLOW_ART_EXT = ("mp3", "m4a", "jpg", "jpeg", "png", "tbn") # This will be used to search additional files after NFO files (IMPORTANT: Need to have same name as NFO file)
# ========================

# ----------------------------
# Parse command-line arguments
# ----------------------------
parser = argparse.ArgumentParser(description=f"{SCRIPT_NAME} (Movies/Series)")

parser.add_argument("--dry-run",            action="store_true",        dest="dry_run",             default=None,   help="Don't perform edits/uploads; just print intended actions")
parser.add_argument("--debug-mode",         action="store_true",        dest="debug_mode",          default=False,  help="Enable debug-level console output")
parser.add_argument("--scan-path",                                      dest="scan_path",type=str,  default=None,   help="Path to scan (non-interactive mode)")
parser.add_argument("--logging",            action="store_true",        dest="logging",             default=True,   help="Enable/disable logging to file (default: ON)")
parser.add_argument("--no-logging",         action="store_false",       dest="logging",                             help="Disable logging to file")
parser.add_argument("--allow-unlock",       action="store_true",        dest="allow_unlock",        default=True,   help="Allow unlocking locked fields before editing")
parser.add_argument("--no-unlock",          action="store_false",       dest="allow_unlock",                        help="Disallow unlocking locked fields")
parser.add_argument("--update-art",         action="store_true",        dest="update_art",          default=True,   help="Enable artwork updates (default: ON)")
parser.add_argument("--no-art",             action="store_false",       dest="update_art",                          help="Disable artwork updates")
parser.add_argument("--always-update-art",  action="store_true",        dest="always_update_art",   default=False,  help="Force artwork updates even if metadata hasn't changed (except in dry-run)")

args = parser.parse_args()

# ----------------------------------
# Assign parsed arguments to globals
# ----------------------------------
LOGGING = args.logging
SCRIPT_NAME = SCRIPT_NAME
ALLOW_UNLOCK = args.allow_unlock
ALLOW_ART_UPDATE = args.update_art
ALWAYS_UPDATE_ART = args.always_update_art
DRY_RUN = args.dry_run
DEBUG_MODE = args.debug_mode
SCAN_PATH = args.scan_path

# -------------------
# Debug print summary
# -------------------
if DEBUG_MODE:
    print(f"[DEBUG] {SCRIPT_NAME} configuration:")
    print(f"  LOGGING:            {LOGGING}")
    print(f"  ALLOW_UNLOCK:       {ALLOW_UNLOCK}")
    print(f"  ALLOW_ART_UPDATE:   {ALLOW_ART_UPDATE}")
    print(f"  ALWAYS_UPDATE_ART:  {ALWAYS_UPDATE_ART}")
    print(f"  DRY_RUN:            {DRY_RUN}")
    print(f"  SCAN_PATH:          {SCAN_PATH}")
    print(f"  LOG_FILE:           {LOG_FILE}")



# ------------------------------------------------------------------------------
# Unified mapping of logical NFO fields to Plex API fields for batch editing
# The "plex_item.edit()" method uses these "rest_field" values as keys
# Reference: https://python-plexapi.readthedocs.io/en/latest/modules/mixins.html
# ------------------------------------------------------------------------------
SUPPORTED_FIELD_MAP = {
    # NFO Tag        -> { "rest_field": "plex_api_field_name", "is_tag": True/False }

    # single-valued fields (used with editField)
    "title":         {"rest_field": "title",                 "is_tag": False},
    "originaltitle": {"rest_field": "originalTitle",         "is_tag": False},
    "plot":          {"rest_field": "summary",               "is_tag": False},
    "summary":       {"rest_field": "summary",               "is_tag": False},
    "overview":      {"rest_field": "summary",               "is_tag": False},
    "studio":        {"rest_field": "studio",                "is_tag": False},
    "premiered":     {"rest_field": "originallyAvailableAt", "is_tag": False},
    "year":          {"rest_field": "year",                  "is_tag": False},
    "mpaa":          {"rest_field": "contentRating",         "is_tag": False},
    "contentrating": {"rest_field": "contentRating",         "is_tag": False},
    "rating":        {"rest_field": "rating",                "is_tag": False},

    # tag/collection fields (use plural collection names)
    "genres":        {"rest_field": "genres",                "is_tag": True},
    "genre":         {"rest_field": "genres",                "is_tag": True},  # alias
    "country":       {"rest_field": "countries",             "is_tag": True},
    "countries":     {"rest_field": "countries",             "is_tag": True},
    "directors":     {"rest_field": "directors",             "is_tag": True},
    "director":      {"rest_field": "directors",             "is_tag": True},  # alias
    "writers":       {"rest_field": "writers",               "is_tag": True},
    "writer":        {"rest_field": "writers",               "is_tag": True},  # alias
    "actors":        {"rest_field": "actors",                "is_tag": True},
    "actor":         {"rest_field": "actors",                "is_tag": True},  # alias
}

STATS = {
        "processed_nfo": 0,
        "updated": [],
        "skipped": [],
        "failed": []
    }

# Enable ANSI escape characters in terminal (for Windows)
try:
    os.system("")
except Exception:
    pass

# ANSI colors for terminal output (used only for console)
COLOR = {
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "ORANGE": "\033[38;5;208m",
    "RED": "\033[91m",
    "RESET": "\033[0m",
}

# ------------
# Plex details
# ------------

# If not changed in configurations, get value from .env
if not PLEX_URL:
    PLEX_URL = os.environ.get("PLEX_URL")

if not PLEX_TOKEN:
    PLEX_TOKEN = os.environ.get("PLEX_TOKEN")

if not PLEX_URL or not PLEX_TOKEN:
    print(f"\n{COLOR['RED']}ERROR{COLOR['RESET']}: PLEX_URL and PLEX_TOKEN must be set in a .env file or environment variables.")
    print("Create a .env with:")
    print("  PLEX_URL=http://your-plex:32400")
    print("  PLEX_TOKEN=xxxxxxxxxxxxxxxx")
    sys.exit(1)

# Remove trailing slash from Plex URL (for consistency)
PLEX_URL = PLEX_URL.rstrip("/")

# Connect to Plex
try:
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    print(f"{COLOR['GREEN']}SUCCESS{COLOR['RESET']}: Connected to Plex at {PLEX_URL}\n")

except Exception as e:
    print(f"{COLOR['RED']}ERROR{COLOR['RESET']}: Failed to connect to Plex at {PLEX_URL}: {e}\n")
    sys.exit(1)




#############
# FUNCTIONS #
#############

def enable_tab_completion():
    # ============================================
    # Try to enable tab completion for input paths
    # Windows: Prefer 'pyreadline3' (if installed)
    # ============================================
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

# Enable auto complete TAB
enable_tab_completion()


def log(level, message):
    # =================================
    # Central logging/printing function
    # =================================

    global DEBUG_MODE

    # Always uppercase
    level = (level or "INFO").upper()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plain_msg = f"{now} [{level}] {message}"

    # Skip debug logs entirely if DEBUG_MODE is off
    if level == "DEBUG" and not DEBUG_MODE:
        return

    # Write to file (plain text)
    if LOGGING:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as lf:
                # write each line separately for long/multiline messages
                for line in str(message).splitlines() or [str(message)]:
                    lf.write(f"{now} [{level}] {line}\n")

        except Exception:
            # don't crash logging
            pass

    # Color selection
    color = {
        "DEBUG": COLOR["CYAN"],
        "INFO": COLOR["BLUE"],
        "SUCCESS": COLOR["GREEN"],
        "WARN": COLOR["YELLOW"],
        "WARNING": COLOR["YELLOW"],
        "ERROR": COLOR["RED"]
    }.get(level, COLOR["ORANGE"])

    try:
        print(f"{now} [{color}{level}{COLOR['RESET']}] {message}")
    except Exception:
        # fallback plain print
        print(plain_msg)


def prompt_choice(prompt, choices):
    # ============================
    # Prompt the user with choices
    # ============================

    print(prompt)

    for i, c in enumerate(choices, start=1):
        print(f"  {COLOR['BLUE']}{i}{COLOR['RESET']}. {c}")

    while True:
        s = input("Choose number (or 'q' to quit): ").strip()

        if s.lower() == "q":
            print("Quitting.")
            sys.exit(0)

        if s.isdigit():
            idx = int(s) - 1
            if 0 <= idx < len(choices):
                return idx

        print(f"{COLOR['RED']}Invalid{COLOR['RESET']} choice, try again.")


def normalize_path(p):
    # =========================================================
    # Return absolute, normalized path without trailing slashes
    # =========================================================

    if not p:
        return p

    # Expand user and make absolute
    p = os.path.expanduser(p)
    p = os.path.abspath(p)
    p = os.path.normpath(p)

    # Remove trailing separator except for root paths like "/" or "C:\"
    if len(p) > len(os.path.abspath(os.sep)) and p.endswith(os.path.sep):
        p = p.rstrip(os.path.sep)

    # Normalize case on case-insensitive file systems for stable comparisons
    try:
        p = os.path.normcase(p)

    except Exception:
        pass

    return p


def resolve_plex_item(media_title, media_type, automatic_mode, parent_plex_item=None):
    # ============================================================================================
    # Resolves the correct Plex item (movie, show, season, episode, etc.) for a given media title
    # ============================================================================================

    global STATS

    plex_item = None

    # ----------------------------
    # Perform Plex search by title
    # ----------------------------
    results = search_plex_for_media_by_title(media_title, media_type, parent_plex_item)

    if not results["candidates"]:
        log("WARN", f"No candidate found for '{media_title}'")
        STATS["skipped"].append(f"{media_title}: No candidate found.")
        return None

    # --------------------------------
    # Automatic (non-interactive) mode
    # --------------------------------
    if automatic_mode:
        if results["is_confident"] and results["nb_excellent_match"] == 1:
            # Confident single excellent match → safe auto-select
            plex_item = results["best_match"]
            log("INFO", f"Automatically matched '{media_title}' (confident single match, score={results['best_score']}).")

        elif results["nb_excellent_match"] > 1:
            # Multiple excellent matches → skip for safety
            log("WARN", f"Automatic mode: Multiple excellent matches found for '{media_title}' ({results['nb_excellent_match']} matches ≥99). Skipping.")

        else:
            # No confident match → skip for safety
            log("WARN", f"Automatic mode: No confident match for '{media_title}' (best score={results['best_score']}). Skipping.")

    # -------------------------
    # Manual / interactive mode
    # -------------------------
    else:
        if results["is_confident"] and results["nb_excellent_match"] == 1:
            # Confident single match — auto-accept
            plex_item = results["best_match"]
            log("INFO", f"Automatically matched '{media_title}' (single confident match).")

        elif results["nb_excellent_match"] > 1:
            # Multiple excellent matches: prompt user
            log("WARN", f"Multiple excellent matches found for '{media_title}' ({results['nb_excellent_match']} matches).") # Score >= 99
            plex_item = choose_plex_item(results["candidates"][:results["nb_excellent_match"]], media_title)
            if not plex_item:
                STATS["skipped"].append(f"{media_title}: User did not select any match.")

        elif len(results["nb_excellent_match"]) == 1:
            # Only one total candidate: accept it interactively
            plex_item = results["candidates"][0]
            log("INFO", f"Accepted single candidate for '{media_title}' (manual mode).")

        else:
            # Multiple uncertain matches — prompt user
            log("INFO", f"No confident match for '{media_title}'. Prompting user selection.")
            plex_item = choose_plex_item(results["candidates"], media_title)
            if not plex_item:
                STATS["skipped"].append(f"{media_title}: No confident match and user did not select any match.")

    # ----------
    # Safety net
    # ----------
    if not plex_item:
        log("DEBUG", f"No item assigned for '{media_title}'.")

    return plex_item




def search_plex_for_media_by_title(media_title, media_type=None, parent_plex_item=None):
    # ================================================================================
    # Search Plex for a media item by title (and optionally media type or parent item)
    # ================================================================================

    function_name = "search_plex_for_media_by_title"
    media_title_raw = str(media_title).strip()

    # -------------------------------
    # Handle empty title early
    # -------------------------------
    if not media_title_raw:
        log("WARN", f"{function_name}: Empty media_title provided.")
        return {
            "candidates": [],
            "best_match": None,
            "best_score": 0,
            "is_confident": False,
            "nb_excellent_match": 0
        }

    # ------------------------------------------------------------
    # Extract trailing year if present (e.g. 1999, (1999), - 1999)
    # ------------------------------------------------------------
    year = None
    match = re.search(r'\s*[\-\(\[\{]\s*\d{4}[\)\]\}]?$', media_title_raw)
    if match:
        matched_str = match.group(0)
        year_match = re.search(r'\d+', matched_str)
        year = int(year_match.group(0)) if year_match else None
        media_title_raw = re.sub(re.escape(matched_str) + r'$', '', media_title_raw).strip()


    def _normalize(s):
        # ========================================================
        # Normalization helper (Unicode-aware, accent-insensitive)
        # ========================================================

        if s is None:
            return ""

        s = str(s).strip()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))

        return s.casefold()
        # ========================================================


    norm_search = _normalize(media_title_raw)

    # --------------------------------------------------------------
    # Helper to determine if a candidate belongs to the given parent
    # --------------------------------------------------------------
    def _is_child_of_parent(candidate, parent_obj):
        try:
            if hasattr(parent_obj, 'ratingKey'):
                parent_rk = getattr(parent_obj, 'ratingKey')

                # Compare candidate parent/grandparent keys
                if getattr(candidate, 'parentRatingKey', None) and str(getattr(candidate, 'parentRatingKey')) == str(parent_rk):
                    return True

                if getattr(candidate, 'grandparentRatingKey', None) and str(getattr(candidate, 'grandparentRatingKey')) == str(parent_rk):
                    return True

                # Check for parent key substring inside candidate key path
                cand_key = getattr(candidate, 'key', None)
                if cand_key and str(parent_rk) in str(cand_key):
                    return True

                # Compare normalized parent titles
                if getattr(candidate, 'parentTitle', None) and _normalize(getattr(candidate, 'parentTitle')) == _normalize(getattr(parent_obj, 'title', '')):
                    return True
            else:
                parent_str = str(parent_obj)
                if getattr(candidate, 'parentTitle', None) and _normalize(getattr(candidate, 'parentTitle')) == _normalize(parent_str):
                    return True

                if getattr(candidate, 'grandparentTitle', None) and _normalize(getattr(candidate, 'grandparentTitle')) == _normalize(parent_str):
                    return True

            return False

        except Exception:
            return False

    # ---------------------------------------------------
    # If parent item itself matches the search title/year
    # ---------------------------------------------------
    parent = parent_plex_item or None
    if parent:
        try:
            parent_title = getattr(parent, 'title', None)
            parent_year = getattr(parent, 'year', None)

            if _normalize(parent_title) == norm_search and (year is None or str(parent_year) == str(year)):
                log("DEBUG", f"{function_name}: Parent itself '{parent_title}' matches search query '{media_title_raw}'.")
                return {
                    "candidates": [parent],
                    "best_match": parent,
                    "best_score": 100,
                    "is_confident": True,
                    "nb_excellent_match": 1
                }

        except Exception as exc:
            log("DEBUG", f"{function_name}: Error evaluating parent self-match: {exc}")

    # ---------------------------------
    # Collect candidate items from Plex
    # ---------------------------------
    scoped_candidates = []

    if parent:
        try:
            if media_type == 'season' and hasattr(parent, 'seasons'):
                scoped_candidates.extend(parent.seasons())

            elif media_type == 'episode':
                if hasattr(parent, 'episodes'):
                    scoped_candidates.extend(parent.episodes())

                elif hasattr(parent, 'seasons'):
                    for s in parent.seasons():
                        try:
                            if hasattr(s, 'episodes'):
                                scoped_candidates.extend(list(s.episodes()))
                            else:
                                scoped_candidates.extend(getattr(s, 'children', []) or [])

                        except Exception:
                            continue
        except Exception as exc:
            log("DEBUG", f"{function_name}: Scoped candidate collection failed: {exc}")
            scoped_candidates = []

    if scoped_candidates:
        log("DEBUG", f"Using {len(scoped_candidates)} scoped candidates under parent for '{media_title_raw}'")
        candidates_to_score = scoped_candidates

    else:
        # No parent or scoped data — perform Plex search
        try:
            candidates_to_score = plex.search(media_title_raw)

        except Exception as exc:
            log("ERROR", f"Plex search failed for '{media_title_raw}': {exc}")
            return {
                "candidates": [],
                "best_match": None,
                "best_score": 0,
                "is_confident": False,
                "nb_excellent_match": 0
            }

    # -------------------------------------------------------
    # Score candidates based on title, year, and relationship
    # -------------------------------------------------------
    scored = []
    noise_keywords = ('sample', 'trailer', 'teaser', 'promo', 'deleted scene', 'behind the scenes')

    for idx, cand in enumerate(candidates_to_score):
        try:
            cand_type = getattr(cand, 'type', None)
            if media_type and cand_type and media_type != cand_type:
                continue

            cand_title = getattr(cand, 'title', None) or getattr(cand, 'name', None) or ""
            norm_cand_title = _normalize(cand_title)
            cand_year = getattr(cand, 'year', None)
            cand_year_int = int(cand_year) if cand_year else None

            score = 0

            # Exact title match
            if norm_cand_title == norm_search:
                score = 99

                if year and cand_year_int == year:
                    score = 100

            elif norm_search in norm_cand_title:
                score = 20

                if cand_title.lower().startswith(media_title_raw.lower()):
                    score += 5

            lower_cand_title = cand_title.lower()
            if any(k in lower_cand_title for k in noise_keywords):
                score = max(score - 50, 1)

            if parent and _is_child_of_parent(cand, parent):
                score += 30

            score = max(0, score)
            scored.append((score, idx, cand, norm_cand_title, cand_year_int))

        except Exception as exc:
            log("DEBUG", f"Error scoring candidate {getattr(cand, 'title', str(cand))}: {exc}")
            scored.append((0, idx, cand, _normalize(getattr(cand, 'title', None)), None))

    if not scored:
        log("DEBUG", f"{function_name}('{media_title_raw}') returned no candidates after filtering.")
        return {
            "candidates": [],
            "best_match": None,
            "best_score": 0,
            "is_confident": False,
            "nb_excellent_match": 0
        }

    # ------------------------------
    # Sort and apply selection rules
    # ------------------------------
    scored.sort(key=lambda x: (-x[0], x[1]))  # Sort by descending score, stable order by index

    # Determine best match and excellent matches
    best_score, _, best_match, _, _ = scored[0]

    excellent_matches = [cand for score, _, cand, _, _ in scored if score >= 99]

    nb_excellent_match = len(excellent_matches)

    is_confident_match = best_score >= 99

    if nb_excellent_match > 1:
        log("DEBUG", f"{function_name}: Found {nb_excellent_match} excellent matches (score ≥99) for '{media_title_raw}'.")

    elif is_confident_match:
        log("DEBUG", f"{function_name}: Confident single match found '{getattr(best_match, 'title', best_match)}' with score {best_score}.")

    else:
        log("DEBUG", f"{function_name}: Returning {len(scored)} candidates (no confident match).")

    # ------------------------------------------
    # Return structured dictionary with metadata
    # ------------------------------------------
    return {
        "candidates": [cand for _, _, cand, _, _ in scored],
        "best_match": best_match,
        "best_score": best_score,
        "is_confident": is_confident_match,
        "nb_excellent_match": nb_excellent_match
    }



def choose_plex_item(candidates, media_title):
    # ==============================================================================
    # Prompt the user to choose among multiple Plex search results (interctive mode)
    # ==============================================================================

    if not candidates:
        return None

    # --- Single candidate ---
    if len(candidates) == 1:
        log("INFO", f"One Plex candidate found for '{media_title}': {getattr(candidates[0],'title',str(candidates[0]))}")
        return candidates[0]

    # --- Multiple candidates ---
    display = []
    for c in candidates:
        title = getattr(c, "title", str(c))
        typ = getattr(c, "type", getattr(c, "TYPE", "")) or c.__class__.__name__
        lib = getattr(c, "librarySectionTitle", "")
        display.append(f"{title}  [{typ}]  (library: {lib})")

    # Add "Skip" option at the end
    display.append("Skip (do not select any match)")

    idx = prompt_choice(f"Multiple Plex matches found for '{media_title}'. Choose one:", display)

    # --- Handle skip ---
    if idx == len(display) - 1:
        log("INFO", f"User chose to skip selection for '{media_title}'.")
        return None

    return candidates[idx]



def parse_nfo_to_dict(nfo_path: str) -> dict:
    # =============================================================================
    # Parse an NFO (XML) file into a flattened Python dictionary of tags and values
    # =============================================================================

    data = {}

    if not os.path.exists(nfo_path):
        log("WARN", f"NFO file not found: {nfo_path}")
        return data

    # Parse XML safely
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    def element_to_value(elem):
        # Recursively convert an XML element to dict/list/str
        children = list(elem)

        if not children:
            return elem.text.strip() if elem.text else None

        result = {}
        for child in children:
            tag = child.tag.lower()
            value = element_to_value(child)

            # Handle multiple same tags (e.g., multiple <actor>)
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]

                result[tag].append(value)
            else:
                result[tag] = value

        return result

    # Flatten one level - make all root children peers in dict
    for child in root:
        tag = child.tag.lower()
        value = element_to_value(child)

        # Handle multiple entries of the same tag
        if tag in data:
            if not isinstance(data[tag], list):
                data[tag] = [data[tag]]
            data[tag].append(value)
        else:
            data[tag] = value

    # Include the root tag (like <tvshow> or <episodedetails>)
    data["root_tag"] = root.tag.lower()

    # Ensure title exists
    data.setdefault("title", "")

    return data


def get_media_type_from_nfo(nfo_data: dict) -> str:
    # ==================================================================================
    # Return media type ('movie', 'show', 'season', 'episode') based on the NFO root tag
    # ==================================================================================

    tag_map = {
        "movie": ["movie", "moviedetail", "moviedetails"],
        "show": ["show", "showdetail", "showdetails", "tvshow", "serie", "tvserie"],
        "season": ["season", "seasondetail", "seasondetails"],
        "episode": ["episode", "episodedetail", "episodedetails"],
    }

    root_tag = nfo_data.get("root_tag", "").lower()

    for media_type, aliases in tag_map.items():
        if root_tag in aliases:
            return media_type

    return ""



def update_plex_item_fields(plex_item, nfo_data, nfo_file=None):
    # =======================================================================
    # Update a Plex item's metadata (show, season, or episode) using NFO data
    # =======================================================================

    global SUPPORTED_FIELD_MAP, ALLOW_UNLOCK, DRY_RUN, CUSTOM_DELAY, STATS, log, time, re, ALWAYS_UPDATE_ART

    item_title = getattr(plex_item, "title", "Unknown Item")
    item_type = getattr(plex_item, "type", "Unknown Type")
    log("DEBUG", f"Starting metadata analysis for '{item_title}' ({item_type})")

    # Flag to indicate whether edits were successfully applied (used to decide artwork uploads)
    edits_applied = False

    try:
        planned_ops = []  # List of field/tag updates to apply

        # -----------------------------------------
        # Determine which fields/tags need updating
        # -----------------------------------------
        for nfo_key, nfo_value in nfo_data.items():
            if nfo_key not in SUPPORTED_FIELD_MAP:
                log("DEBUG", f"{item_title}: Unsupported NFO field '{nfo_key}', skipping.")
                continue

            if nfo_value is None or (isinstance(nfo_value, (str, list, dict)) and not nfo_value):
                continue

            field_info = SUPPORTED_FIELD_MAP[nfo_key]
            rest_field = field_info["rest_field"]
            is_tag = field_info["is_tag"]

            # TAG FIELD HANDLING (genres, directors, actors, etc.)
            if is_tag:
                tag_names = []

                def add_tag(name):
                    # =============================================
                    # Add a cleaned tag name if valid and non-empty
                    # =============================================
                    if not name:
                        return
                    clean = str(name).strip()
                    if clean:
                        tag_names.append(clean)
                    # =============================================

                # Regex used to slpit tag field like genre
                split_re = r'[,/|;]+'

                if isinstance(nfo_value, str):
                    parts = re.split(split_re, nfo_value)

                    for part in parts:
                        add_tag(part)

                elif isinstance(nfo_value, dict):
                    name = nfo_value.get("tag") or nfo_value.get("name")
                    add_tag(name)

                elif isinstance(nfo_value, list):
                    for item in nfo_value:
                        if isinstance(item, str):
                            parts = re.split(split_re, item)

                            for part in parts:
                                add_tag(part)

                        elif isinstance(item, dict):
                            name = item.get("tag") or item.get("name")
                            add_tag(name)

                # Remove duplicates while preserving order
                seen = set()
                unique_tags = []

                for tag in tag_names:
                    clean = tag.strip()

                    if not clean:
                        continue

                    lowered = clean.lower()

                    if lowered not in seen:
                        seen.add(lowered)
                        unique_tags.append(clean)

                if not unique_tags:
                    continue

                # Retrieve current Plex tags for comparison
                plex_attr = getattr(plex_item, rest_field, []) or []

                existing_tags = []
                for t in plex_attr:
                    if isinstance(t, str):
                        candidate = t.strip()

                        if candidate:
                            existing_tags.append(candidate)

                    else:
                        tagname = getattr(t, "tag", None) or getattr(t, "name", None) or None

                        if tagname:
                            candidate = str(tagname).strip()

                            if candidate:
                                existing_tags.append(candidate)

                # Deduplicate existing_tags while preserving order
                seen_tmp = set()
                clean_existing = []

                for t in existing_tags:
                    tl = t.lower()

                    if tl not in seen_tmp:
                        seen_tmp.add(tl)
                        clean_existing.append(t)

                existing_tags = clean_existing
                existing_lower = {t.lower() for t in existing_tags}
                # ------------------------------------------------------------

                # Remove combined tags like "Action / Adventure" if they still contain separators
                refined_tags = []
                combined_seps = ["/", ",", "|", ";"]

                for tag in unique_tags:
                    if any(sep in tag for sep in combined_seps):
                        log("DEBUG", f"{item_title}: Skipping combined tag '{tag}'.")
                        continue

                    refined_tags.append(tag)

                if not refined_tags:
                    continue

                planned_ops.append({
                    "type": "tag",
                    "rest_field": rest_field,  # plural collection name (e.g. "genres")
                    "new": refined_tags,
                    "existing": existing_tags,
                })

            # SINGLE-VALUED FIELD HANDLING (title, studio, summary, etc.)
            else:
                # Normalize both new and current values before any comparison
                new_value = str(nfo_value).strip()

                # Use a default empty string here so we can compare; missing attributes are handled later in a validation pass using a sentinel
                current_raw = getattr(plex_item, rest_field, "") or ""
                current_value = str(current_raw).strip()

                # If values are identical after normalization, skip
                if new_value == current_value:
                    log("DEBUG", f"{item_title}: Skipping unchanged field '{rest_field}'.")
                    continue

                # Check if the field is locked (do this AFTER deciding there's a difference)
                try:
                    locked = plex_item.isLocked(rest_field)
                except Exception:
                    locked = False

                # Skip locked fields if unlocking not allowed
                if locked and not ALLOW_UNLOCK:
                    log("DEBUG", f"{item_title}: Field '{rest_field}' locked (ALLOW_UNLOCK=False), skipping.")
                    continue

                planned_ops.append({
                    "type": "field",
                    "rest_field": rest_field,
                    "value": new_value,
                    "old_value": current_value
                })


        # ========================================================================================================================================
        # VALIDATION PASS: Remove operations that the plex_item does not support
        # Sentinel can tell the difference between does not exists (returns the sentinel), is empty/None/false or has a value (returns that value)
        # ========================================================================================================================================
        sentinel = object()
        validated_ops = []

        for op in planned_ops:
            rest = op["rest_field"]

            if op["type"] == "field":
                # For single-valued fields check the direct attribute presence
                # If the attribute isn't present (getattr returns sentinel), skip the op
                present = getattr(plex_item, rest, sentinel)

                if present is sentinel:
                    log("DEBUG", f"{item_title}: Field '{rest}' not present on item type '{item_type}', skipping planned op.")
                    STATS.setdefault("skipped_missing_field", []).append(f"{item_title}: Missing field '{rest}'")
                    continue

                validated_ops.append(op)

            else:  # tag operation
                # rest is already the plural collection name for tags (e.g. "genres")
                plex_tag_attr = getattr(plex_item, rest, sentinel)

                if plex_tag_attr is sentinel:
                    # Fallback: some bindings are inconsistent — try singular as a last resort
                    plex_tag_attr2 = getattr(plex_item, rest.rstrip('s'), sentinel)

                    if plex_tag_attr2 is sentinel:
                        log("DEBUG", f"{item_title}: Tag collection '{rest}' not present on item type '{item_type}', skipping planned op.")
                        STATS.setdefault("skipped_missing_field", []).append(f"{item_title}: Missing tag collection '{rest}'")
                        continue

                validated_ops.append(op)

        # Replace planned_ops with validated_ops for the rest of the function
        planned_ops = validated_ops
        # ============================================================


        # -----------------------------------
        # Skip items with no detected changes (after validation)
        # -----------------------------------
        if not planned_ops:
            log("INFO", f"'{item_title}': No metadata changes required. Will not update artwork.")
            STATS["skipped"].append(f"{item_title}: No metadata changes required.")

            if ALWAYS_UPDATE_ART:
                log("DEBUG", f"{item_title}: ALWAYS_UPDATE_ART=True, updating artwork despite no metadata changes.")
                update_plex_item_artwork(plex_item, nfo_file)

            return


        # -----------------------------------------
        # DRY RUN MODE (just log the planned edits)
        # -----------------------------------------
        if DRY_RUN:
            log("INFO", f"[DRY RUN] Planned edits for '{item_title}':")

            for op in planned_ops:
                if op["type"] == "field":
                    log("INFO", f"  Field → {op['rest_field']} = '{op['value']}' (was: '{op.get('old_value','')}')")
                else:
                    log("INFO", f"  Tags → {op['rest_field']} (new: {op['new']}, existing: {op['existing']})")

            STATS["skipped"].append(f"{item_title}: Dry-run is activated.")

            update_plex_item_artwork(plex_item, nfo_file)
            return


        # ---------------------------------------
        # Apply updates using Plex batch edit API
        # ---------------------------------------
        log("DEBUG", f"{item_title}: Preparing batch edits...")

        # Debug: show brief planned_ops summary before starting edits
        log("DEBUG", f"{item_title}: Planned operations summary: {len(planned_ops)} ops.")

        for op in planned_ops:
            if op["type"] == "field":
                log("DEBUG", f"  Field: {op['rest_field']}: '{op.get('old_value','')}' -> '{op['value']}'")
            else:
                log("DEBUG", f"  Tag: {op['rest_field']} -> add {len(op['new'])}, existing {len(op['existing'])}")

        plex_item.batchEdits()

        # Safe batching size to avoid Plex API URL limits
        MAX_TAG_BATCH = 5

        for op in planned_ops:
            if op["type"] == "field":
                # Apply field update
                plex_item.editField(
                    field=op["rest_field"],
                    value=op["value"],
                    locked=ALLOW_UNLOCK,
                )

                log("DEBUG", f"{item_title}: Queued field '{op['rest_field']}' = '{op['value']}'")

            else:
                # Apply tag updates
                rest_field = op["rest_field"]  # plural collection name
                refined_tags = op["new"]
                existing_tags = op.get("existing", [])
                existing_lower = {t.lower() for t in existing_tags}

                if ALLOW_UNLOCK:
                    # Remove all existing tags in small batches (if any)
                    if existing_tags:
                        for i in range(0, len(existing_tags), MAX_TAG_BATCH):
                            plex_item.editTags(
                                tag=rest_field,
                                items=existing_tags[i:i+MAX_TAG_BATCH],
                                remove=True,
                                locked=True,
                            )

                    # Add new tags in safe chunks
                    for i in range(0, len(refined_tags), MAX_TAG_BATCH):
                        plex_item.editTags(
                            tag=rest_field,
                            items=refined_tags[i:i+MAX_TAG_BATCH],
                            remove=False,
                            locked=True,
                        )

                    log("DEBUG", f"{item_title}: Replaced all '{rest_field}' tags ({len(refined_tags)} total).")

                else:
                    # Append mode (no removal of existing tags)
                    tags_to_add = [t for t in refined_tags if t.lower() not in existing_lower]

                    if tags_to_add:
                        for i in range(0, len(tags_to_add), MAX_TAG_BATCH):
                            plex_item.editTags(
                                tag=rest_field,
                                items=tags_to_add[i:i+MAX_TAG_BATCH],
                                remove=False,
                                locked=True,
                            )

                        log("DEBUG", f"{item_title}: Added {len(tags_to_add)} new '{rest_field}' tags.")
                    else:
                        log("DEBUG", f"{item_title}: No new '{rest_field}' tags to append.")


        # Commit all edits to Plex
        log("DEBUG", f"Applying edits to '{item_title}'...")
        plex_item.saveEdits()

        # If we get here without exception, mark edits as applied (used to decide artwork upload)
        edits_applied = True

        log("SUCCESS", f"Successfully updated '{item_title}'.")


        # -------------------------------------------
        # Post-processing (statistics, reload, delay)
        # -------------------------------------------
        STATS["updated"].append(item_title)

        if CUSTOM_DELAY > 0:
            time.sleep(CUSTOM_DELAY)

        plex_item.reload()

    except Exception as e:
        log("ERROR", f"Error while updating '{item_title}': {e}")
        STATS["failed"].append(f"{item_title}: Error while updating.")

    # Finally: update the artwork based on NFO filename and if edits were applied
    if edits_applied or ALWAYS_UPDATE_ART:
        log("DEBUG", f"{item_title}: Updating artwork (edits_applied={edits_applied}, ALWAYS_UPDATE_ART={ALWAYS_UPDATE_ART}).")
        update_plex_item_artwork(plex_item, nfo_file)



def update_plex_item_artwork(plex_item, file_path):
    # ==================================
    # Upload artwork file to a Plex item
    # ==================================

    global ALLOW_ART_EXT, DRY_RUN, CUSTOM_DELAY, STATS, ALLOW_UNLOCK, ALLOW_ART_UPDATE, time, os, log

    # Not updating artwork if disabled
    if not ALLOW_ART_UPDATE:
        log("INFO", "Artwork updates are disabled by the ALLOW_ART_UPDATE global setting.")
        return

    # Extract pats and filename components
    base_name = os.path.basename(file_path)
    base_stem, _ext = os.path.splitext(base_name)
    dir_path = os.path.dirname(file_path)

    # Map keywords for upload
    artwork_map = {
        "poster":    ("uploadPoster",    "thumb"),
        "fanart":    ("uploadArt",       "art"),
        "backdrop":  ("uploadArt",       "art"),
        "background":("uploadArt",       "art"),
        "art":       ("uploadArt",       "art"),
        "theme":     ("uploadTheme",     "theme"),
    }

    # Normalized allowed artwork extensions
    allowed_exts = {e.lower().lstrip(".") for e in ALLOW_ART_EXT}
    found_files = []

    # Search for artwork files
    for ext in allowed_exts:
        candidate = os.path.join(dir_path, f"{base_stem}.{ext}")

        # If the file exists, determine which artwork type it corresponds to
        if os.path.isfile(candidate):
            method = None
            lock_field = None
            lower_stem = base_stem.lower()

            # Use keyword matching in the filename to find upload type
            for keyword, (upload_method, field_name) in artwork_map.items():
                if keyword in lower_stem:
                    method = upload_method
                    lock_field = field_name
                    break

            # Fallback: If no keyword found, assume a poster
            if method is None and ext in ("jpg", "jpeg", "png", "webp"):
                method = "uploadPoster"
                lock_field = "thumb"

            # Record valid artwork file for later processing
            if method:
                found_files.append({
                    "filename": os.path.basename(candidate),
                    "fullpath": candidate,
                    "method": method,
                    "lock_field": lock_field
                })

    # No file matched: Stop here
    if not found_files:
        item_title = getattr(plex_item, 'title', 'Unknown Item')
        log("INFO", f"No artwork files found for '{item_title}' matching '{base_stem}'.")
        return

    # Looping through matched files
    for art_file in found_files:
        filename = art_file["filename"]
        fullpath = art_file["fullpath"]
        method = art_file["method"]
        lock_field = art_file["lock_field"]
        item_title = getattr(plex_item, 'title', 'Unknown Item')

        log("INFO", f"Processing '{filename}' for '{item_title}' (method: '{method}').")

        # Check if method exists on this object
        upload_fn = getattr(plex_item, method, None)
        if not callable(upload_fn):
            log("WARNING", f"Plex item '{item_title}' does not have method '{method}'... Skipping.")
            STATS["skipped"].append(f"{item_title}: Method '{method}' not found ({filename}).")
            continue

        # If the field can be locked/unlocked, and we have a lock_field defined
        if lock_field:
            is_locked = False
            # some items may not implement isLocked for that field; catch exceptions
            try:
                is_locked = plex_item.isLocked(lock_field)

            except Exception as e:
                log("DEBUG", f"Could not determine lock state for field '{lock_field}' on '{item_title}': {e}")
                is_locked = False  # assume unlocked

            # Unlock file if it is locked
            if is_locked:
                if ALLOW_UNLOCK:
                    log("INFO", f"Field '{lock_field}' is locked. Attempting unlock for '{item_title}'.")
                    try:
                        plex_item.edit(**{f"{lock_field}.locked": 0})
                        plex_item.reload()

                    except Exception as e:
                        log("ERROR", f"Failed to unlock '{lock_field}' for '{item_title}': {e}")
                        STATS["failed"].append(f"{item_title}: Unlock failed for {lock_field} ({filename}).")
                        continue

                else:
                    log("WARNING", f"Skipping '{filename}' because field '{lock_field}' is locked and ALLOW_UNLOCK is False.")
                    STATS["skipped"].append(f"{item_title}: Artwork upload skipped, field locked ({filename}).")
                    continue

        # Perform upload
        try:
            if DRY_RUN:
                log("INFO", f"[DRY‑RUN] Would upload '{filename}' to '{item_title}' via '{method}'.")
            else:
                upload_fn(filepath=fullpath)
                log("SUCCESS", f"Uploaded '{filename}' as {method} for '{item_title}'.")
                STATS["updated"].append(f"{item_title}: Uploaded '{filename}' ({method})")

                time.sleep(CUSTOM_DELAY)

                # Reload data
                try:
                    plex_item.refresh()
                    plex_item.reload()
                except Exception as e:
                    log("DEBUG", f"Reload failed for '{item_title}' after upload: {e}")

        except Exception as e:
            log("ERROR", f"Failed to upload '{filename}' for '{item_title}': {e}")
            STATS["failed"].append(f"{item_title}: Artwork upload failed ({filename}).")
            continue



def process_data(data={}, automatic_mode=True):
    # =======================================================================================================================================
    # Main processing function: Iterates through discovered media, resolves them to Plex items, and triggers updates for metadata and artwork
    # =======================================================================================================================================

    if not data:
        log("ERROR", "There is no data to work with. Exiting...")
        return

    global ROOT_PLEX_SHOW_DIR, ROOT_PLEX_MOVIE_DIR, SUPPORTED_FIELD_MAP, ALLOW_UNLOCK, DRY_RUN, CUSTOM_DELAY, STATS

    for media_parent_title, media_info in data.items():
        log("INFO", f"Processing parent folder '{media_parent_title}' at path '{media_info['path']}'.")

        path_parts = media_info["path"].lower().split(os.path.sep)
        parent_media_type = None

        if any(part in path_parts for part in ROOT_PLEX_SHOW_DIR):
            parent_media_type = "show"

        elif any(part in path_parts for part in ROOT_PLEX_MOVIE_DIR):
            parent_media_type = "movie"

        parent_plex_item = resolve_plex_item(media_parent_title, parent_media_type, automatic_mode)

        if not parent_plex_item:
            log("WARN", f"Could not resolve parent item for '{media_parent_title}'. Skipping all files within.")
            STATS["skipped"].append(f"{media_parent_title}: Could not resolve parent item in Plex.")
            continue

        log("SUCCESS", f"Resolved parent '{media_parent_title}' to Plex {parent_plex_item.type}: '{parent_plex_item.title}'.")

        for nfo_file in media_info["files"]:
            STATS["processed_nfo"] += 1
            plex_item = None
            log("INFO", f"Processing NFO file: {nfo_file}")

            nfo_data = parse_nfo_to_dict(nfo_file)

            if not nfo_data or not nfo_data.get("title"):
                log("WARN", f"NFO file '{nfo_file}' is empty or missing a title. Skipping.")
                STATS["skipped"].append(f"{nfo_file}: NFO empty or missing title.")
                continue

            media_type = get_media_type_from_nfo(nfo_data)
            nfo_title = nfo_data.get("title")

            # Handling show/season/episode
            if parent_plex_item.type == "show" and media_type in ["show", "season", "episode"]:
                try:
                    if media_type == "show":
                        # Directly use the show item
                        plex_item = parent_plex_item

                    elif media_type == "season":
                        # Try to find the season within the show
                        season_num = nfo_data.get("season") or nfo_data.get("seasonnumber")

                        if season_num:
                            season_num = int(season_num)
                            log("INFO", f"Directly looking for Season {season_num} in '{parent_plex_item.title}'.")
                            plex_item = parent_plex_item.season(season=season_num)

                    elif media_type == "episode":
                        # Try to find the episode within a specific season
                        season_num = nfo_data.get("season")
                        episode_num = nfo_data.get("episode") or nfo_data.get("episodenumber")

                        if season_num and episode_num:
                            season_num = int(season_num)
                            episode_num = int(episode_num)

                            try:
                                log("INFO", f"Directly looking for S{season_num:02d}E{episode_num:02d} in '{parent_plex_item.title}'.")

                                # Getting season
                                season = parent_plex_item.season(season_num)

                                # Getting episode
                                plex_item = season.episode(episode_num)

                            except:
                                # Fallback search: Looping over episodes in season
                                log("WARN", f"Direct lookup failed for S{season_num:02d}E{episode_num:02d} in '{parent_plex_item.title}'. Falling back to loop search.")
                                plex_item = None

                                try:
                                    # Getting season
                                    season = parent_plex_item.season(season_num)

                                    # Iterate through all known episodes in this season
                                    for ep in season.episodes():
                                        if ep.index == episode_num:
                                            plex_item = ep
                                            log("DEBUG", f"Found episode by iterating index ({ep.index}) for S{season_num:02d}E{episode_num:02d} in '{parent_plex_item.title}'.")
                                            break

                                except Exception as e:
                                    log("DEBUG", f"Could not find episode for S{season_num:02d}E{episode_num:02d} in '{parent_plex_item.title}'. Falling back to search.")
                                    plex_item = None

                except Exception as e:
                    log("ERROR", f"Failed to directly find {media_type} from parent '{parent_plex_item.title}': {e}. Falling back to search.")
                    plex_item = None

            # Fallback
            if not plex_item:
                plex_item = resolve_plex_item(nfo_title, media_type, automatic_mode, parent_plex_item)

            if not plex_item:
                log("WARN", f"Could not resolve a Plex item for '{nfo_title}'. Update skipped.")
                STATS["skipped"].append(f"{nfo_title} ({nfo_file}): Could not resolve Plex item.")
                continue

            log("SUCCESS", f"Matched NFO '{nfo_title}' to Plex item '{plex_item.title}'. Starting update process.")

            # --- Pass the parent_plex_item for fallback  ---
            update_plex_item_fields(plex_item, nfo_data, nfo_file)

    # Provide statistics once everything is processed
    summarize_results(STATS)


def summarize_results(STATS):
    # ================================================================
    # Prints a final summary of all operations performed by the script
    # ================================================================

    if not STATS:
        print("\nNo statistics were generated.")
        return

    global DEBUG_MODE, DRY_RUN

    print("\n\n" + "="*20 + " SUMMARY " + "="*20)
    print(f"Dry-run mode: {'ON (no changes were made)' if DRY_RUN else 'OFF (changes were applied)'}")
    print(f"Processed NFO files: {STATS.get('processed_nfo', 0)}")

    # Use set to remove duplicate update messages
    unique_updates = sorted(list(set(STATS.get("updated", []))))

    if unique_updates:
        print(f"\n--- Items Updated: {len(unique_updates)} ---")

        if DEBUG_MODE:
            # Print updated items
            for item in unique_updates:
                print(f"  - {item}")
    else:
        print("\n--- No items were updated ---")

    if STATS.get("skipped"):
        print(f"\n--- Skipped Items ({len(STATS['skipped'])}) ---")

        # Alway print skipped items except if in dry-run
        if not DRY_RUN:
            for item in STATS["skipped"]:
                print(f"  - {item}")

    else:
        print("\n--- No items were skipped ---")

    if STATS.get("failed"):
        print(f"\n--- Failed Operations: ({len(STATS['failed'])}) ---")

        # Always print the failed items
        for item in STATS["failed"]:
            print(f"  - {item}")

    else:
        print("\n--- No items were skipped ---")

    print("\n" + "="*50)
    print("Done.")



###############
# MAIN SCRIPT #
###############

def main():
    log("INFO", f"{SCRIPT_NAME} started.")
    print("Dry-run mode:", "ON (no changes)" if DRY_RUN else "OFF (changes will be applied)")

    # ==== REQUIRED VARIABLES ====
    global ROOT_PLEX_MOVIE_DIR, ROOT_PLEX_SHOW_DIR, SCAN_PATH

    ROOT_PLEX_DIR = ROOT_PLEX_SHOW_DIR + ROOT_PLEX_MOVIE_DIR
    data = {}
    nfo_files = []
    automatic_mode = True
    # ============================

    if not SCAN_PATH:
        # ==== INTERACTIVE MODE ====
        print("Interactive mode:")
        automatic_mode = False

        # Setting SCAN_PATH
        raw_path = input("Enter path (directory) to operate on (TAB for autocompletion): ").strip()
        if not raw_path:
            log("ERROR", "No path provided. Exiting...")
            return

        SCAN_PATH = normalize_path(raw_path)
        # ==========================

    if not os.path.exists(SCAN_PATH):
        log("ERROR", f"Provided path does not exist ({SCAN_PATH}). Exiting...")
        return


    # ==== Searching NFO files and sorting them out based on ROOT_PLEX_DIR ====
    # Recursively find all .nfo files and sort them
    for root, _, files in os.walk(SCAN_PATH):
        for file in files:
            if file.lower().endswith(".nfo"):
                nfo_files.append(os.path.join(root, file))

    nfo_files.sort()


    if len(nfo_files) == 0:
        log("INFO", "No NFO files found. Exiting...")

    log("INFO", f"{len(nfo_files)} NFO files found. Sorting files and setting root directory...")

    root_dirs_lower = [r.lower() for r in ROOT_PLEX_DIR]

    # Sorting files and setting root directory inside data
    for nfo in nfo_files:
        norm = os.path.normpath(nfo)
        parts = norm.split(os.path.sep)

        # Find which root type this file belongs to
        for idx, part in enumerate(parts):
            if part.lower() in root_dirs_lower:
                # Build top-level dir (e.g., /mnt/media/tv/Show)
                end_idx = idx + 2  # "root_dir" + next level (show/movie folder)
                top_path = os.path.join(*parts[:end_idx])
                top_path = os.path.normpath(top_path)
                basename = os.path.basename(top_path)

                if basename not in data:
                    data[basename] = {"id": 0,
                                      "path":f"{top_path}",
                                      "files": []
                                      }

                data[basename]["files"].append(nfo)
                break  # Stop once we’ve matched a root

    # DEBUGGING: Printing data found
    """
    for root, info in data.items():
        print(f"{root}:")
        for f in info["files"]:
            print(f"  - {f}")
    """

    # Process all data
    process_data(data, automatic_mode)



# Running main function
if __name__ == "__main__":
    main()
