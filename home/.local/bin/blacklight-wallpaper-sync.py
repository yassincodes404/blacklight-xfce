#!/usr/bin/env python3
"""
Blacklight Wallpaper-Adaptive System Rice Engine
Maintains a clean, deep obsidian base (#0a0a0d / #101015) that blends seamlessly
with the #000000 terminal, while adapting accent highlights, taskbar icons,
desktop widget to the active wallpaper.
"""

import colorsys
import tempfile
import json
import os
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Xfconf", "0")
from gi.repository import GdkPixbuf, GLib, Xfconf

HOME = Path.home()
PALETTE_DIR = HOME / ".config/blacklight-rice"
PALETTE_JSON = PALETTE_DIR / "palette.json"
GTK3_THEME_DIR = HOME / ".local/share/themes/Blacklight-Ultra/gtk-3.0"
GTK4_THEME_DIR = HOME / ".local/share/themes/Blacklight-Ultra/gtk-4.0"
XFWM4_DIR = HOME / ".local/share/themes/Blacklight-Ultra-Rounded/xfwm4"
USER_GTK3_CSS = HOME / ".config/gtk-3.0/gtk.css"
USER_GTK4_CSS = HOME / ".config/gtk-4.0/gtk.css"

def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(round(v))))


def rgb_to_hex(rgb):
    return f"#{clamp(rgb[0]):02x}{clamp(rgb[1]):02x}{clamp(rgb[2]):02x}"


def hls_to_rgb255(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return [clamp(r * 255), clamp(g * 255), clamp(b * 255)]


SHARED_WALLPAPER = PALETTE_DIR / "wallpaper"
DEFAULT_WALLPAPER = HOME / ".local/share/backgrounds/Galinia/galinia-dusk.png"


def get_active_wallpaper() -> Path:
    if SHARED_WALLPAPER.is_file():
        selected = Path(SHARED_WALLPAPER.read_text().strip())
        if selected.is_file():
            return selected
    return DEFAULT_WALLPAPER


def share_wallpaper(channel, wallpaper, mirrored):
    properties = channel.get_properties("/backdrop")
    targets = {prop for prop in properties if prop.endswith("/last-image")}

    if os.environ.get("XDG_SESSION_TYPE") != "wayland":
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk
        if Gdk.init_check([])[0]:
            screen = Gdk.Screen.get_default()
            workspace = channel.get_int("/backdrop/single-workspace-number", 0)
            for index in range(screen.get_n_monitors()):
                connector = screen.get_monitor_plug_name(index)
                if connector:
                    prefix = f"/backdrop/screen0/monitor{connector}/workspace{workspace}"
                    if not channel.has_property(f"{prefix}/image-style"):
                        channel.set_int(f"{prefix}/image-style", 5)
                    targets.add(f"{prefix}/last-image")

    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        # XFCE 4.20 settings can write the display model while the desktop
        # reads the compositor connector (for example HDMI-A-1).
        workspace = channel.get_int("/backdrop/single-workspace-number", 0)
        for status in Path("/sys/class/drm").glob("card*-*/status"):
            if status.read_text().strip() != "connected":
                continue
            connector = status.parent.name.split("-", 1)[1]
            prefix = f"/backdrop/screen0/monitor{connector}/workspace{workspace}"
            style = f"{prefix}/image-style"
            if not channel.has_property(style):
                channel.set_int(style, 5)  # Zoomed.
            targets.add(f"{prefix}/last-image")

    for prop in sorted(targets):
        if properties.get(prop) != str(wallpaper):
            mirrored[prop] = str(wallpaper)
            if not channel.set_string(prop, str(wallpaper)):
                mirrored.pop(prop, None)


def extract_palette_from_wallpaper(img_path: Path) -> dict:
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(img_path), 96, 96, False)
        pixels = pixbuf.get_pixels()
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        rowstride = pixbuf.get_rowstride()
        n_chan = pixbuf.get_n_channels()

        rgb_list = []
        vivid_samples = []
        for y in range(h):
            row_off = y * rowstride
            for x in range(w):
                idx = row_off + x * n_chan
                r = pixels[idx]
                g = pixels[idx + 1]
                b = pixels[idx + 2]
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                hue, light, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
                rgb_list.append((lum, r, g, b, hue, light, sat))
                if sat > 0.28 and 0.16 < light < 0.88:
                    weight = (sat ** 1.3) * (0.4 + 0.6 * min(1.0, light * 1.4))
                    vivid_samples.append((weight, hue, light, sat, r, g, b))
    except Exception:
        rgb_list = []
        vivid_samples = []

    if not rgb_list:
        rgb_list = [(20.0, 14, 14, 18, 0.66, 0.06, 0.04)]

    n = len(rgb_list)
    # Only treat wallpaper as colored if >= 4.5% of the image has distinct color
    # (prevents tiny floor notes or compression artifacts on black wallpapers from turning windows brown/yellow)
    has_color = len(vivid_samples) >= int(n * 0.045)
    # The supplied wallpaper concentrates its color in the small flame mark.
    branded = img_path == DEFAULT_WALLPAPER or img_path == DEFAULT_WALLPAPER.with_suffix(".svg")
    has_color = has_color or branded
    is_mono = not has_color

    if branded:
        dom_hue, dom_sat = 0.075, 0.75
    elif has_color:
        bins = [0.0] * 24
        hue_sum = [0.0] * 24
        sat_sum = [0.0] * 24
        for w_val, hue, light, sat, r, g, b in vivid_samples:
            b_idx = int(hue * 24) % 24
            bins[b_idx] += w_val
            hue_sum[b_idx] += hue * w_val
            sat_sum[b_idx] += sat * w_val
        best_bin = max(range(24), key=lambda i: bins[i])
        dom_hue = (hue_sum[best_bin] / bins[best_bin]) % 1.0
        dom_sat = min(0.75, max(0.35, sat_sum[best_bin] / bins[best_bin]))
    else:
        dom_hue = 0.66
        dom_sat = 0.05

    # Keep surfaces ultra-clean deep obsidian (#0a0a0d -> #101015 -> #18181f) with at most 5% hue whisper
    # so window frames and internal windows NEVER look muddy brown/yellow and always match the #000000 terminal!
    surf_s = 0.06 if has_color else 0.05
    bg_0 = hls_to_rgb255(dom_hue, 0.042, surf_s)  # ~#0a0a0c
    bg_1 = hls_to_rgb255(dom_hue, 0.068, surf_s)  # ~#111113
    bg_2 = hls_to_rgb255(dom_hue, 0.102, surf_s)  # ~#19191c
    bg_3 = hls_to_rgb255(dom_hue, 0.148, surf_s * 1.2)  # ~#242429
    border = hls_to_rgb255(dom_hue, 0.175, surf_s * 1.1)  # ~#2b2b31 (clean subtle dark graphite border)

    if is_mono:
        accent = [242, 242, 248]       # #f2f2f8 crisp ice white
        accent_soft = [180, 180, 194]  # #b4b4c2 clean silver
        fg_0 = [240, 240, 246]         # #f0f0f6
        fg_1 = [166, 166, 180]         # #a6a6b4
    else:
        accent = hls_to_rgb255(dom_hue, 0.80, min(0.70, max(0.42, dom_sat * 0.95)))
        accent_soft = hls_to_rgb255(dom_hue, 0.64, min(0.45, max(0.25, dom_sat * 0.65)))
        fg_0 = [240, 240, 245]
        fg_1 = [170, 170, 182]

    sel_fg = bg_0

    return {
        "wallpaper": str(img_path),
        "is_mono": is_mono,
        "bg_0_rgb": bg_0,
        "bg_1_rgb": bg_1,
        "bg_2_rgb": bg_2,
        "bg_3_rgb": bg_3,
        "border_rgb": border,
        "accent_rgb": accent,
        "accent_soft_rgb": accent_soft,
        "bg_0": rgb_to_hex(bg_0),
        "bg_1": rgb_to_hex(bg_1),
        "bg_2": rgb_to_hex(bg_2),
        "bg_3": rgb_to_hex(bg_3),
        "border_hex": rgb_to_hex(border),
        "accent_hex": rgb_to_hex(accent),
        "accent_soft_hex": rgb_to_hex(accent_soft),
        "fg_hex": rgb_to_hex(fg_0),
        "sub_hex": rgb_to_hex(fg_1),
        "sel_fg_hex": rgb_to_hex(sel_fg),
        "bg_rgb": bg_0,
        "card_rgb": bg_1,
    }


