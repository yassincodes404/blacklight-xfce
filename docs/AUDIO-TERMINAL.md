# Terminal and desktop audio

Kitty ships a pinned MIT-licensed Catppuccin Mocha theme with JetBrains Mono,
a pure black background, 12-pixel padding and a bottom powerline tab bar when multiple tabs are open.
The fixed-theme comment in kitty.conf opts it out of wallpaper palette updates.
Existing terminal windows reload with Kitty's supported SIGUSR1 mechanism.
The previous live config is backed up before replacement. Fresh profiles select Kitty as the preferred terminal, matching the reference
desktop. XFCE Terminal remains installed as a fallback. Shell startup files,
prompts and history are not changed.

The desktop sound/music card is fixed at the primary monitor's bottom-right
work area. It has no pointer-motion or drag handler. Its transparent surface and light text match the system monitor, while record
artwork, compact controls and a thin playback line follow the requested reference.
Use Control Center → Appearance to hide/show it. Session startup respects that
preference. Sound settings opens the maintained pavucontrol application.

The card listens for MPRIS player metadata and playback changes on the session
bus. It prefers a playing player, supports previous/play-pause/next where the
player exposes those capabilities, and displays elapsed/total time when
provided. The progress line is a readout, not a seek control. Browser/media
support depends on the app exposing MPRIS; the card does not capture audio.

Volume and mute use WirePlumber's default output, with PulseAudio-compatible
events supplied by PipeWire/pactl. Volume writes are debounced and the slider
is capped at 100%; already-boosted volume is displayed without silently changing
it. Microphone volume is intentionally separate in the normal sound settings.

A 48-frame, small record animation is prepared on demand and capped near
12 frames per second while music plays. Pause stops its timer. Fully obscured
X11 windows also stop the animation where visibility notifications are provided.
Playback readouts update once per twelve frames, using monotonic time and
MPRIS position/seek events. Paused/idle operation is event-driven. There is no
web view, remote album-art download, waveform capture or visualizer process.
GTK still has a measurable memory cost; this is not a zero-RAM feature.
The standalone card can be stopped with:

```sh
systemctl --user stop galinia-audio.service
```

Disable its checkbox in Control Center to keep it off at the next login.
