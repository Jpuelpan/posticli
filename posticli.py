import urwid
import pgpasslib
import logging

from pg import DB

logging.basicConfig(
    level=logging.DEBUG,
    filename="debug.log",
    filemode='a',
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)

def exit_on_q(input):
    if input in ('q', 'Q'):
        raise urwid.ExitMainLoop()

class SelectableText(urwid.WidgetWrap):
    """
    Generates a Text widget that accepts a *value* argument that will be
    returned on the *chosen* signal callback. If no value is given
    *None* will be returned

    To trigger the *chosen* signal, the enter key must be pressed.
    """
    signals = ['chosen']

    def __init__(self, text, **args):
        self.value = args.get('value', None)

        if self.value:
            del args['value'] 

        self.widget = urwid.Text(text, **args)
        urwid.WidgetWrap.__init__(self, self.widget)

    def selectable(self):
        return True

    def keypress(self, size, key):
        # logging.debug('Pressed key %s on %s' % (key, self))

        if key == 'enter':
            urwid.emit_signal(self, 'chosen', self.value)

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
    signals = ['changed_table']

    def __init__(self, connection):
        self.connection = connection
        self.tables = []

        tableslist = urwid.SimpleListWalker(self.get_tables_list())
        listbox = CommonListBoxWidget(tableslist)

        self.widget = urwid.LineBox(
            listbox,
            title="Tables"
        )

        def changed(**args):
            selected_table = tableslist.get_focus()[0].base_widget.value
            urwid.emit_signal(self, 'changed_table', selected_table)

        urwid.connect_signal(tableslist, 'modified', changed)
        urwid.WidgetWrap.__init__(self, self.widget)

    def get_tables_list(self):
        """
        Returns a list of SelectableText widgets with the table names
        from the database
        """

        self.tables = list(map(
            lambda x: x.split('.')[1].replace('"', ''),
            self.connection.get_tables()
        ))

        return list(map(
            lambda x: urwid.AttrMap(
                SelectableText(x, value=x), '', 'item_active'
            ),
            self.tables
        ))

    def initial_focus(self):
        if self.tables:
            urwid.emit_signal(self, 'changed_table', self.tables[0])

class RightPanelWidget(urwid.WidgetWrap):
    def __init__(self, connection):
        self.connection = connection
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
        logging.debug('Changed table %s' % table_name)
        self.widget.set_title(table_name)
        self.items.clear()

        table_columns = []

        try:
            table_columns = self.connection.get_attnames(table_name)
        except:
            pass

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

class DatabaseExplorerWidget(urwid.WidgetWrap):
    def __init__(self, connection):
        logging.debug('Initializing application widgets...')

        left_panel = LeftPanelWidget(connection)
        right_panel = RightPanelWidget(connection)

        urwid.connect_signal(left_panel, 'changed_table', right_panel.on_table_change)
        left_panel.initial_focus()

        self.columns = urwid.Columns(
            [
                (30, left_panel),
                right_panel
            ],
            focus_column=0
        )

        self.status_text = urwid.Text('AAAHHHH')
        self.connection_status = urwid.Text(
            connection.user + "@" +
            connection.host + "/" +
            connection.dbname,
            align='right'
        )

        footer = urwid.Columns([
             urwid.AttrMap(urwid.Padding(self.status_text, left=1), 'footer', ''),
             urwid.AttrMap(urwid.Padding(self.connection_status, right=1), 'footer', ''),
        ])

        self.widget = urwid.Frame(
            self.columns,
            footer=footer
        )

        urwid.WidgetWrap.__init__(self, self.widget)

    def keypress(self, size, key):
        """
        Navigate bwtweeen left and right panes
        """
        exit_on_q(key)

        if key == 'right':
            self.columns.focus_position = 1

        if key == 'left':
            self.columns.focus_position = 0

        super().keypress(size, key)

class DatabasesListWidget(urwid.WidgetWrap):
    """
    Displays a list of databases read from .pgpass file using
    pgpasslib package. Updates the frame's footer with the connection
    status and triggers a 'connected' signal for successfull connections.
    """
    signals = ['connected']

    def __init__(self):
        logging.debug('Databases widget init...')

        self.status_text = urwid.Text("")
        self.items = self.get_databases_list()
        tableslist = urwid.SimpleListWalker(self.items)

        self.listbox = CommonListBoxWidget(tableslist)
        self.container = urwid.LineBox(self.listbox, title='Databases') 
        self.footer = urwid.AttrMap(urwid.Padding(self.status_text, left=1), 'footer', '')

        self.widget = urwid.Frame(
            self.container,
            footer=self.footer
        )

        urwid.WidgetWrap.__init__(self, self.widget)

    def on_chose(self, entry):
        """
        Tries to connect to the given database entry selected from
        the SelectableText widget. The entry argument is an Entry object
        from the pgpasslib.
        """
        logging.info('Connecting to database...')
        self.status_text.set_text('Connecting to database %s...' % entry.dbname)
        self.footer.set_attr_map({ None: 'footer' })

        try:
            connection = DB(
                dbname=entry.dbname,
                host=entry.host,
                port=entry.port,
                user=entry.user,
                passwd=entry.password
            )

            logging.info('Connected to databse %s' % entry.dbname)
            urwid.emit_signal(self, 'connected', connection)

        except Exception as e:
            logging.error(str(e).strip())
            self.status_text.set_text(str(e).strip())
            self.footer.set_attr_map({ None: 'footer_error' })

    def get_databases_list(self):
        """
        Generates a list SelectableText widgets wrapped in Padding and AttrMap.
        This will feed a SimpleListWalker widget listing all databases.
        """
        logging.debug('Reading .pgpass file')
        entries = pgpasslib._get_entries()
        logging.debug('Found %s database entries on .pgpass' % str(len(entries)))

        databases = []
        databases.append( urwid.Divider("-") )

        for entry in entries:
            text = SelectableText(
                "Name: " + entry.dbname + "\n" +
                "Host: " + entry.host + ":" + str(entry.port) + "\n" +
                "User: " + entry.user,
                value=entry
            )

            urwid.connect_signal(text, 'chosen', self.on_chose)

            padding = urwid.Padding(text, left=1)
            databases.append( urwid.AttrMap(padding, '', 'item_active') )
            databases.append( urwid.Divider("-") )

        self.status_text.set_text(str(len(entries)) + " databases found on .pgpass")

        return databases

    def keypress(self, size, key):
        super().keypress(size, key)

class PosticliApp(urwid.WidgetWrap):
    """
    Starts home widget with the databases list from the current user .pgpass file
    Listens for a successfull connection and change placeholder widget
    with a columns widget listing database tables on the left
    and table contents on the right
    """

    def __init__(self):
        databases_list = DatabasesListWidget()
        self.widget = urwid.WidgetPlaceholder(databases_list)

        urwid.connect_signal(databases_list, 'connected', self.on_connected)
        urwid.WidgetWrap.__init__(self, self.widget)

    def on_connected(self, connection):
        """
        Callback for a successfull connection
        triggered from the DatabasesListWidget
        """
        self.widget.original_widget = DatabaseExplorerWidget(connection)

def main():
    palette = [
        ('item_active', 'black', 'white', 'standout'),
        ('normal_text', 'black', 'white', 'standout'),
        ('footer', 'black', 'dark cyan', 'standout'),
        ('footer_error', 'white', 'dark red', 'standout'),
    ]

    logging.debug('Initializing PosticliApp')

    layout = PosticliApp()
    loop = urwid.MainLoop(layout, palette, unhandled_input=exit_on_q)
    loop.run()

if __name__ == "__main__":
    main()

