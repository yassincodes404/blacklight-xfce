/* Scoped GTK 3 module for xfce4-settings-manager. GPL-2.0-or-later. */
typedef struct GtkWidget GtkWidget;
typedef struct GValue GValue;
typedef struct GSignalInvocationHint GSignalInvocationHint;
typedef unsigned long GType;

/* The small GTK and GObject ABI subset needed by this module. */
extern GType gtk_widget_get_type(void);
extern GType gtk_search_entry_get_type(void);
extern int g_type_check_instance_is_a(void *, GType);
extern unsigned int g_signal_lookup(const char *, GType);
extern void *g_value_get_object(const GValue *);
extern unsigned long g_signal_add_emission_hook(
    unsigned int, unsigned long,
    int (*)(GSignalInvocationHint *, unsigned int, const GValue *, void *),
    void *, void (*)(void *));
extern GtkWidget *gtk_widget_get_parent(GtkWidget *);
extern void gtk_widget_set_halign(GtkWidget *, int);
extern void gtk_widget_set_margin_top(GtkWidget *, int);
extern void gtk_widget_set_margin_bottom(GtkWidget *, int);
extern void gtk_widget_set_margin_end(GtkWidget *, int);
extern void gtk_widget_set_name(GtkWidget *, const char *);
extern void gtk_entry_set_width_chars(void *, int);
extern void gtk_entry_set_placeholder_text(void *, const char *);

static int style_search(GSignalInvocationHint *hint, unsigned int count,
                        const GValue *values, void *data)
{
    (void)hint;
    (void)count;
    (void)data;
    GtkWidget *entry = g_value_get_object(values);
    if (!g_type_check_instance_is_a(entry, gtk_search_entry_get_type()))
        return 1;

    GtkWidget *bar = gtk_widget_get_parent(entry);
    if (!bar)
        return 1;
    enum { GTK_ALIGN_CENTER = 3 };
    gtk_widget_set_halign(bar, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top(bar, 14);
    gtk_widget_set_margin_bottom(bar, 12);
    gtk_widget_set_margin_end(bar, 0);
    gtk_entry_set_width_chars(entry, 34);
    gtk_entry_set_placeholder_text(entry, "Search settings");
    gtk_widget_set_name(entry, "galinia-settings-search");
    return 1;
}

void gtk_module_init(int *argc, char ***argv)
{
    (void)argc;
    (void)argv;
    GType widget = gtk_widget_get_type();
    extern void *g_type_class_ref(GType);
    g_type_class_ref(widget);
    unsigned int signal = g_signal_lookup("map", widget);
    if (signal)
        g_signal_add_emission_hook(signal, 0, style_search, 0, 0);
}
