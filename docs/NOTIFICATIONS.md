# Galinia notification settings

Open Galinia Control Center (Super+S), then Notifications. The Desktop page's
Notifications tile leads to the same page. The controls use the existing
xfce4-notifyd Xfconf channel, so changes from the panel and native XFCE settings
are reflected while the page is open. There is no additional notification daemon
or copied preference store.

The page provides Do Not Disturb, hardware indicators during focus mode, six
popup positions, monitor selection, automatic dismissal, duration, app timeout
overrides, fade-out, optional history and its entry limit. Critical alerts retain
XFCE's urgency behavior. Per-app exceptions and history review/clearing stay in
the native dialog reached through Manage apps and history.

Sound availability is checked through the notification service's capabilities.
The reference Ubuntu package does not advertise sound support, so the sound
control is disabled and explained instead of presenting a setting that has no
effect. Applications may still produce audio independently.

Fresh Galinia defaults select the Galinia popup theme, 8-second default duration,
98% opacity, fade without sliding, and a 320-pixel minimum width. Apps retain
permission to request their own timeout. History is off by default; when enabled
its default cap is 100 entries. Turning history off does not delete existing
records. Enabling history through Galinia first enables the native size limit.

On the existing reference account, new defaults were added only for unset
properties, apart from selecting the new Galinia theme. Existing Do Not Disturb,
muted applications and per-app exceptions were preserved. Prior managed files
and notification properties were backed up in the private directory
~/.local/state/galinia/notification-repairs before application.

Popup CSS is generated with the desktop accent. The Galinia/Galinia-Live aliases
refresh notifyd's cached provider after palette changes, without taking over a
custom notification theme selected in XFCE settings. The native provider is
attached to Galinia's graphical session target and still starts on demand.

The main panel's hover, pressed, toggled and keyboard-focus button backgrounds
are transparent for both task icons and right-side controls. A thin accent line
indicates checked or focused controls; popup menus retain their normal readable
surface.

Verification: six typed-backend tests, the full repository suite, isolated GTK
page rendering, native DND-to-UI synchronization, no preference writes on page
opening, native CSS parsing, a real notification preview, and defaults package
construction. X11-specific presentation still needs a session test; the live
visual checks used Wayland.

Upstream settings reference:
https://github.com/xfce-mirror/xfce4-notifyd/blob/xfce4-notifyd-0.9.7/common/xfce-notify-common.h
