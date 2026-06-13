# SMT III Nocturne HD — Steam Deck Mod Kit

A small, **dependency-free** guided installer that sets up the essential
quality-of-life mods for **Shin Megami Tensei III Nocturne HD Remaster** on the
Steam Deck (and any Linux Steam install) — high FPS, the radar fix, and more —
in a couple of clicks.

It exists because doing this by hand involves a half-dozen fiddly steps
(MelonLoader, the right .NET runtime inside the Proton prefix, the exact launch
options, picking compatible mod versions) and several easy-to-hit traps. This
automates the safe parts and clearly hands you the two steps Steam won't let a
script do.

> First-time, **vanilla** experience in mind: every bundled mod is a fix or a
> display/convenience tweak. Nothing alters game balance.

## What it does

1. **Finds your install automatically** — every Steam library, including games
   on a **microSD card**. Falls back to a folder picker if needed.
2. **Lets you pick mods** from a graphical checklist.
3. **Installs MelonLoader 0.6.1** (the exact version these mods require) plus
   your chosen mods.
4. **Installs the .NET 6 Desktop Runtime** into the game's Proton prefix (the
   step most people get stuck on).
5. **Writes your framerate config** (60 or 90 FPS).
6. **Tells you the one launch-options line to paste** and how to optionally bind
   the back buttons — the two things that must be done in Steam's UI.

## Mods offered

| Mod | What it does | Default |
|-----|--------------|---------|
| Fixed Encounter Radar | Fixes the broken (delayed) panic radar | ✅ |
| Graphics Configurator | Unlocks 60/90 FPS, resolution, etc. | ✅ |
| Display Buffs | Shows buff/debuff levels in battle | ✅ |
| Minimap Over Compass | Minimap instead of the radar compass | ☐ |
| Show Skill Changes | Reveals skill-mutation results (English) | ☐ |
| Skip PuzzleBoy (Buy Geis) | Makes the Geis magatama buyable | ☐ |

Mods are **downloaded live from their original GameBanana pages** at install
time — this project never rehosts them, so you always get the current file and
the authors keep their credit and download counts.

The **widescreen cutscene** and **HD audio** packs are intentionally *not*
automated: they're large Google-Drive downloads behind virus-scan pages that
can't be scripted reliably. The Steam guide links them as manual steps.

## Requirements

All preinstalled on SteamOS — nothing to install, no `sudo`, no `pip`:

- `python3`
- `bsdtar` (libarchive)
- `kdialog` **or** `zenity` (a plain-terminal fallback exists if neither)

## Usage

First, install the game from Steam and **launch it once** (this creates the
Proton prefix the .NET step needs — it's fine if it just shows a menu or closes).

### Easiest: double-click launcher

1. Download **`Install-SMT3-Mods.desktop`** to your Deck (e.g. `~/Downloads`).
2. In Desktop Mode, **right-click it → Properties → Permissions → tick "Is
   executable"** (KDE blocks downloaded shortcuts until you allow them).
3. **Double-click it.** It fetches the latest installer and runs it; at the end
   it offers to delete the shortcut for you.

### Alternative: from the terminal

1. Download `install.py`.
2. In Desktop Mode, open **Konsole** and run:
   ```bash
   python3 ~/Downloads/install.py
   ```

Then do the two manual steps it shows you at the end.

## The two manual steps (and why)

- **Launch options.** Paste this into the game's Properties → Launch Options:
  ```
  WINEDLLOVERRIDES="version=n,b" %command% --melonloader.hideconsole
  ```
  Steam server-syncs launch options and reverts any file edit, so a script
  cannot set them. `version=n,b` loads MelonLoader; `--melonloader.hideconsole`
  stops its console window from stealing focus (which otherwise makes the game
  ignore your controller).
- **Play in Game Mode.** Controller input is reliable in Game Mode; Desktop Mode
  is not. This is a SteamOS/focus quirk, not a mod issue.

## Why it won't touch controller bindings

Hand-editing Steam Input controller config files is unreliable — a malformed
file makes Steam emit *no gamepad at all* (symptom: touchscreen works, every
button/stick is dead, in both Desktop and Game Mode). So back-button hotkeys are
left as an **optional, manual** step done through Steam's controller UI:

- **L4 → F9** (hide UI) · **R4 → F11** (60/90 FPS toggle) · **R5 → F10** (speedhack)

Bind them as *keyboard keys* in the game's controller layout.

## Credits

All mods belong to their authors on GameBanana — **bud.** (Graphics
Configurator, Fixed Encounter Radar, Minimap), **Matthiew Purple** (Display
Buffs), and the authors of Show Skill Changes and Buy Geis. MelonLoader by
**LavaGang**. This installer just fetches and places their work; please visit
the GameBanana pages to like/thank them.

Inspired by ffrasisti [ARG]'s Steam guide and Meimei's Steam Deck guide.

## License

The installer code is MIT (see `LICENSE`). The mods it downloads are under their
own licenses and are **not** included in this repository.