def build_custom_gtk3_css(pal: dict) -> str:
    b0r, b0g, b0b = pal["bg_0_rgb"]
    b1r, b1g, b1b = pal["bg_1_rgb"]
    b2r, b2g, b2b = pal["bg_2_rgb"]
    b3r, b3g, b3b = pal["bg_3_rgb"]
    ar, ag, ab = pal["accent_rgb"]

    return f"""/* ==========================================================================
   Blacklight Wallpaper-Adaptive System Rice (GTK 3.0)
   Auto-generated by blacklight-wallpaper-sync.py
   ========================================================================== */

@define-color theme_fg_color {pal['fg_hex']};
@define-color theme_text_color {pal['fg_hex']};
@define-color theme_bg_color {pal['bg_0']};
@define-color theme_base_color {pal['bg_1']};
@define-color theme_selected_bg_color {pal['bg_3']};
@define-color theme_selected_fg_color {pal['accent_hex']};
@define-color borders {pal['border_hex']};

/* --- Global High-Visibility Text Cursor (Caret) & Selection --- */
*,
entry,
spinbutton,
textview,
textview text,
view {{
    caret-color: #ffffff;
    -gtk-secondary-caret-color: {pal['accent_hex']};
}}

selection,
*:selected {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
}}

/* --- One full-width wallpaper-adaptive main bar --- */
.xfce4-panel.background {{
    padding: 0 6px;
    background-color: {pal['bg_1']};
    border: none;
    border-bottom: 1px solid {pal['border_hex']};
    border-radius: 0;
    box-shadow: none;
    color: {pal['fg_hex']};
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 500;
}}

.xfce4-panel.background button,
.xfce4-panel.background button.flat {{
    min-height: 0;
    min-width: 0;
    background-image: none;
    background-color: transparent;
    border: none;
    border-image: none;
    border-radius: 6px;
    box-shadow: none;
    color: {pal['accent_hex']};
    margin: 3px 2px;
    padding: 0 5px;
}}

.xfce4-panel.background image,
.xfce4-panel.background button image {{
    padding: 0;
    margin: 0;
    min-width: 0;
    min-height: 0;
    color: {pal['accent_hex']};
    -gtk-icon-shadow: none;
}}

.xfce4-panel.background button:hover {{
    background-color: {pal['bg_2']};
}}
.xfce4-panel.background button:active,
.xfce4-panel.background button:checked {{
    background-color: {pal['bg_3']};
}}

/* Consistent task-button hit areas around 16px icons. */
.xfce4-panel.background .tasklist button {{
    min-width: 28px;
    min-height: 0;
    margin: 3px 2px;
    padding: 0;
}}
.xfce4-panel.background .tasklist button:checked {{
    box-shadow: inset 0 -2px 0 {pal['accent_hex']};
}}

#clock-button {{
    padding: 0 9px;
    margin: 3px 2px;
    font-weight: 500;
    color: {pal['fg_hex']};
}}

/* External plugin windows need the same opaque surface as the full bar. */
#XfcePanelWindowWrapper,
#XfcePanelWindowWrapper.xfce4-panel,
.xfce4-panel .systray,
.xfce4-panel > box {{
    background-color: {pal['bg_1']};
    color: {pal['accent_hex']};
    border: none;
    border-radius: 0;
    box-shadow: none;
}}

/* Shared window surfaces, including legacy Xfce notebook pages and dialogs. */
window.background, dialog.background, messagedialog.background,
window.background:backdrop, dialog.background:backdrop,
notebook, notebook > stack, notebook > stack:backdrop,
notebook > stack > box, notebook > stack > grid,
.dialog-vbox, .dialog-action-area {{
    background-image: none;
    background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}

#galinia-settings-search {{
    min-height: 34px;
    border-radius: 11px;
}}

/* --- 2. Entries, Search & Application Finder --- */
entry,
searchentry,
#whiskermenu-window entry {{
    min-height: 30px;
    padding: 2px 10px;
    border-radius: 8px;
    background-color: {pal['bg_2']};
    color: {pal['fg_hex']};
    caret-color: #ffffff;
    border: 1px solid {pal['border_hex']};
    box-shadow: none;
    border-image: none;
}}

entry:focus,
searchentry:focus,
#whiskermenu-window entry:focus {{
    border-color: {pal['accent_hex']};
    background-color: {pal['bg_2']};
    box-shadow: none;
    border-image: none;
}}

entry image,
searchentry image {{
    color: {pal['sub_hex']};
}}

/* --- 3. Internal Windows, Settings Manager, Thunar & Dialogs --- */
window.background,
dialog.background,
messagedialog.background,
.xfce4-settings-manager {{
    background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}

headerbar,
.titlebar,
toolbar,
.primary-toolbar {{
    background-color: {pal['bg_0']};
    background-image: none;
    color: {pal['fg_hex']};
    border-bottom: 1px solid {pal['border_hex']};
    box-shadow: none;
}}

toolbar button,
.primary-toolbar button,
.path-bar button {{
    color: {pal['fg_hex']};
    border-radius: 7px;
}}

toolbar button:hover,
.primary-toolbar button:hover,
.path-bar button:hover {{
    background-color: {pal['bg_2']};
    color: {pal['accent_hex']};
}}

iconview.view,
.view {{
    background-color: transparent;
    color: {pal['fg_hex']};
    border-radius: 8px;
}}

iconview.view cell:hover {{
    background-color: {pal['bg_2']};
    color: #ffffff;
}}

iconview.view:selected,
treeview.view:selected,
row:selected {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
    border-radius: 7px;
}}

/* Thunar Sidebar & Places Sidebar */
.sidebar,
.sidebar .view,
placessidebar,
placessidebar list,
.thunar .sidebar,
.thunar treeview.view {{
    background-color: {pal['bg_1']};
    color: {pal['fg_hex']};
    border-right: 1px solid {pal['border_hex']};
}}

placessidebar row,
.sidebar row {{
    border-radius: 7px;
    margin: 2px 5px;
    padding: 4px 6px;
}}

placessidebar row:hover,
.sidebar row:hover {{
    background-color: {pal['bg_2']};
}}

placessidebar row:selected,
.sidebar row:selected,
.thunar .sidebar treeview.view:selected {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
}}

.thunar scrolledwindow,
.thunar .standard-view,
exo-icon-view.view {{
    background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}

statusbar {{
    background-color: {pal['bg_1']};
    color: {pal['sub_hex']};
    border-top: 1px solid {pal['border_hex']};
}}

/* Clean Modern Pill Buttons across Settings, Dialogs & Toolbars */
button:not(.flat):not(.titlebutton) {{
    background-color: {pal['bg_2']};
    color: {pal['fg_hex']};
    border: 1px solid {pal['border_hex']};
    border-radius: 8px;
    padding: 4px 12px;
    box-shadow: none;
    background-image: none;
}}

button:not(.flat):not(.titlebutton):hover {{
    background-color: {pal['bg_3']};
    border-color: {pal['sub_hex']};
    color: #ffffff;
}}

button:not(.flat):not(.titlebutton):active,
button:not(.flat):not(.titlebutton):checked,
button.suggested-action {{
    background-color: {pal['bg_3']};
    border-color: {pal['accent_hex']};
    color: {pal['accent_hex']};
}}

/* Clean Modern Tabs (Notebooks) */
notebook > header {{
    background-color: {pal['bg_1']};
    border-color: {pal['border_hex']};
    padding: 0 4px;
}}

notebook > header > tabs > tab {{
    color: {pal['sub_hex']};
    background-color: transparent;
    background-image: none;
    padding: 3px 11px;
    min-height: 23px;
    margin: 0 2px;
    border-radius: 5px 5px 0 0;
    border: none;
    box-shadow: none;
}}

notebook > header > tabs > tab:hover {{
    color: {pal['fg_hex']};
    background-color: {pal['bg_2']};
}}

notebook > header > tabs > tab:checked {{
    color: {pal['accent_hex']};
    background-color: {pal['bg_2']};
    box-shadow: inset 0 -2px 0 {pal['accent_hex']};
}}

notebook > stack {{
    background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}

/* Tab close controls follow tab state without bringing a button tile. */
notebook > header > tabs > tab button {{
    border: none;
    border-image: none;
    background: transparent;
    box-shadow: none;
    padding: 2px 4px;
    min-width: 16px;
    min-height: 16px;
    color: {pal['sub_hex']};
}}
notebook > header > tabs > tab button:hover {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
}}

/* Keep GTK's scalable check/radio glyphs and state behavior. */
checkbutton check, radiobutton radio {{
    min-width: 16px;
    min-height: 16px;
    padding: 0;
    margin: 0;
    border: 1px solid {pal['sub_hex']};
    background-color: {pal['bg_2']};
    background-image: none;
    box-shadow: none;
}}
checkbutton check {{ border-radius: 4px; margin-right: 6px; }}
radiobutton radio {{ border-radius: 50%; margin-right: 6px; }}
checkbutton check:checked, checkbutton check:indeterminate,
radiobutton radio:checked, radiobutton radio:indeterminate,
checkbutton check:checked:hover, checkbutton check:checked:disabled,
checkbutton check:checked:backdrop,
radiobutton radio:checked:hover, radiobutton radio:checked:disabled,
radiobutton radio:checked:backdrop {{
    background-image: none;
    box-shadow: none;
    background-color: {pal['accent_hex']};
    border-color: {pal['accent_hex']};
    color: {pal['bg_0']};
}}
checkbutton check:disabled, radiobutton radio:disabled {{
    opacity: 0.5;
}}
switch {{
    min-width: 34px;
    min-height: 18px;
    padding: 1px;
    border: 1px solid {pal['border_hex']};
    border-radius: 12px;
    background-image: none;
    background-color: {pal['bg_3']};
    box-shadow: none;
    color: transparent;
}}
switch slider {{
    min-width: 16px;
    min-height: 16px;
    margin: 0;
    border: none;
    border-radius: 50%;
    background-image: none;
    background-color: {pal['sub_hex']};
    box-shadow: none;
}}
switch:checked {{
    background-color: {pal['accent_soft_hex']};
    border-color: {pal['accent_soft_hex']};
}}
switch:checked slider {{ background-color: {pal['fg_hex']}; }}
switch:disabled {{ opacity: 0.5; }}

/* Plain proportional controls; replace the base theme's 32px ripple knobs. */
scale.horizontal {{ padding: 10px 8px; }}
scale.vertical {{ padding: 8px 10px; }}
scale trough {{
    min-width: 4px;
    min-height: 4px;
    border: none;
    border-radius: 2px;
    background-image: none;
    background-color: {pal['border_hex']};
}}
scale highlight,
progressbar progress {{
    background-image: none;
    background-color: {pal['accent_hex']};
    border-radius: 2px;
}}
scale slider,
scale slider:hover,
scale slider:active,
scale slider:disabled,
scale.fine-tune slider {{
    min-width: 12px;
    min-height: 12px;
    margin: -5px;
    padding: 0;
    border: 1px solid {pal['bg_1']};
    border-radius: 50%;
    background-image: none;
    background-color: {pal['accent_hex']};
    box-shadow: none;
    animation: none;
    transition: none;
}}
scale slider:disabled {{ background-color: {pal['sub_hex']}; }}

/* Sleek Thin Scrollbars */
scrollbar {{
    background-color: transparent;
    border: none;
}}

scrollbar slider {{
    background-color: {pal['border_hex']};
    border-radius: 6px;
    min-width: 5px;
    min-height: 5px;
    border: none;
}}

scrollbar slider:hover {{
    background-color: {pal['sub_hex']};
}}

/* Adwaita paints these child surfaces gray on backdrop independently
   of window.background. Keep each surface on the same palette on blur. */
menubar, .menubar, menubar:backdrop, .menubar:backdrop,
textview text, textview text:backdrop,
.thunar .standard-view, .thunar .standard-view:backdrop,
.thunar .standard-view .view, .thunar .standard-view .view:backdrop,
exo-icon-view.view, exo-icon-view.view:backdrop {{
    background-image: none;
    background-color: {pal['bg_0']};
}}
.view:backdrop, iconview:backdrop,
.view text:backdrop, iconview text:backdrop {{
    background-image: none;
    background-color: transparent;
}}
.thunar .standard-view .view:backdrop, exo-icon-view.view:backdrop {{
    background-color: {pal['bg_0']};
}}
.sidebar .view:backdrop, .thunar .sidebar treeview.view:backdrop,
placessidebar list:backdrop {{
    background-color: {pal['bg_1']};
}}
.view:selected:backdrop, iconview:selected:backdrop, row:selected:backdrop,
.thunar .standard-view .view:selected:backdrop,
.thunar .sidebar treeview.view:selected:backdrop {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
}}

/* Exo/xfdesktop temporarily add the rubberband class to the view
   itself. Keep the outline square: Exo only repaints a one-pixel edge
   where old and new rectangles overlap. Rounded edges leave stale pixels. */
rubberband, .rubberband, .view.rubberband,
.content-view rubberband, .content-view .rubberband,
treeview.view rubberband, flowbox rubberband,
.thunar .standard-view .view.rubberband,
.thunar .standard-view .view.rubberband:active,
.thunar .standard-view .view.rubberband:backdrop,
.thunar .standard-view iconview.view.rubberband:selected:backdrop,
.thunar .standard-view exo-icon-view.view.rubberband:selected:backdrop {{
    background-image: none;
    background-color: alpha({pal['accent_hex']}, 0.17);
    border: 1px solid alpha({pal['accent_hex']}, 0.82);
    border-radius: 0;
    box-shadow: none;
    transition: none;
}}

/* Inactive windows keep the same surfaces instead of reverting to base gray. */
window.background:backdrop, dialog.background:backdrop {{
    background-color: {pal['bg_0']}; color: {pal['fg_hex']};
}}
entry:backdrop {{
    background-image: none; background-color: {pal['bg_2']};
    border-color: {pal['border_hex']}; color: {pal['fg_hex']};
}}
headerbar:backdrop, toolbar:backdrop, .titlebar:backdrop {{
    background-image: none; background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}
switch:backdrop {{
    background-image: none; background-color: {pal['bg_3']};
    border-color: {pal['border_hex']};
}}
switch:checked:backdrop {{
    background-image: none; background-color: {pal['accent_soft_hex']};
    border-color: {pal['accent_soft_hex']};
}}
switch:backdrop slider {{
    background-image: none; background-color: {pal['sub_hex']};
    border: none; box-shadow: none;
}}
switch:checked:backdrop slider {{ background-color: {pal['fg_hex']}; }}
scale slider:backdrop {{
    background-image: none; background-color: {pal['accent_hex']};
    border-color: {pal['bg_1']}; box-shadow: none;
}}
checkbutton check:checked:backdrop:disabled,
radiobutton radio:checked:backdrop:disabled {{
    background-image: none; background-color: {pal['accent_hex']};
    color: {pal['bg_0']};
}}

/* --- 4. XFCE Notifications (#XfceNotifyWindow) --- */
#XfceNotifyWindow {{
    background-color: rgba({b1r}, {b1g}, {b1b}, 0.95);
    border: 1px solid {pal['accent_hex']};
    border-radius: 12px;
    color: {pal['fg_hex']};
}}

#XfceNotifyWindow label#summary {{
    color: {pal['accent_hex']};
    font-weight: 800;
}}

#XfceNotifyWindow label#body {{
    color: {pal['fg_hex']};
}}

/* --- 5. Terminal Inner Breathing Room (VTE Padding) --- */
vte-terminal {{
    padding: 12px 15px;
}}

/* --- 6. Client-Side Decorated (CSD) Windows, Menus & Tooltips --- */
window.csd:not(.maximized):not(.fullscreen):not(.tiled),
window.csd:not(.maximized):not(.fullscreen):not(.tiled) decoration {{
    border-radius: 10px;
    border: 1px solid {pal['border_hex']};
}}

window.csd:not(.maximized):not(.fullscreen):not(.tiled) headerbar,
window.csd:not(.maximized):not(.fullscreen):not(.tiled) .titlebar {{
    background-color: {pal['bg_1']};
    color: {pal['fg_hex']};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid {pal['border_hex']};
}}

menu,
.menu,
.context-menu,
popover.background,
tooltip.background {{
    background-color: {pal['bg_1']};
    border: 1px solid {pal['border_hex']};
    border-radius: 9px;
    color: {pal['fg_hex']};
    padding: 4px;
}}

menuitem {{
    border-radius: 6px;
    padding: 5px 8px;
    color: {pal['fg_hex']};
}}

menuitem:hover {{
    background-color: {pal['bg_3']};
    color: {pal['accent_hex']};
}}
"""


