# TouchDeck

TouchDeck is a fullscreen, touch-friendly shortcut launcher built with PyQt6. It supports
multiple modes, swipe navigation, per-button keyboard shortcuts, and optional icons.

## Features
- Grid of launch buttons with editable labels, colors, and text colors
- Multiple modes with swipe left/right to switch
- Per-button keyboard shortcuts (application-wide)
- Shortcut-only buttons that send key combos to the active window
- Folder buttons (open a folder directly)
- Optional icons per button

## Run
```
python main.py
```

## Edit Buttons
- Click **Edit** to enter edit mode.
- Click a button to edit it, or click **+ Add** to create a new one.
- Use **Record** to capture a shortcut key combo.

## Modes
- Swipe left or right to switch modes.
- Edit mode shows **Add Mode** to create a new mode.

## Configuration
Config is stored under:
```
%LOCALAPPDATA%\TouchDeck\touchdeck.json
```

Key settings:
- `modes`: list of modes, each with a `name` and `buttons`
- `current_mode_index`: index of the active mode
- `swipe_threshold`: pixels needed for a swipe (default: 80)
- `swipe_vertical_tolerance`: max vertical drift (default: 60)
- `icon_size`: icon size in pixels
- `prev_mode_shortcut` / `next_mode_shortcut`: keyboard shortcuts for mode switching

## Build (EXE)
```
pyinstaller --onefile --windowed --name "TouchDeck" --icon "SDE.ico" "main.py"
```

## Build (MSI, WiX v6)
1) Install WiX Toolset v6.
2) Build the MSI from the installer folder:
```
& "C:\Program Files\WiX Toolset v6.0\bin\wix.exe" build TouchDeck.wxs -o TouchDeck.msi
```

## Notes
- Shortcut-only buttons send their key combo to the currently active window.
- If a button has no command and no shortcut, it will not save.
