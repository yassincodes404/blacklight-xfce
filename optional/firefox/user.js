// ============================================================================
// Blacklight-Ultra Monochrome Customization & Balanced Privacy/Security Hardening
// ============================================================================

// --- 1. UI, Theme & Font Preferences ---
user_pref("extensions.activeThemeID", "firefox-compact-dark@mozilla.org");
user_pref("ui.systemUsesDarkTheme", 1);
user_pref("layout.css.prefers-color-scheme.content-override", 0);
user_pref("browser.compactmode.show", true);
user_pref("browser.uidensity", 1); // Compact toolbar density
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true); // Enable userChrome.css & userContent.css
user_pref("svg.context-properties.content.enabled", true);
user_pref("layout.css.color-mix.enabled", true);
user_pref("browser.tabs.inTitlebar", 1);
user_pref("browser.toolbars.bookmarks.visibility", "never");

// Desktop font preference (JetBrains Mono)
user_pref("browser.display.use_document_fonts", 1);
user_pref("font.name.serif.x-western", "JetBrains Mono");
user_pref("font.name.sans-serif.x-western", "JetBrains Mono");
user_pref("font.name.monospace.x-western", "JetBrains Mono");
user_pref("font.name.serif.x-unicode", "JetBrains Mono");
user_pref("font.name.sans-serif.x-unicode", "JetBrains Mono");
user_pref("font.name.monospace.x-unicode", "JetBrains Mono");
user_pref("font.name.serif.x-central-euro", "JetBrains Mono");
user_pref("font.name.sans-serif.x-central-euro", "JetBrains Mono");
user_pref("font.name.monospace.x-central-euro", "JetBrains Mono");
user_pref("font.name.serif.x-cyrillic", "JetBrains Mono");
user_pref("font.name.sans-serif.x-cyrillic", "JetBrains Mono");
user_pref("font.name.monospace.x-cyrillic", "JetBrains Mono");
user_pref("font.name.serif.el", "JetBrains Mono");
user_pref("font.name.sans-serif.el", "JetBrains Mono");
user_pref("font.name.monospace.el", "JetBrains Mono");
user_pref("font.name.serif.tr", "JetBrains Mono");
user_pref("font.name.sans-serif.tr", "JetBrains Mono");
user_pref("font.name.monospace.tr", "JetBrains Mono");
user_pref("font.name.serif.x-baltic", "JetBrains Mono");
user_pref("font.name.sans-serif.x-baltic", "JetBrains Mono");
user_pref("font.name.monospace.x-baltic", "JetBrains Mono");
user_pref("font.name.serif.x-vietnamese", "JetBrains Mono");
user_pref("font.name.sans-serif.x-vietnamese", "JetBrains Mono");
user_pref("font.name.monospace.x-vietnamese", "JetBrains Mono");

// --- 2. Enhanced Tracking Protection (Strict + Total Cookie Protection) ---
user_pref("browser.contentblocking.category", "strict");
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.socialtracking.enabled", true);
user_pref("privacy.trackingprotection.cryptomining.enabled", true);
user_pref("privacy.trackingprotection.fingerprinting.enabled", true);
user_pref("privacy.query_stripping.enabled", true);
user_pref("privacy.query_stripping.enabled.pbmode", true);
user_pref("privacy.partition.network_state.ocsp_cache", true);
user_pref("privacy.globalprivacycontrol.enabled", true);
user_pref("privacy.donottrackheader.enabled", true);
user_pref("network.cookie.sameSite.noneRequiresSecure", true);

// --- 3. HTTPS-Only Mode, DNS-over-HTTPS & Network Hardening ---
user_pref("dom.security.https_only_mode", true);
user_pref("dom.security.https_only_mode_ever_enabled", true);
user_pref("dom.security.https_only_mode_send_http_background_request", false);
user_pref("network.trr.mode", 2); // DNS-over-HTTPS with native fallback
user_pref("network.http.referer.XOriginTrimmingPolicy", 2); // Trim cross-origin referrers to origin
user_pref("network.predictor.enabled", false);
user_pref("network.prefetch-next", false);
user_pref("network.dns.disablePrefetch", true);
user_pref("network.dns.disablePrefetchFromHTTPS", true);
user_pref("network.http.speculative-parallel-limit", 0);
user_pref("browser.urlbar.speculativeConnect.enabled", false);
user_pref("browser.places.speculativeConnect.enabled", false);

