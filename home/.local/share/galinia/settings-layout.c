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

typedef struct List {
    void *data;
    struct List *next, *prev;
} List;

extern GType g_type_from_name(const char *);
extern GType gtk_cell_renderer_text_get_type(void);
extern void *g_object_get_data(void *, const char *);
extern void g_object_set_data(void *, const char *, void *);
extern void g_object_get(void *, const char *, ...);
extern void g_object_set(void *, const char *, ...);
extern List *gtk_tree_view_get_columns(void *);
extern List *gtk_cell_layout_get_cells(void *);
extern void gtk_tree_view_column_set_title(void *, const char *);
extern void gtk_tree_view_column_set_min_width(void *, int);
extern void gtk_tree_view_column_set_cell_data_func(
    void *, void *, void (*)(void *, void *, void *, void *, void *),
    void *, void (*)(void *));
extern char *g_strndup(const char *, unsigned long);
extern char *g_path_get_basename(const char *);
extern void g_free(void *);
extern void g_list_free(List *);
extern unsigned long strcspn(const char *, const char *);

enum { TASK_NAME, TASK_PID, TASK_MEMORY, TASK_CPU, TASK_OTHER };

static void style_process_cell(void *column, void *cell, void *model,
                               void *iter, void *kind)
{
    (void)column;
    (void)model;
    (void)iter;
    int name = kind == (void *)(long)TASK_NAME;
    g_object_set(cell, "cell-background-set", 0, "foreground-set", 0,
                 "xpad", 10u, "ypad", 2u, "weight", name ? 500 : 400, 0);
    if (name && !g_getenv("GALINIA_TASK_FULL_COMMANDS")) {
        char *text = 0;
        g_object_get(cell, "text", &text, 0);
        if (text && *text) {
            char *executable = g_strndup(text, strcspn(text, " \t"));
            char *short_name = g_path_get_basename(executable);
            g_object_set(cell, "text", short_name, 0);
            g_free(short_name);
            g_free(executable);
        }
        g_free(text);
    } else if (!name) {
        g_object_set(cell, "family", "JetBrains Mono", "size-points", 9.0,
                     "foreground", "#afb5c2", 0);
    }
}

static void style_process_table(GtkWidget *widget)
{
    if (g_object_get_data(widget, "galinia-process-style"))
        return;
    g_object_set_data(widget, "galinia-process-style", widget);
    List *columns = gtk_tree_view_get_columns(widget);
    for (List *item = columns; item; item = item->next) {
        void *column = item->data;
        long id = (long)g_object_get_data(column, "column-id");
        int kind = TASK_OTHER;
        switch (id) {
        case 0: kind = TASK_NAME; gtk_tree_view_column_set_title(column, "Process"); break;
        case 1: kind = TASK_PID; gtk_tree_view_column_set_min_width(column, 84); break;
        case 6: kind = TASK_MEMORY; gtk_tree_view_column_set_title(column, "Memory");
                gtk_tree_view_column_set_min_width(column, 110); break;
        case 9: kind = TASK_CPU; gtk_tree_view_column_set_min_width(column, 80); break;
        }
        List *cells = gtk_cell_layout_get_cells(column);
        for (List *cell = cells; cell; cell = cell->next) {
            if (g_type_check_instance_is_a(cell->data, gtk_cell_renderer_text_get_type()))
                gtk_tree_view_column_set_cell_data_func(
                    column, cell->data, style_process_cell, (void *)(long)kind, 0);
        }
        g_list_free(cells);
    }
    g_list_free(columns);
}

static void style_task_widget(GtkWidget *widget)
{
    GType process_tree = g_type_from_name("XtmProcessTreeView");
    if (process_tree && g_type_check_instance_is_a(widget, process_tree))
        style_process_table(widget);
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
