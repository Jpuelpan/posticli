import urwid
import db


def exit_on_q(input):
    if input in ('q', 'Q'):
        raise urwid.ExitMainLoop()

class SelectableText(urwid.Text):
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

class PostcliListBox(urwid.ListBox):
    def keypress(self, size, key):
        exit_on_q(key)

        if key == 'j':
            key = 'down'
        if key == 'k':
            key = 'up'

        super().keypress(size, key)

def get_tables_list():
    return list(map(
        lambda x: urwid.AttrMap(SelectableText(x), '', 'item_active'),
        db.get_table_names()
    ))

# def left_panel():

class LeftPanel(urwid.WidgetWrap):
    def __init__(self, *args, **kw):
        print('AHHH')
        # super(LeftPanel, self).__init__(*args, **kw)
        # self.redraw()

class MainWidget(urwid.WidgetWrap):
    def __init__(self, widgets, **options):
        self.display_widget = urwid.Columns(widgets, **options)
        urwid.WidgetWrap.__init__(self, self.display_widget)

    def keypress(self, size, key):
        # print(self.display_widget.focus)
        if key == 'l':
            self.display_widget.focus_position = 1

        if key == 'h':
            self.display_widget.focus_position = 0

        super().keypress(size, key)

def main():
    title = urwid.Text('Tables')
    line_box = urwid.LineBox(title)

    tableslist = urwid.SimpleListWalker(get_tables_list())
    listbox = PostcliListBox(tableslist)
    # view = urwid.Frame(listbox)

    widgets = [
        listbox,
        listbox,
        listbox,
    ]

    columns = MainWidget(
        widgets,
        dividechars=1,
        focus_column=0
    )

    view = urwid.Frame(columns)
    palette = [
        ('item_active', 'black', 'white', 'standout')
    ]
    loop = urwid.MainLoop(view, palette, unhandled_input=exit_on_q)
    loop.run()


if __name__ == "__main__":
    main()

