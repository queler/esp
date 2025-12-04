#!/usr/bin/env python3
import os
import platform
import fnmatch
import re
import pyperclip
from pathlib import Path
from playwright.sync_api import sync_playwright

# ==== CONFIG ==========================================================
PROJECT_URL = "https://wokwi.com/projects/448733698865351681"

# Your local source dir
LOCAL_DIR = "~/build/esp"
LOCAL_DIR = Path(LOCAL_DIR).expanduser()
# Ignore list: exact names or globs (fnmatch)
IGNORE_PATTERNS = [
    # examples:
    # "*_old.py",
    # "scratch_*.py",
]

# Extra non-.py files you still want to sync
EXTRA_FILES = [
    "wifi.json",
]

# Whether to create a new Wokwi file if the tab doesn't exist yet
CREATE_MISSING_FILES = True

# Where to store Playwright auth state (cookies, localStorage, etc.)
STATE_FILE = f"{LOCAL_DIR}/tools/wokwi_state.json"
# ======================================================================


def should_ignore(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_PATTERNS)


def wants_sync(name: str) -> bool:
    if should_ignore(name):
        return False
    if name.endswith(".py"):
        return True
    if name in EXTRA_FILES:
        return True
    return False

def is_logged_in(page) -> bool:
    """
    Logged in if the header contains a user avatar: <div class="MuiAvatar-root">...</div>
    """
    header = page.locator("header")
    # scope to header just to be safe
    avatar = header.locator("div.MuiAvatar-root")
    return avatar.count() > 0

def collect_target_files(local_dir: Path):
    local_files = {p.name: p for p in local_dir.iterdir() if p.is_file()}
    target_files = [name for name in local_files.keys() if wants_sync(name)]
    return local_files, target_files


def find_tab(page, filename: str):
    """
    Tabs are role=button with name=filename, per codegen:
      page.get_by_role("button", name="candle.py")
    """
    loc = page.get_by_role("button", name=filename)
    return loc.first if loc.count() else None


def create_wokwi_file(page, filename: str) -> bool:
    """
    Use the tabs dropdown → 'New file...' flow to create a new file.
    Based on your recorder snippet.
    """
    print(f"  → Creating new Wokwi file '{filename}'")

    # Tabs dropdown: codegen used:
    # page.get_by_role("button").filter(has_text=re.compile(r"^$")).nth(5).click()
    dropdown = page.get_by_role("button").filter(has_text=re.compile(r"^$")).nth(5)
    if not dropdown.count():
        print("  ⚠ Could not find tabs dropdown button (empty-text button nth(5)).")
        return False
    dropdown.click()

    # Click "New file..."
    new_file_item = page.get_by_text("New file...")
    if not new_file_item.count():
        print("  ⚠ Could not find 'New file...' menu item.")
        return False
    new_file_item.click()

    # Fill the file name
    name_input = page.get_by_role("textbox", name="New file name")
    if not name_input.count():
        print("  ⚠ Could not find 'New file name' input.")
        return False
    name_input.fill(filename)

    # Click "Create"
    create_btn = page.get_by_role("button", name="Create")
    if not create_btn.count():
        print("  ⚠ Could not find 'Create' button.")
        return False
    create_btn.click()

    page.wait_for_timeout(500)

    # Confirm tab now exists
    tab = find_tab(page, filename)
    if tab:
        print(f"  ✔ Created Wokwi file '{filename}'")
        return True

    print(f"  ⚠ After attempting to add, still no tab for {filename}")
    return False


def ensure_tab_for_file(page, filename: str, create_if_missing: bool = True):
    tab = find_tab(page, filename)
    if tab or not create_if_missing:
        return tab

    if create_wokwi_file(page, filename):
        return find_tab(page, filename)

    return None


def replace_tab_with_file(page, filename: str, file_path: Path):
    """
    Ensure a tab exists, select it, then replace its content with file_path.
    Uses clipboard + paste to avoid Monaco auto-reindenting line-by-line.
    """
    tab = ensure_tab_for_file(page, filename, create_if_missing=CREATE_MISSING_FILES)
    if not tab:
        print(f"  ✖ No tab for {filename} (and could not create it).")
        return

    print(f"  → Updating tab '{filename}' from {file_path}")
    tab.click()

    # Focus the editor view area (Monaco)
    page.locator(".view-lines").click()

    # This is the hidden Monaco textarea, from your codegen:
    editor_input = page.get_by_role("textbox", name=re.compile(r"Editor content"))
    if not editor_input.count():
        print("  ⚠ Could not find Monaco editor textbox.")
        return
    editor = editor_input.first

    # Select all + clear
    editor.press("ControlOrMeta+a")
    editor.press("Backspace")

    # Read file and put it on the clipboard
    text = file_path.read_text(encoding="utf-8")
    pyperclip.copy(text)

    # Paste once – treat as a single paste event
    paste_key = "Meta+V" if platform.system() == "Darwin" else "Control+V"
    editor.press(paste_key)

    print(f"  ✔ Tab '{filename}' updated (via paste)")

def main():
    local_dir = Path(LOCAL_DIR).expanduser()
    if not local_dir.is_dir():
        print(f"[ERROR] LOCAL_DIR does not exist: {local_dir}")
        return

    local_files, target_files = collect_target_files(local_dir)
    if not target_files:
        print("[ERROR] No files to sync – check LOCAL_DIR / IGNORE_PATTERNS / EXTRA_FILES.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # Use stored auth state if present, otherwise start fresh
        if os.path.exists(Path(STATE_FILE).expanduser()):
            print(f"Using existing session from {STATE_FILE}")
            context = browser.new_context(storage_state=STATE_FILE)
        else:
            print("No stored session found; starting fresh context.")
            context = browser.new_context()

        page = context.new_page()
        print(f"Opening {PROJECT_URL} ...")
        page.goto(PROJECT_URL)
        page.wait_for_load_state("domcontentloaded")

        # First check: are we already logged in (avatar visible)?
        if not is_logged_in(page):
            print("\nYou are NOT logged in (no avatar found).")
            print("→ In the Playwright browser window:")
            print("   - Log in however you like (GitHub, email link, etc.)")
            print("   - Make sure you end up back on THIS project page.")
            input("When you are logged in and see the project editor, press Enter here... ")

            # Reload once after you say you're done
            page.goto(PROJECT_URL)
            page.wait_for_load_state("domcontentloaded")

            if not is_logged_in(page):
                print("[ERROR] Still no avatar after login; aborting save ayway.")
                context.storage_state(path=STATE_FILE)
                #browser.close()
                return

            print("Avatar found; saving session state for future runs.")
            context.storage_state(path=STATE_FILE)
        else:
            print("Avatar present – assuming you are already logged in.")

        # Ensure Monaco is ready
        page.wait_for_selector(".monaco-editor")
        print("Project loaded. Starting sync...")

        for fname in target_files:
            fpath = local_files.get(fname)
            if not fpath:
                print(f"  (Skip) Local file not found: {fname}")
                continue
            replace_tab_with_file(page, fname, fpath)

        # Do NOT click SAVE automatically
        print("\n✅ Sync complete.")
        print("Review the code in the browser and click SAVE manually if you’re happy.")

        input("Press Enter to close the browser...")
        browser.close()


if __name__ == "__main__":
    main()
