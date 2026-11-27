/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <gtk/gtk.h>

GIcon *
_xfw_g_icon_new(const gchar *icon_name) {
    if (icon_name != NULL) {
        /* has_icon() excludes unthemed icons in standard pixmaps directories.
         * Use GTK's actual lookup path, which also supports those icons. */
        GtkIconInfo *info = gtk_icon_theme_lookup_icon(gtk_icon_theme_get_default(),
                                                      icon_name, 48, 0);
        if (info != NULL) {
            g_object_unref(info);
            return g_themed_icon_new(icon_name);
        } else if (g_path_is_absolute(icon_name)
                   && g_file_test(icon_name, G_FILE_TEST_IS_REGULAR)) {
            GFile *file = g_file_new_for_path(icon_name);
            GIcon *icon = g_file_icon_new(file);
            g_object_unref(file);
            return icon;
        }
    }
    return NULL;
}
