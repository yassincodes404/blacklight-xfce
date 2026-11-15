# Security and scope

This project customizes an XFCE desktop. It does not turn X11 into an isolated security boundary, encrypt disks or secure firmware. Optional Firefox policies are explicit opt-ins and may affect local development, calls and downloads. User services run as the desktop user, with privilege-escalation restrictions; the FUSE/Drive and Tailscale account state is not distributed.

Do not publish credentials in issues or pull requests. Report a sensitive vulnerability using GitHub's private reporting feature if it is enabled; otherwise contact the maintainer through their public profile to arrange a private channel. Provide a minimal reproduction without real secrets.
