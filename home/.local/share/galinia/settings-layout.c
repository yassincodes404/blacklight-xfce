/* Scoped GTK 3 module for Galinia’s XFCE utilities. GPL-2.0-or-later. */
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

extern const char *g_getenv(const char *);
extern int g_strcmp0(const char *, const char *);
extern const char *gtk_buildable_get_name(void *);
extern void gtk_widget_set_no_show_all(GtkWidget *, int);
extern void gtk_widget_hide(GtkWidget *);
extern void gtk_paned_set_position(void *, int);
extern void gtk_alignment_set(void *, float, float, float, float);
extern void *g_object_ref(void *);
extern void g_object_unref(void *);
extern unsigned int g_idle_add(int (*)(void *), void *);

static int hide_graph(void *widget)
{
    gtk_widget_set_no_show_all(widget, 1);
    gtk_widget_hide(widget);
    GtkWidget *summary = gtk_widget_get_parent(widget);
    GtkWidget *paned = summary ? gtk_widget_get_parent(summary) : 0;
    if (paned && g_strcmp0(gtk_buildable_get_name(paned), "mainview-vpaned") == 0)
        gtk_paned_set_position(paned, 34);
    g_object_unref(widget);
    return 0;
}

static void style_task_widget(GtkWidget *widget)
{
    const char *id = gtk_buildable_get_name(widget);
    if (g_strcmp0(id, "graph-hbox") == 0) {
        /* Defer until GTK has finished mapping this widget. */
        g_idle_add(hide_graph, g_object_ref(widget));
    } else if (g_strcmp0(id, "filter-entry") == 0) {
        GtkWidget *alignment = gtk_widget_get_parent(widget);
        if (alignment)
            gtk_alignment_set(alignment, 0.5f, 0.5f, 0.82f, 0.0f);
        gtk_entry_set_placeholder_text(widget, "Find a process…");
    } else if (g_strcmp0(id, "filter-searchbar") == 0) {
        gtk_widget_set_name(widget, "galinia-task-toolbar");
    } else if (g_strcmp0(id, "graph-vbox") == 0) {
        gtk_widget_set_name(widget, "galinia-task-summary");
    }
}

static int style_search(GSignalInvocationHint *hint, unsigned int count,
                        const GValue *values, void *data)
{
    (void)hint;
    (void)count;
    (void)data;
    GtkWidget *entry = g_value_get_object(values);
    if (g_getenv("GALINIA_TASK_LAYOUT")) {
        style_task_widget(entry);
        return 1;
    }
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
