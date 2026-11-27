#include "icon-lookup.c"
int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    gchar *dir = g_dir_make_tmp("galinia-pixmaps-XXXXXX", NULL);
    gchar *path = g_build_filename(dir, "galinia-unthemed-fixture.png", NULL);
    GdkPixbuf *pixbuf = gdk_pixbuf_new(GDK_COLORSPACE_RGB, TRUE, 8, 4, 4);
    gdk_pixbuf_fill(pixbuf, 0xff8040ff);
    g_assert(gdk_pixbuf_save(pixbuf, path, "png", NULL, NULL));
    g_object_unref(pixbuf);
    gtk_icon_theme_append_search_path(gtk_icon_theme_get_default(), dir);
    g_assert(!gtk_icon_theme_has_icon(gtk_icon_theme_get_default(), "galinia-unthemed-fixture"));
    GIcon *icon = _xfw_g_icon_new("galinia-unthemed-fixture");
    g_assert(icon != NULL);
    GtkIconInfo *info = gtk_icon_theme_lookup_by_gicon(gtk_icon_theme_get_default(), icon, 48, 0);
    g_assert(info != NULL);
    pixbuf = gtk_icon_info_load_icon(info, NULL);
    g_assert(pixbuf != NULL);
    g_object_unref(pixbuf); g_object_unref(info); g_object_unref(icon);
    icon = _xfw_g_icon_new(path); g_assert(icon != NULL); g_object_unref(icon);
    g_assert(_xfw_g_icon_new("galinia-missing-fixture") == NULL);
    g_assert(_xfw_g_icon_new(NULL) == NULL);
    remove(path); rmdir(dir); g_free(path); g_free(dir);
    return 0;
}
