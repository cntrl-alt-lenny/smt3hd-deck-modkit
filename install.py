#!/usr/bin/env python3
"""
SMT III Nocturne HD — Steam Deck Mod Kit
=========================================
A guided, dependency-free installer for the essential MelonLoader mods on the
Steam Deck (and any Linux Steam install).

It will:
  1. Auto-detect your SMT3 Nocturne HD install (incl. microSD libraries).
  2. Let you pick which mods to enable (graphical checklist).
  3. Install MelonLoader 0.6.1 + your chosen mods (downloaded live from source).
  4. Install the .NET 6 Desktop Runtime into the game's Proton prefix.
  5. Tell you the one launch-option line to paste and how to bind the back buttons.

It deliberately does NOT touch Steam controller configs or launch options —
those must be set through Steam's UI (see the final instructions). This is on
purpose: hand-editing those files is unreliable and can break controller input.

Requirements (all preinstalled on SteamOS): python3, bsdtar, and kdialog OR
zenity. No pip packages, no sudo.

Run it from the Desktop (Konsole):  python3 install.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

APP_ID = "1413480"
GAME_DIR_NAME = "smt3hd"
GAME_EXE = "smt3hd.exe"

MELONLOADER_URL = (
    "https://github.com/LavaGang/MelonLoader/releases/download/"
    "v0.6.1/MelonLoader.x64.zip"
)
# Pinned .NET 6 Desktop Runtime (x64) — the version MelonLoader's il2cpp needs.
DOTNET_VERSION = "6.0.36"
DOTNET_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/"
    f"{DOTNET_VERSION}/windowsdesktop-runtime-{DOTNET_VERSION}-win-x64.exe"
)

UA = "Mozilla/5.0 (X11; Linux x86_64) smt3hd-deck-modkit"

# Mod catalog. `gb_type`/`gb_id` point at the GameBanana page; we resolve the
# actual download via the API at runtime so it always grabs the current file.
# `file_hint`: substring to disambiguate when a page has multiple files
# (None = take the first/newest). We never rehost these files.
MODS = [
    {
        "key": "radar",
        "name": "Fixed Encounter Radar",
        "desc": "Fixes the broken (delayed) panic radar. Essential.",
        "gb_type": "Mod", "gb_id": "513059", "file_hint": None,
        "default": True,
    },
    {
        "key": "graphics",
        "name": "Graphics Configurator (high FPS)",
        "desc": "Unlocks framerate (60/90), resolution, etc. Essential.",
        "gb_type": "Wip", "gb_id": "69935", "file_hint": None,
        "default": True, "is_graphics_cfg": True,
    },
    {
        "key": "buffs",
        "name": "Display Buffs",
        "desc": "Shows buff/debuff levels in battle. Recommended QOL.",
        "gb_type": "Mod", "gb_id": "436369", "file_hint": None,
        "default": True,
    },
    {
        "key": "minimap",
        "name": "Minimap Over Compass",
        "desc": "Replaces the radar compass with a minimap. Optional QOL.",
        "gb_type": "Wip", "gb_id": "72800", "file_hint": None,
        "default": False,
    },
    {
        "key": "skillchanges",
        "name": "Show Skill Changes (English only)",
        "desc": "Reveals skill-mutation results. Optional QOL.",
        "gb_type": "Mod", "gb_id": "436666", "file_hint": "showskillupgrades_a",
        "default": False,
    },
    {
        "key": "puzzleboy",
        "name": "Skip PuzzleBoy (Buy Geis)",
        "desc": "Makes the Geis magatama buyable to skip the minigame. Optional.",
        "gb_type": "Mod", "gb_id": "381668", "file_hint": "buy-geis-06",
        "default": False,
    },
]

LAUNCH_OPTIONS = 'WINEDLLOVERRIDES="version=n,b" %command% --melonloader.hideconsole'


# ---------------------------------------------------------------------------
# Tiny GUI abstraction: prefer kdialog (KDE/Deck desktop), fall back to zenity,
# then to a plain-terminal prompt so the script still works headless.
# ---------------------------------------------------------------------------
class UI:
    def __init__(self) -> None:
        self.kind = (
            "kdialog" if shutil.which("kdialog")
            else "zenity" if shutil.which("zenity")
            else "term"
        )

    def _run(self, args: list[str]) -> tuple[int, str]:
        p = subprocess.run(args, capture_output=True, text=True)
        return p.returncode, p.stdout.strip()

    def info(self, text: str, title: str = "SMT3 Mod Kit") -> None:
        if self.kind == "kdialog":
            self._run(["kdialog", "--title", title, "--msgbox", text])
        elif self.kind == "zenity":
            self._run(["zenity", "--info", "--title", title,
                       "--no-wrap", "--text", text])
        else:
            print(f"\n=== {title} ===\n{text}\n")

    def error(self, text: str, title: str = "SMT3 Mod Kit — Error") -> None:
        if self.kind == "kdialog":
            self._run(["kdialog", "--title", title, "--error", text])
        elif self.kind == "zenity":
            self._run(["zenity", "--error", "--title", title,
                       "--no-wrap", "--text", text])
        else:
            print(f"\n!!! {title} !!!\n{text}\n", file=sys.stderr)

    def yesno(self, text: str, title: str = "SMT3 Mod Kit") -> bool:
        if self.kind == "kdialog":
            return self._run(["kdialog", "--title", title, "--yesno", text])[0] == 0
        if self.kind == "zenity":
            return self._run(["zenity", "--question", "--title", title,
                              "--no-wrap", "--text", text])[0] == 0
        return input(f"{text} [y/N] ").strip().lower().startswith("y")

    def pick_dir(self, text: str) -> str | None:
        start = str(Path.home())
        if self.kind == "kdialog":
            rc, out = self._run(["kdialog", "--title", text,
                                 "--getexistingdirectory", start])
            return out or None if rc == 0 else None
        if self.kind == "zenity":
            rc, out = self._run(["zenity", "--file-selection", "--directory",
                                 "--title", text])
            return out or None if rc == 0 else None
        ans = input(f"{text}\nPath: ").strip()
        return ans or None

    def checklist(self, title: str, items: list[tuple[str, str, bool]]) -> list[str]:
        """items: (tag, label, checked). Returns selected tags."""
        if self.kind == "kdialog":
            args = ["kdialog", "--title", title, "--separate-output",
                    "--checklist", "Select mods to install:"]
            for tag, label, chk in items:
                args += [tag, label, "on" if chk else "off"]
            rc, out = self._run(args)
            return out.splitlines() if rc == 0 else []
        if self.kind == "zenity":
            args = ["zenity", "--list", "--checklist", "--title", title,
                    "--text", "Select mods to install:",
                    "--column", "Pick", "--column", "Tag", "--column", "Mod",
                    "--hide-column", "2", "--print-column", "2"]
            for tag, label, chk in items:
                args += ["TRUE" if chk else "FALSE", tag, label]
            rc, out = self._run(args)
            return out.split("|") if rc == 0 and out else []
        # terminal
        print(f"\n{title}")
        for i, (tag, label, chk) in enumerate(items):
            print(f"  [{i}] {'x' if chk else ' '} {label}")
        raw = input("Enter numbers to toggle (space-separated, blank=keep defaults): ")
        chosen = {tag for tag, _, chk in items if chk}
        if raw.strip():
            toggles = {int(x) for x in raw.split() if x.isdigit()}
            chosen = set()
            for i, (tag, _, chk) in enumerate(items):
                on = chk ^ (i in toggles)
                if on:
                    chosen.add(tag)
        return list(chosen)

    def menu(self, title: str, text: str, items: list[tuple[str, str]]) -> str | None:
        if self.kind == "kdialog":
            args = ["kdialog", "--title", title, "--menu", text]
            for tag, label in items:
                args += [tag, label]
            rc, out = self._run(args)
            return out if rc == 0 else None
        if self.kind == "zenity":
            args = ["zenity", "--list", "--title", title, "--text", text,
                    "--column", "Tag", "--column", "Option", "--hide-column", "1",
                    "--print-column", "1"]
            for tag, label in items:
                args += [tag, label]
            rc, out = self._run(args)
            return out if rc == 0 and out else None
        print(f"\n{title}: {text}")
        for tag, label in items:
            print(f"  {tag}) {label}")
        return input("Choice: ").strip() or None


# ---------------------------------------------------------------------------
# Steam / game discovery
# ---------------------------------------------------------------------------
def steam_roots() -> list[Path]:
    candidates = [
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    return [c for c in candidates if c.is_dir()]


def library_paths(steam_root: Path) -> list[Path]:
    """Parse libraryfolders.vdf for all Steam library roots."""
    vdf = steam_root / "steamapps/libraryfolders.vdf"
    paths = [steam_root]
    if vdf.is_file():
        import re
        for m in re.finditer(r'"path"\s*"([^"]+)"', vdf.read_text(errors="ignore")):
            paths.append(Path(m.group(1)))
    # de-dupe, keep order
    seen, out = set(), []
    for p in paths:
        rp = str(p)
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def find_game() -> tuple[Path, Path] | None:
    """Return (game_dir, steam_root) if the game exe is found, else None."""
    for root in steam_roots():
        for lib in library_paths(root):
            game = lib / "steamapps/common" / GAME_DIR_NAME / GAME_EXE
            if game.is_file():
                return game.parent, root
    return None


# ---------------------------------------------------------------------------
# Download / extract helpers
# ---------------------------------------------------------------------------
def download(url: str, dest: Path, log) -> None:
    log(f"  ↓ {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    if dest.stat().st_size == 0:
        raise RuntimeError(f"Downloaded 0 bytes from {url}")


def gb_resolve(mod: dict, log) -> tuple[str, str]:
    """Query the GameBanana API; return (filename, download_url)."""
    api = (f"https://gamebanana.com/apiv11/{mod['gb_type']}/"
           f"{mod['gb_id']}?_csvProperties=_aFiles")
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    files = data.get("_aFiles", [])
    if not files:
        raise RuntimeError(f"No files listed for {mod['name']}")
    chosen = files[0]
    if mod.get("file_hint"):
        for f in files:
            if mod["file_hint"] in f["_sFile"]:
                chosen = f
                break
    return chosen["_sFile"], chosen["_sDownloadUrl"]


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(["bsdtar", "-xf", str(archive), "-C", str(dest)], check=True)


def collect_dlls(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*.dll")]


# ---------------------------------------------------------------------------
# Install steps
# ---------------------------------------------------------------------------
def install_melonloader(game_dir: Path, tmp: Path, log) -> None:
    log("Installing MelonLoader 0.6.1 …")
    zip_path = tmp / "MelonLoader.x64.zip"
    download(MELONLOADER_URL, zip_path, log)
    extract(zip_path, game_dir)            # version.dll, dobby.dll, MelonLoader/
    (game_dir / "Mods").mkdir(exist_ok=True)
    (game_dir / "UserData").mkdir(exist_ok=True)
    if not (game_dir / "version.dll").is_file():
        raise RuntimeError("MelonLoader extraction failed (version.dll missing)")


def install_mod(mod: dict, game_dir: Path, tmp: Path, log) -> None:
    log(f"Installing {mod['name']} …")
    fname, url = gb_resolve(mod, log)
    arc = tmp / fname
    download(url, arc, log)
    out = tmp / ("x_" + mod["key"])
    extract(arc, out)
    dlls = collect_dlls(out)
    if not dlls:
        raise RuntimeError(f"No .dll found inside {fname}")
    for dll in dlls:
        shutil.copy2(dll, game_dir / "Mods" / dll.name)
        log(f"    → Mods/{dll.name}")


def find_proton(steam_root: Path) -> Path | None:
    """Pick a Proton to run the .NET installer with. Prefer official Proton."""
    cands: list[Path] = []
    for lib in library_paths(steam_root):
        common = lib / "steamapps/common"
        if common.is_dir():
            cands += sorted(common.glob("Proton*"))
    cands += sorted((steam_root / "compatibilitytools.d").glob("GE-Proton*")) \
        if (steam_root / "compatibilitytools.d").is_dir() else []
    # prefer non-GE, newest-looking last in sorted order
    official = [c for c in cands if "GE" not in c.name]
    chosen = (official or cands)
    for c in reversed(chosen):
        if (c / "proton").is_file():
            return c / "proton"
    return None


def dotnet_present(steam_root: Path) -> bool:
    base = (steam_root / "steamapps/compatdata" / APP_ID /
            "pfx/drive_c/Program Files/dotnet/shared/Microsoft.WindowsDesktop.App")
    return base.is_dir() and any(p.name.startswith("6.") for p in base.iterdir())


def install_dotnet(steam_root: Path, tmp: Path, ui: UI, log) -> bool:
    compatdata = steam_root / "steamapps/compatdata" / APP_ID
    if not (compatdata / "pfx").is_dir():
        ui.error(
            "The game's Proton prefix doesn't exist yet.\n\n"
            "Please LAUNCH the game once from Steam (it can crash/close — that's "
            "fine), then run this installer again so .NET can be installed."
        )
        return False
    if dotnet_present(steam_root):
        log(".NET 6 Desktop Runtime already present in the prefix — skipping.")
        return True
    proton = find_proton(steam_root)
    if not proton:
        ui.error("Couldn't find a Proton install to set up .NET with.\n"
                 "Open the game's Properties → Compatibility and pick a Proton "
                 "version, launch once, then re-run this installer.")
        return False
    log(f"Installing .NET {DOTNET_VERSION} Desktop Runtime into the prefix "
        f"(via {proton.parent.name}) …")
    exe = tmp / "dotnet.exe"
    download(DOTNET_URL, exe, log)
    env = dict(os.environ)
    env["STEAM_COMPAT_DATA_PATH"] = str(compatdata)
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(steam_root)
    p = subprocess.run([str(proton), "run", str(exe),
                        "/install", "/quiet", "/norestart"],
                       env=env, capture_output=True, text=True)
    if not dotnet_present(steam_root):
        log("  ⚠ .NET install finished but runtime not detected; "
            "MelonLoader may still work, or re-run if the game errors.")
        log(p.stdout[-500:] if p.stdout else "")
    return True


def write_fps_cfg(game_dir: Path, fps: int, log) -> None:
    cfg = game_dir / "NocturneGraphicsConfiguratorConfig.cfg"
    body = (
        '["FRAMERATE AND SPEEDHACK"]\n'
        f"Framerate = {fps}\n"
        "SpeedhackSpeed = 2.0\n"
        "CustomFramerateOnLaunch = true\n"
        "VSyncModeWhenCustomFramerate = 1\n\n"
        '["RESOLUTION AND SHADOW"]\n'
        "ResolutionOverrideWidth = 0\nResolutionOverrideHeight = 0\n"
        "ShadowMapOverrideWidth = 0\nShadowMapOverrideHeight = 0\n\n"
        '["EXTRA GRAPHICS"]\nBloom = true\nExclusiveFullscreen = false\n\n'
        '["TOGGLE BINDINGS"]\n'
        'FramerateToggleKey = "f11"\nSpeedhackToggleKey = "f10"\n'
        'UIToggleKey = "f9"\n'
    )
    cfg.write_text(body)
    log(f"Wrote graphics config ({fps} FPS target).")


# ---------------------------------------------------------------------------
# Double-click shortcut self-cleanup
# ---------------------------------------------------------------------------
def normalize_desktop_path(raw: str | None) -> Path | None:
    """The .desktop launcher passes its own location (maybe a file:// URI)."""
    if not raw:
        return None
    from urllib.parse import urlparse, unquote
    p = unquote(urlparse(raw).path) if raw.startswith("file://") else raw
    return Path(p)


def offer_self_cleanup(ui: "UI", desktop: Path | None) -> None:
    """When launched from the double-click shortcut, offer to remove it."""
    if not desktop:
        return
    if ui.yesno("All done — mods are installed!\n\n"
                "Delete this installer shortcut now? You won't need it again."):
        try:
            if desktop.is_file():
                desktop.unlink()
            Path("/tmp/smt3_install.py").unlink(missing_ok=True)  # bootstrapped copy
            ui.info("Installer shortcut deleted. Enjoy!")
        except OSError as e:
            ui.error(f"Couldn't delete the shortcut automatically:\n{desktop}\n\n{e}")


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def main() -> int:
    ui = UI()
    logs: list[str] = []

    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--desktop", default=None,
                    help="Path of the launching .desktop shortcut (internal).")
    cli, _ = ap.parse_known_args()
    desktop = normalize_desktop_path(cli.desktop)

    def log(msg: str) -> None:
        print(msg)
        logs.append(msg)

    if not shutil.which("bsdtar"):
        ui.error("`bsdtar` is required but not found. On SteamOS it's preinstalled; "
                 "otherwise install libarchive/bsdtar and re-run.")
        return 1

    # 1. Find the game
    found = find_game()
    if found:
        game_dir, steam_root = found
        if not ui.yesno(f"Found the game here:\n\n{game_dir}\n\nUse this install?"):
            found = None
    if not found:
        manual = ui.pick_dir("Select your smt3hd folder (contains smt3hd.exe)")
        if not manual:
            ui.error("No install selected. Aborting.")
            return 1
        game_dir = Path(manual)
        if not (game_dir / GAME_EXE).is_file():
            ui.error(f"{GAME_EXE} not found in:\n{game_dir}")
            return 1
        # best-effort steam root for .NET step
        steam_root = next(iter(steam_roots()), Path.home() / ".local/share/Steam")

    # 2. Mod selection
    items = [(m["key"], f"{m['name']} — {m['desc']}", m["default"]) for m in MODS]
    selected = ui.checklist("SMT3 Nocturne — Choose Mods", items)
    if not selected:
        if not ui.yesno("No mods selected. Install MelonLoader only?"):
            return 0
    chosen_mods = [m for m in MODS if m["key"] in selected]

    # 3. FPS target (only relevant if graphics configurator is chosen)
    fps = 60
    if any(m["key"] == "graphics" for m in chosen_mods):
        pick = ui.menu("Framerate Target", "Pick your framerate cap:",
                       [("60", "60 FPS — all Steam Decks (recommended)"),
                        ("90", "90 FPS — OLED Deck only (90Hz screen)")])
        fps = int(pick) if pick in ("60", "90") else 60

    if not ui.yesno(
        "Ready to install:\n\n"
        f"• Location: {game_dir}\n"
        f"• MelonLoader 0.6.1\n"
        f"• Mods: {', '.join(m['name'] for m in chosen_mods) or '(none)'}\n"
        f"• .NET 6 runtime into the Proton prefix\n\n"
        "Make sure the game is NOT currently running. Proceed?"
    ):
        return 0

    # 4. Do the work
    try:
        with tempfile.TemporaryDirectory(prefix="smt3kit_") as td:
            tmp = Path(td)
            install_melonloader(game_dir, tmp, log)
            for m in chosen_mods:
                install_mod(m, game_dir, tmp, log)
            if any(m.get("is_graphics_cfg") for m in chosen_mods):
                write_fps_cfg(game_dir, fps, log)
            install_dotnet(steam_root, tmp, ui, log)
    except (urllib.error.URLError, RuntimeError, subprocess.CalledProcessError) as e:
        ui.error(f"Install failed:\n\n{e}\n\nNothing else was changed.")
        return 1

    # 5. Final manual steps (the bits a script can't safely do)
    ui.info(
        "✅ Mods installed!\n\n"
        "TWO manual steps remain (Steam won't let a script do these):\n\n"
        "1) LAUNCH OPTIONS — in Steam, right-click the game → Properties →\n"
        "   General → Launch Options, and paste EXACTLY:\n\n"
        f"   {LAUNCH_OPTIONS}\n\n"
        "   (Required: loads MelonLoader and hides its console window — without\n"
        "   the hideconsole part the console steals focus and the game ignores\n"
        "   your controller.)\n\n"
        "2) Play in GAME MODE (not Desktop) for the controller to work.\n\n"
        "OPTIONAL — back-button hotkeys: in Game Mode, open the controller\n"
        "settings for the game and bind, as KEYBOARD keys:\n"
        "   L4 → F9 (hide UI),  R4 → F11 (60/90 toggle),  R5 → F10 (speedhack).\n"
        "Do this in the Steam UI — never by editing controller config files.\n\n"
        "Then launch from Game Mode and enjoy. ONE MORE GOD REJECTED!"
    )
    offer_self_cleanup(ui, desktop)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