def patch_base_gtk_theme(pal: dict):
    # GTK's bundled base supplies scalable state glyphs and complete keyboard,
    # disabled, hover, focus and accessibility behavior. No bitmap theme assets.
    base = '@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");\n'
    atomic_write(GTK3_THEME_DIR / "gtk.css", base + build_custom_gtk3_css(pal))


def write_user_gtk_css(pal: dict):
    gtk3_css = build_custom_gtk3_css(pal)
    USER_GTK3_CSS.parent.mkdir(parents=True, exist_ok=True)
    # A few legacy utilities load their own application-priority notebook CSS.
    gtk3_compat = f"""
headerbar, .titlebar {{
    min-height: 28px;
    padding: 0 6px;
}}
headerbar button.titlebutton, .titlebar button.titlebutton {{
    min-width: 24px;
    min-height: 24px;
    padding: 0 3px;
    margin: 0;
    border-radius: 6px;
}}
/* Thunar uses ACTIVE or SELECTED on the view to tint icons. The class
   matches both Exo icon views and GTK tree views, regardless of node name. */
.standard-view .view:active,
.standard-view .view:selected,
.standard-view .view:selected:active,
.standard-view .view:selected:backdrop {{
    background-color: transparent;
}}
.standard-view .view:selected,
.standard-view .view:selected:active,
.standard-view .view:selected:backdrop {{
    background-image: image({pal['bg_3']});
    color: {pal['accent_hex']};
}}
.standard-view .view.rubberband,
.standard-view .view.rubberband:active,
.standard-view .view.rubberband:selected,
.standard-view .view.rubberband:selected:active,
.standard-view .view.rubberband:selected:backdrop {{
    background-color: alpha({pal['accent_hex']}, 0.17);
    background-image: none;
    border: 1px solid alpha({pal['accent_hex']}, 0.82);
    border-radius: 0;
    box-shadow: none;
    transition: none;
}}
notebook, notebook > header, notebook > stack, notebook > stack:not(:only-child) {{
    background: {pal['bg_0']};
    border-color: {pal['border_hex']};
    box-shadow: none;
}}
notebook > header > tabs > tab {{
    color: {pal['sub_hex']};
}}
notebook > header > tabs > tab:checked {{
    background: transparent;
    color: {pal['accent_hex']};
    box-shadow: inset 0 -2px {pal['accent_hex']};
}}
"""
    atomic_write(USER_GTK3_CSS, gtk3_compat)

    gtk4_css = f"""/* Blacklight Wallpaper-Adaptive System Rice (GTK 4.0) */
@define-color theme_fg_color {pal['fg_hex']};
@define-color theme_text_color {pal['fg_hex']};
@define-color theme_bg_color {pal['bg_0']};
@define-color theme_base_color {pal['bg_1']};
@define-color theme_selected_bg_color {pal['bg_3']};
@define-color theme_selected_fg_color {pal['accent_hex']};

*,
entry,
text,
textview {{
    caret-color: #ffffff;
}}

window.background,
dialog.background {{
    background-color: {pal['bg_0']};
    color: {pal['fg_hex']};
}}

window.csd:not(.maximized):not(.fullscreen):not(.tiled) {{
    border-radius: 10px;
    border: 1px solid {pal['border_hex']};
}}

headerbar,
.titlebar {{
    background-color: {pal['bg_0']};
    background-image: none;
    color: {pal['fg_hex']};
    border-bottom: 1px solid {pal['border_hex']};
}}

headerbar > windowhandle > box {{
    min-height: 30px;
    padding: 0 6px;
}}
headerbar windowcontrols button {{
    min-width: 24px;
    min-height: 24px;
    padding: 0 3px;
    border-radius: 6px;
}}
notebook > header > tabs > tab {{
    min-height: 23px;
    padding: 3px 11px;
}}
notebook > header > tabs > tab:checked {{
    background: transparent;
    box-shadow: inset 0 -2px {pal['accent_hex']};
}}

/* Keep editor and menu surfaces stable when focus moves to another window. */
menubar, menubar:backdrop, popover.menubar:backdrop,
textview, textview:backdrop, textview text, textview text:backdrop {{
    background-image: none;
    background-color: {pal['bg_0']};
}}

rubberband {{
    background-color: alpha({pal['accent_hex']}, 0.17);
    border: 1px solid alpha({pal['accent_hex']}, 0.82);
    border-radius: 0;
    box-shadow: none;
    transition: none;
}}

popover.background > contents {{
    background-color: {pal['bg_1']};
    border: 1px solid {pal['border_hex']};
    border-radius: 9px;
    color: {pal['fg_hex']};
}}
"""
    USER_GTK4_CSS.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(USER_GTK4_CSS, gtk4_css)


