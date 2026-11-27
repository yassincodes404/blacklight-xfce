/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Galinia's fallback desktop-entry resolution for libxfce4windowing 4.20.5.
 * No polling, icon artwork, window renaming or application-specific icon table.
 */
#include <gio/gdesktopappinfo.h>
#include <string.h>

static GDesktopAppInfo *
galinia_exact_desktop(const gchar *app_id) {
    GDesktopAppInfo *info = NULL;
    if (app_id != NULL && *app_id != '\0' && strchr(app_id, '/') == NULL) {
        gchar *id = g_strconcat(app_id, ".desktop", NULL);
        info = g_desktop_app_info_new(id);
        g_free(id);
        if (info == NULL) {
            gchar *lower = g_ascii_strdown(app_id, -1);
            id = g_strconcat(lower, ".desktop", NULL);
            info = g_desktop_app_info_new(id);
            g_free(id);
            g_free(lower);
        }
    }
    return info;
}

GDesktopAppInfo *
_xfw_g_desktop_app_info_get(const gchar *app_id) {
    GDesktopAppInfo *info;
    GList *apps;
    gboolean ambiguous = FALSE;
    if (app_id == NULL || *app_id == '\0') {
        return NULL;
    }
    info = galinia_exact_desktop(app_id);
    if (info != NULL) {
        return info;
    }
    /* StartupWMClass is explicit desktop metadata, not indexed by GIO's
     * name/keyword search. Accept a unique exact match only. */
    apps = g_app_info_get_all();
    for (GList *item = apps; item != NULL; item = item->next) {
        if (G_IS_DESKTOP_APP_INFO(item->data)
            && g_strcmp0(g_desktop_app_info_get_startup_wm_class(item->data), app_id) == 0) {
            if (info != NULL) {
                g_clear_object(&info);
                ambiguous = TRUE;
                break;
            }
            info = g_object_ref(item->data);
        }
    }
    g_list_free_full(apps, g_object_unref);
    if (info != NULL || ambiguous) {
        return info;
    }
    /* Some XWayland clients append an absolute profile directory to their
     * instance name. Use the prefix only when it names an installed entry. */
    const gchar *profile = strstr(app_id, " (/");
    if (profile != NULL && g_str_has_suffix(app_id, ")")) {
        gchar *base = g_strndup(app_id, profile - app_id);
        info = galinia_exact_desktop(base);
        g_free(base);
        if (info != NULL) {
            return info;
        }
    }
    /* Retain the upstream name/keyword fallback for other applications. */
    gchar ***ids = g_desktop_app_info_search(app_id);
    if (ids != NULL && ids[0] != NULL) {
        info = g_desktop_app_info_new(ids[0][0]);
    }
    if (ids != NULL) {
        for (gchar ***row = ids; *row != NULL; row++) {
            g_strfreev(*row);
        }
        g_free(ids);
    }
    return info;
}
