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

class CommonListBoxWidget(urwid.ListBox):
    def keypress(self, size, key):
        exit_on_q(key)

        if key == 'j':
            key = 'down'
        if key == 'k':
            key = 'up'

        super().keypress(size, key)

class LeftPanelWidget(urwid.WidgetWrap):
    """
    Creates a list for the current tables of the selected database
    wrapping it in a LineBox
    """
    signals = ['change']

    def __init__(self):
        tableslist = urwid.SimpleListWalker(self.get_tables_list())
        listbox = CommonListBoxWidget(tableslist)

        self.widget = urwid.LineBox(
            listbox,
            title="Tables"
        )

        def changed(**args):
            selected_table, *tail = tableslist.get_focus()[0].base_widget.get_text() 
            urwid.emit_signal(self, 'change', selected_table)

        urwid.connect_signal(tableslist, 'modified', changed)
        urwid.WidgetWrap.__init__(self, self.widget)

    def get_tables_list(self):
        """
        Returns a list of SelectableText widgets with the table names
        from the database
        """
        return list(map(
            lambda x: urwid.AttrMap(SelectableText(x), '', 'item_active'),
            db.get_table_names()
        ))

class RightPanelWidget(urwid.WidgetWrap):
    def __init__(self):
        self.text = urwid.Text('No table selected')

        name_input = urwid.AttrMap(
            SelectableText('Table Name'),
            '',
            'item_active'
        )

        self.items = [
            # urwid.LineBox(name_input),
        ]

        self.listbox = urwid.ListBox(self.items)

        # pile = urwid.Pile([
            # self.table_columns
        # ])

        self.widget = urwid.LineBox(self.listbox) 
        urwid.WidgetWrap.__init__(self, self.widget)

    def on_table_change(self, table_name):
        self.widget.set_title(table_name)
        self.items.clear()
        table_columns = db.get_table_structure(table_name)

        for column in table_columns:
            # self.items.append(urwid.LineBox(urwid.AttrMap(
                # SelectableText(column),
                # '',
                # 'item_active'
            # )))

            self.items.append(urwid.AttrMap(
                SelectableText(column),
                '',
                'item_active'
            ))

            # self.items.append(urwid.Divider(div_char="_", top=1))

        self.listbox.body = self.items

    def keypress(self, size, key):
        super().keypress(size, key)


class MainWidget(urwid.WidgetWrap):
    """
    Initializes a Columns widgets holding the left and right panels
    """

    def __init__(self):
        left_panel = LeftPanelWidget()
        right_panel = RightPanelWidget()

        urwid.connect_signal(left_panel, 'change', right_panel.on_table_change)

        self.widget = urwid.Columns(
            [
                (30, left_panel),
                right_panel
            ],
            focus_column=1
        )

        urwid.WidgetWrap.__init__(self, self.widget)

    def keypress(self, size, key):
        """
        Navigate bwtweeen left and right panes
        """

        # print(key)

        if key == 'right':
            self.widget.focus_position = 1

        if key == 'left':
            self.widget.focus_position = 0

        super().keypress(size, key)

def main():
    palette = [
        ('item_active', 'black', 'white', 'standout'),
        ('normal_text', 'black', 'white', 'standout'),
    ]

    layout = urwid.Frame(MainWidget())
    loop = urwid.MainLoop(layout, palette, unhandled_input=exit_on_q)
    loop.run()

if __name__ == "__main__":
    main()