def update_xfwm4_theme(pal: dict):
    """
    Uses a clean, deep obsidian titlebar (#0b0b0e) and subtle dark graphite 1px border (#23232c)
    so the window frame around the #000000 terminal looks sleek and seamless instead of brown/yellow!
    """
    if not XFWM4_DIR.exists():
        return

    bg_act = pal["bg_0"]
    bg_inact = pal["bg_0"]
    frame_act = pal["border_hex"]
    frame_inact = pal["bg_2"]
    bot_line = bg_act
    accent = pal["accent_hex"]
    fg_act = pal["fg_hex"]
    fg_inact = pal["sub_hex"]
    sel_fg = pal["bg_0"]

    themerc = (
        f"# Blacklight-Ultra-Rounded (Sleek Obsidian Window Frame)\n"
        f"active_text_color={fg_act}\n"
        f"active_text_shadow_color=#000000\n"
        f"inactive_text_color={fg_inact}\n"
        f"inactive_text_shadow_color=#000000\n"
        f"title_shadow_active=false\n"
        f"title_shadow_inactive=false\n"
        f"full_width_title=true\n"
        f"title_vertical_offset_active=0\n"
        f"title_vertical_offset_inactive=0\n"
        f"button_offset=9\n"
        f"button_spacing=2\n"
        f"shadow_delta_height=0\n"
        f"shadow_delta_width=0\n"
        f"shadow_delta_x=0\n"
        f"shadow_delta_y=0\n"
        f"shadow_opacity=100\n"
        f"show_app_icon=false\n"
        f"show_popup_shadow=false\n"
        f"button_layout=|HMC\n"
        f"sync_to_vblank=false\n"
        f"vblank_mode=none\n"
        f"raise_delay=200\n"
        f"focus_delay=200\n"
        f"double_click_time=200\n"
        f"title_alignment=center\n"
    )
    (XFWM4_DIR / "themerc").write_text(themerc, encoding="utf-8")

    for i in range(1, 6):
        (XFWM4_DIR / f"title-{i}-active.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="32" viewBox="0 0 2 32">'
            f'<rect width="2" height="32" fill="{bg_act}"/>'
            f'<rect width="2" height="1" fill="{frame_act}"/>'
            f'<rect y="31" width="2" height="1" fill="{bot_line}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )
        (XFWM4_DIR / f"title-{i}-inactive.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="32" viewBox="0 0 2 32">'
            f'<rect width="2" height="32" fill="{bg_inact}"/>'
            f'<rect width="2" height="1" fill="{frame_inact}"/>'
            f'<rect y="31" width="2" height="1" fill="{bg_act}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )

    for extra in ["menu", "shade", "shade-toggled", "stick", "stick-toggled"]:
        for state, bg_c, hi_c in [
            ("active", bg_act, frame_act),
            ("prelight", bg_act, frame_act),
            ("pressed", bg_act, frame_act),
            ("inactive", bg_inact, frame_inact),
        ]:
            (XFWM4_DIR / f"{extra}-{state}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="32" viewBox="0 0 4 32">'
                f'<rect width="4" height="32" fill="{bg_c}"/>'
                f'<rect width="4" height="1" fill="{hi_c}"/>'
                f'</svg>\n',
                encoding="utf-8",
            )

    (XFWM4_DIR / "top-left-active.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="32" viewBox="0 0 10 32">'
        f'<path fill="{bg_act}" d="M0 32V10A10 10 0 0 1 10 0V32Z"/>'
        f'<path fill="none" stroke="{frame_act}" stroke-width="1" d="M0.5 32V10A9.5 9.5 0 0 1 10 0.5"/>'
        f'</svg>\n',
        encoding="utf-8",
    )
    (XFWM4_DIR / "top-left-inactive.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="32" viewBox="0 0 10 32">'
        f'<path fill="{bg_inact}" d="M0 32V10A10 10 0 0 1 10 0V32Z"/>'
        f'<path fill="none" stroke="{frame_inact}" stroke-width="1" d="M0.5 32V10A9.5 9.5 0 0 1 10 0.5"/>'
        f'</svg>\n',
        encoding="utf-8",
    )
    (XFWM4_DIR / "top-right-active.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="32" viewBox="0 0 10 32">'
        f'<path fill="{bg_act}" d="M0 0A10 10 0 0 1 10 10V32H0Z"/>'
        f'<path fill="none" stroke="{frame_act}" stroke-width="1" d="M0 0.5A9.5 9.5 0 0 1 9.5 10V32"/>'
        f'</svg>\n',
        encoding="utf-8",
    )
    (XFWM4_DIR / "top-right-inactive.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="32" viewBox="0 0 10 32">'
        f'<path fill="{bg_inact}" d="M0 0A10 10 0 0 1 10 10V32H0Z"/>'
        f'<path fill="none" stroke="{frame_inact}" stroke-width="1" d="M0 0.5A9.5 9.5 0 0 1 9.5 10V32"/>'
        f'</svg>\n',
        encoding="utf-8",
    )

    for state, border in (("active", frame_act), ("inactive", frame_inact)):
        for side in ("left", "right"):
            (XFWM4_DIR / f"{side}-{state}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="2"><rect width="1" height="2" fill="{border}"/></svg>\n',
                encoding="utf-8",
            )
        (XFWM4_DIR / f"bottom-{state}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="6"><rect width="2" height="6" fill="{bg_act}"/><path d="M0 5.5H2" stroke="{border}"/></svg>\n',
            encoding="utf-8",
        )
        for side in ("left", "right"):
            transform = "" if side == "left" else ' transform="translate(6 0) scale(-1 1)"'
            (XFWM4_DIR / f"bottom-{side}-{state}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="6" height="6"><g{transform}>'
                f'<path d="M0 0H6V6A6 6 0 0 1 0 0Z" fill="{bg_act}"/>'
                f'<path d="M0.5 0A5.5 5.5 0 0 0 6 5.5" fill="none" stroke="{border}"/></g></svg>\n',
                encoding="utf-8",
            )

    def write_btn(name, path_d, is_close=False):
        (XFWM4_DIR / f"{name}-active.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="32" viewBox="0 0 30 32">'
            f'<rect width="30" height="32" fill="{bg_act}"/>'
            f'<rect width="30" height="1" fill="{frame_act}"/>'
            f'<rect y="31" width="30" height="1" fill="{bot_line}"/>'
            f'<path fill="{fg_act}" d="{path_d}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )
        (XFWM4_DIR / f"{name}-inactive.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="32" viewBox="0 0 30 32">'
            f'<rect width="30" height="32" fill="{bg_inact}"/>'
            f'<rect width="30" height="1" fill="{frame_inact}"/>'
            f'<rect y="31" width="30" height="1" fill="{bg_act}"/>'
            f'<path fill="{fg_inact}" d="{path_d}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )
        hover_bg = accent if is_close else pal["bg_3"]
        hover_fg = sel_fg if is_close else accent
        (XFWM4_DIR / f"{name}-prelight.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="32" viewBox="0 0 30 32">'
            f'<rect width="30" height="32" fill="{bg_act}"/>'
            f'<rect width="30" height="1" fill="{frame_act}"/>'
            f'<rect y="31" width="30" height="1" fill="{bot_line}"/>'
            f'<rect x="5" y="6" width="20" height="20" rx="5" fill="{hover_bg}"/>'
            f'<path fill="{hover_fg}" d="{path_d}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )
        (XFWM4_DIR / f"{name}-pressed.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="32" viewBox="0 0 30 32">'
            f'<rect width="30" height="32" fill="{bg_act}"/>'
            f'<rect width="30" height="1" fill="{frame_act}"/>'
            f'<rect x="5" y="6" width="20" height="20" rx="5" fill="{frame_act}"/>'
            f'<path fill="{fg_act}" d="{path_d}"/>'
            f'</svg>\n',
            encoding="utf-8",
        )

    write_btn("close", "M19.5 12.56L18.44 11.5 15 14.94 11.56 11.5 10.5 12.56 13.94 16 10.5 19.44 11.56 20.5 15 17.06 18.44 20.5 19.5 19.44 16.06 16z", is_close=True)
    write_btn("maximize", "M11 11h3.5v1.5h-2v2H11V11zm8 0v3.5h-1.5v-2h-2V11H19zm-8 10v-3.5h1.5v2h2V21H11zm8 0h-3.5v-1.5h2v-2H19V21z")
    write_btn("maximize-toggled", "M11 11h3.5v1.5h-2v2H11V11zm8 0v3.5h-1.5v-2h-2V11H19zm-8 10v-3.5h1.5v2h2V21H11zm8 0h-3.5v-1.5h2v-2H19V21z")
    write_btn("hide", "m11 16.5h8v1.5h-8z")


def reload_live_desktop():
    # Identical aliases trigger reload without transient font/geometry changes.
    for channel, prop, base in [
        ("xsettings", "/Net/ThemeName", "Blacklight-Ultra"),
        ("xfwm4", "/general/theme", "Blacklight-Ultra-Rounded"),
    ]:
        current = subprocess.check_output(
            ["xfconf-query", "-c", channel, "-p", prop], text=True, timeout=5
        ).strip()
        alias = base + "-Live"
        target = base if current == alias else alias
        subprocess.run(["xfconf-query", "-c", channel, "-p", prop, "-s", target],
                       check=True, timeout=5)


def update_terminal_palette(pal: dict):
    settings = {
        "color-background": pal["bg_0"],
        "color-foreground": pal["fg_hex"],
        "color-bold": pal["accent_hex"],
        "color-cursor": pal["accent_hex"],
        "color-cursor-foreground": pal["bg_0"],
        "color-selection": pal["bg_3"],
        "tab-activity-color": pal["accent_hex"],
    }
    for key, value in settings.items():
        subprocess.run(
            ["xfconf-query", "-c", "xfce4-terminal", "-p", f"/{key}",
             "-n", "-t", "string", "-s", value],
            check=True, timeout=5,
        )



def update_kitty_palette(pal):
    directory = HOME / ".config/kitty"
    if not (directory / "kitty.conf").is_file():
        return
    colors = {
        "background": pal["bg_0"], "foreground": pal["fg_hex"],
        "cursor": pal["accent_hex"], "cursor_text_color": pal["bg_0"],
        "selection_background": pal["bg_3"], "selection_foreground": pal["fg_hex"],
    }
    atomic_write(directory / "colors.conf", "".join(
        f"{name} {value}\n" for name, value in colors.items()
    ))
    # Kitty supports SIGUSR1 for reloading configuration in existing windows.
    subprocess.run(["pkill", "-USR1", "-u", str(os.getuid()), "-x", "kitty"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


def update_labwc_theme(pal):
    theme = HOME / ".local/share/themes/Galinia/openbox-3"
    theme.mkdir(parents=True, exist_ok=True)
    properties = {
        "border.width": "1",
        "window.titlebar.padding.height": "2",
        "window.button.height": "24",
        "window.button.width": "27",
        "window.active.title.bg.color": pal["bg_0"],
        "window.inactive.title.bg.color": pal["bg_0"],
        "window.active.title.bg": "Solid",
        "window.inactive.title.bg": "Solid",
        "window.label.text.justify": "center",
        "window.button.hover.bg.corner-radius": "8",
        "window.active.border.color": pal["bg_3"],
        "window.inactive.border.color": pal["bg_1"],
        "window.active.label.text.color": pal["fg_hex"],
        "window.inactive.label.text.color": pal["fg_hex"],
        "window.active.button.unpressed.image.color": pal["accent_hex"],
        "window.inactive.button.unpressed.image.color": pal["fg_hex"],
    }
    atomic_write(theme / "themerc", "".join(
        f"{key}: {value}\n" for key, value in properties.items()
    ))
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" and os.environ.get("LABWC_PID"):
        subprocess.run(["labwc", "--reconfigure"], check=True, timeout=5)


def sync_now() -> dict:
    wp = get_active_wallpaper()
    pal = extract_palette_from_wallpaper(wp)
    PALETTE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(PALETTE_JSON, json.dumps(pal, indent=2))
    patch_base_gtk_theme(pal)
    write_user_gtk_css(pal)
    update_xfwm4_theme(pal)
    update_labwc_theme(pal)
    update_terminal_palette(pal)
    update_kitty_palette(pal)
    reload_live_desktop()
    print(f"Synced system theme to wallpaper: {wp.name} (mono={pal['is_mono']}, bg={pal['bg_0']}, accent={pal['accent_hex']})", flush=True)
    return pal


def watch_loop():
    Xfconf.init()
    channel = Xfconf.Channel.get("xfce4-desktop")
    pending = [0]
    last = [None]
    mirrored = {}

    def refresh():
        pending[0] = 0
        try:
            wp = get_active_wallpaper()
            signature = (str(wp), wp.stat().st_mtime_ns)
            share_wallpaper(channel, wp, mirrored)
            if signature != last[0]:
                sync_now()
                last[0] = signature
        except Exception as exc:
            print(f"Wallpaper sync failed: {exc}", file=sys.stderr, flush=True)
        return False

    def changed(channel, prop, value):
        if not prop.endswith("/last-image") or not isinstance(value, str) or not Path(value).is_file():
            return
        if mirrored.pop(prop, None) == value:
            return
        if Path(value) != get_active_wallpaper():
            PALETTE_DIR.mkdir(parents=True, exist_ok=True)
            atomic_write(SHARED_WALLPAPER, value + "\n")
        if pending[0]:
            GLib.source_remove(pending[0])
        pending[0] = GLib.timeout_add(350, refresh)

    channel.connect("property-changed", changed)
    refresh()
    GLib.MainLoop().run()


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_loop()
    else:
        sync_now()
