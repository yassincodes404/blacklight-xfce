#include <stdio.h>
#include "resolve-app.c"
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    GDesktopAppInfo *info = _xfw_g_desktop_app_info_get(argv[1]);
    puts(info ? g_app_info_get_id(G_APP_INFO(info)) : "NONE");
    g_clear_object(&info);
    return 0;
}
