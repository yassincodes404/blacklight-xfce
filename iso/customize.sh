#!/bin/sh
# Run ONLY inside the Cubic virtual environment of a verified Xubuntu 26.04 amd64 ISO.
set -eu
[ "${GALINIA_IMAGE_BUILD:-}" = 1 ] || { echo 'Set GALINIA_IMAGE_BUILD=1 inside the Cubic virtual environment.' >&2; exit 1; }
[ "$(id -u)" = 0 ] || { echo 'Image customization requires root inside the image environment.' >&2; exit 1; }
. /etc/os-release
[ "$ID" = ubuntu ] && [ "$VERSION_ID" = 26.04 ] && [ "$(dpkg --print-architecture)" = amd64 ] || { echo 'Expected an Ubuntu/Xubuntu 26.04 amd64 image.' >&2; exit 1; }
[ "$#" = 1 ] && [ -f "$1" ] || { echo 'Usage: GALINIA_IMAGE_BUILD=1 sh customize.sh /absolute/path/galinia-defaults.deb' >&2; exit 1; }
case "$1" in /*.deb) ;; *) echo 'Provide an absolute .deb path.' >&2; exit 1;; esac
[ "$(dpkg-deb -f "$1" Package)" = galinia-defaults ] || { echo 'Expected the galinia-defaults package.' >&2; exit 1; }
apt-get update
apt-get --no-remove install "$1"
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/plymouth/themes/galinia/galinia.plymouth 80
update-alternatives --set default.plymouth /usr/share/plymouth/themes/galinia/galinia.plymouth
update-initramfs -u -k all
fc-cache -f
update-desktop-database /usr/share/applications
# The live user is recreated from /etc/skel by Casper. Never export the owner's home.
[ -f /etc/skel/.config/galinia/initialize ]
echo 'Galinia image customization completed. Configure the live boot-menu labels in Cubic, then generate and VM-test the ISO.'
echo 'Installed-system GRUB reads /etc/default/grub.d/90-galinia.cfg; do not run update-grub against the build host disk.'
