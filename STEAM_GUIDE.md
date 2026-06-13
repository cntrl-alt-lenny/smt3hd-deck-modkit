# Nocturne HD on Steam Deck — the easy way (high FPS + QoL, in a few clicks)

*Draft text for a Steam Community guide. Paste section-by-section into the Steam
guide editor; replace `YOUR-GITHUB-LINK` with the repo URL.*

---

## Overview

Nocturne HD is great on the Steam Deck, but it needs a few fixes and tweaks to
be at its best: the panic radar is broken, it's locked to 30 FPS, and the setup
(MelonLoader + the right .NET runtime + the correct launch options) trips a lot
of people up.

I made a tiny installer that does the fiddly parts for you. You pick the mods
from a list, it finds your game (even on a microSD card), installs everything,
and tells you the two things you have to click yourself. **It keeps the vanilla
experience** — only fixes and display/convenience tweaks, nothing that changes
game balance — so it's safe for a first playthrough.

> Want to do it all by hand instead? The classic full guide by ffrasisti [ARG]
> covers every mod individually. This guide is the fast path.

## Before you start

1. Install **Shin Megami Tensei III Nocturne HD Remaster** from Steam.
2. **Launch it once**, then quit. (This creates the Proton prefix the installer
   needs. It's fine if you just reach the title screen.)

## Step 1 — Run the installer

1. Switch to **Desktop Mode** (hold Power → Switch to Desktop).
2. Download **`Install-SMT3-Mods.desktop`** from here: `YOUR-GITHUB-LINK`
3. Right-click it → **Properties → Permissions → tick "Is executable"** (KDE
   blocks downloaded shortcuts until you allow them), then **double-click it**.
   *(Prefer the terminal? Download `install.py` instead and run
   `python3 ~/Downloads/install.py` in Konsole.)*
4. Tick the mods you want. Defaults (radar fix, high FPS, buff display) are a
   great vanilla-friendly set. Pick **60 FPS** on an LCD Deck, **90 FPS** on the
   OLED.
5. Let it finish. It downloads MelonLoader and your mods, and sets up .NET
   inside the game automatically — then offers to delete the shortcut.

### Mods you can pick

- **Fixed Encounter Radar** — fixes the broken random-encounter warning. *(Get this.)*
- **Graphics Configurator** — unlocks 60/90 FPS and more. *(Get this.)*
- **Display Buffs** — shows buff/debuff levels in battle. *(Recommended.)*
- **Minimap Over Compass** — minimap in the radar. *(Optional.)*
- **Show Skill Changes** — see skill-mutation results. *(Optional, English only.)*
- **Skip PuzzleBoy** — buy your way past the minigame. *(Optional.)*

## Step 2 — Two clicks you have to do yourself

Steam won't let a script change these, so do them once:

**A) Set the launch options.** Back in Steam, right-click the game →
**Properties → General → Launch Options**, and paste exactly:
```
WINEDLLOVERRIDES="version=n,b" %command% --melonloader.hideconsole
```
This loads the mods and hides MelonLoader's console window. **If you skip the
`--melonloader.hideconsole` part, the console steals focus and the game ignores
your controller.**

**B) Play in Game Mode.** Go back to **Gaming Mode** to actually play. The
controller works reliably there (Desktop Mode is finicky — that's a SteamOS
thing, not the mods).

That's it — launch the game and you should be at high FPS with a working radar.

## Optional — back-button hotkeys

The FPS mod uses keyboard keys you can map to the grip buttons. In **Game Mode**,
open the game's **controller settings** and add these as **keyboard** bindings:

- **L4 → F9** — hide the UI
- **R4 → F11** — toggle 60/90 ↔ 30 FPS
- **R5 → F10** — speedhack (fast-forward)

Do this in the Steam controller UI. **Don't** edit controller config files by
hand — a bad edit makes Steam send *no* gamepad input at all (you'll think your
Deck broke).

## Optional — the big extras (manual)

These are too large / awkward to automate, but worth it:

- **Widescreen cutscenes** — replaces the compressed 4:3 FMVs.
  GameBanana mod **400151** (download the actual videos from the author's Google
  Drive, "Widescreen FMV"). Drop `smt3hd_Data` into the game root.
- **HD audio** — higher-quality music (still a work in progress).
  GameBanana **56149** / the r/Megaten release post.

## Troubleshooting

- **Controller does nothing, but touch works** → you're in Desktop Mode, or you
  hand-edited a controller config. Use Game Mode and Steam's default layout.
- **A "missing .NET" error on launch** → launch the game once first, then re-run
  the installer so it can install .NET into the prefix.
- **MelonLoader console keeps popping up** → the `--melonloader.hideconsole`
  part of the launch options is missing.
- **Mods don't load** → make sure you didn't update MelonLoader past **0.6.1**;
  newer versions break these mods.

## Credits

All mods belong to their GameBanana authors — **bud.**, **Matthiew Purple**, and
others — and **LavaGang** for MelonLoader. Please like/thank them on their pages.
The installer just fetches and places their work; it never rehosts anything.