// Prevent WebRTC Local IP Leaks while preserving video calls
user_pref("media.peerconnection.ice.default_address_only", true);
user_pref("media.peerconnection.ice.no_host", true);
user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);

// --- 4. Disable Telemetry, Studies, Crash Reports & Data Collection ---
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.server", "data:,");
user_pref("toolkit.telemetry.archive.enabled", false);
user_pref("toolkit.telemetry.newProfilePing.enabled", false);
user_pref("toolkit.telemetry.shutdownPingSender.enabled", false);
user_pref("toolkit.telemetry.updatePing.enabled", false);
user_pref("toolkit.telemetry.bhrPing.enabled", false);
user_pref("toolkit.telemetry.firstShutdownPing.enabled", false);
user_pref("toolkit.telemetry.coverage.opt-out", true);
user_pref("toolkit.coverage.opt-out", true);
user_pref("toolkit.coverage.endpoint.base", "");
user_pref("app.shield.optoutstudies.enabled", false);
user_pref("app.normandy.enabled", false);
user_pref("app.normandy.api_url", "");
user_pref("breakpad.reportURL", "");
user_pref("browser.tabs.crashReporting.sendReport", false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
user_pref("beacon.enabled", false);

// --- 5. Remove Pocket, Sponsored Bloat & Promotional Clutter ---
user_pref("extensions.pocket.enabled", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
user_pref("browser.newtabpage.activity-stream.telemetry", false);
user_pref("browser.newtabpage.activity-stream.section.highlights.includePocket", false);
user_pref("browser.urlbar.suggest.quicksuggest.sponsored", false);
user_pref("browser.urlbar.suggest.quicksuggest.nonsponsored", false);
user_pref("browser.urlbar.suggest.pocket", false);
user_pref("browser.vpn_promo.enabled", false);
user_pref("browser.promo.focus.enabled", false);
user_pref("extensions.htmlaboutaddons.recommendations.enabled", false);
user_pref("browser.discovery.enabled", false);
user_pref("browser.MessagingSystem.whatsNewPanel.enabled", false);
user_pref("browser.uitour.enabled", false);

// --- 6. Security Hardening (TLS, Punycode Phishing Protection, PDF JS) ---
user_pref("security.ssl.require_safe_negotiation", true);
user_pref("security.tls.enable_0rtt_data", false);
user_pref("security.OCSP.enabled", 1);
user_pref("network.IDN_show_punycode", true); // Prevent homograph spoofing attacks
user_pref("pdfjs.enableScripting", false); // Block malicious JS in PDFs
user_pref("dom.disable_window_move_resize", true);
user_pref("browser.safebrowsing.downloads.remote.enabled", false); // Keep file hashes private

// --- 7. GPU Hardware Acceleration (NVIDIA RTX 2060 SUPER) ---
user_pref("media.hardware-video-decoding.enabled", true);

// Managed workstation security settings (2026-11-15)
user_pref("browser.cache.disk.smart_size.enabled", false);
user_pref("browser.cache.disk.capacity", 262144);
user_pref("browser.cache.memory.capacity", 65536);
user_pref("dom.quotaManager.temporaryStorage.fixedLimit", 1048576);
user_pref("permissions.default.persistent-storage", 2);
user_pref("permissions.default.desktop-notification", 2);
user_pref("permissions.default.geo", 2);
user_pref("permissions.default.camera", 2);
user_pref("permissions.default.microphone", 2);
user_pref("network.protocol-handler.external-default", false);
user_pref("browser.safebrowsing.malware.enabled", true);
user_pref("browser.safebrowsing.phishing.enabled", true);
user_pref("browser.safebrowsing.downloads.enabled", true);
user_pref("dom.security.https_only_mode", true);
user_pref("fission.autostart", true);
user_pref("security.fileuri.strict_origin_policy", true);
user_pref("browser.download.useDownloadDir", false);

// Use selected-file grants with restricted Snap home access.
user_pref("widget.use-xdg-desktop-portal.file-picker", 1);
