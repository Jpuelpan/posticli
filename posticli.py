#!/usr/bin/env python

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

config = {
  'PAGE_LIMIT': 100
}

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
    signals = [
        'changed_table', 'search_start',
        'search_end', 'search_term'
    ]

    def __init__(self, connection, **args):
        self.connection = connection
        self.tables = []
        self.searching = False
        self.search_term = ''

        self.tableslist = urwid.SimpleListWalker(self.get_tables_list())
        listbox = CommonListBoxWidget(self.tableslist)

        self.widget = urwid.LineBox(
            listbox,
            title="Tables"
        )

        def changed(**args):
            selected_table = self.tableslist.get_focus()[0].base_widget.value
            urwid.emit_signal(self, 'changed_table', selected_table)

        urwid.connect_signal(self.tableslist, 'modified', changed)
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

    def filter_tables(self):
        """
        Search the *self.search_term* on the current tables list
        and highlights the matched items
        """
        logging.debug('Filtering tables with %s' % self.search_term)

        for idx, table_name in enumerate(self.tables):
            if self.search_term and self.search_term in table_name:
                self.tableslist[idx].set_attr_map({ None: 'item_highlight' })
            else:
                self.tableslist[idx].set_attr_map({ 'item_highlight': None })

    def keypress(self, size, key):
        if not self.searching and key == '/':
            logging.debug('Search tables enabled')
            self.searching = True
            urwid.emit_signal(self, 'search_start')
            return

        if self.searching and key == 'esc':
            logging.debug('Search tables disabled')
            self.searching = False
            self.search_term = ''
            urwid.emit_signal(self, 'search_end')

        if self.searching:
            if key == 'backspace':
                self.search_term = self.search_term[0:-1]
            elif key == 'enter':
                pass
            else:
                self.search_term = self.search_term + key

            self.filter_tables()
            urwid.emit_signal(self, 'search_term', self.search_term)

        else:
            super().keypress(size, key)


class TableSchemaWidget(urwid.WidgetWrap):
    def __init__(self, connection, table_name):
        self.widget = urwid.Text('AA')

        # self.items.clear()
        # table_columns = []

        # try:
            # table_columns = self.connection.get_attnames(table_name)
        # except:
            # pass

        # for column in table_columns:
            # # self.items.append(urwid.LineBox(urwid.AttrMap(
                # # SelectableText(column),
                # # '',
                # # 'item_active'
            # # )))

            # self.items.append(urwid.AttrMap(
                # SelectableText(column),
                # '',
                # 'item_active'
            # ))

            # # self.items.append(urwid.Divider(div_char="_", top=1))

        # self.listbox.body = self.items
        urwid.WidgetWrap.__init__(self, self.widget)

class TableContentsWidget(urwid.WidgetWrap):
    total_rows = 0
    current_rows = 0
    rows_limit = config.get('PAGE_LIMIT', 100)

    def __init__(self, connection, table_name = None):
        self.connection = connection
        self.table_name = table_name
        self.column_names = []

        logging.debug('Building data rows for table %s' % table_name)

        self.data_rows = self.get_table_rows()
        self.listbox = urwid.ListBox(self.data_rows)

        urwid.WidgetWrap.__init__(self, self.listbox)

    def get_table_rows(self):
        rows = []

        if not self.table_name:
            return rows

        try:
            escaped_name = self.connection.escape_identifier(self.table_name)
            self.column_names = self.connection.get_attnames(self.table_name)

            count_sql = "SELECT COUNT(*) FROM %s" % escaped_name
            logging.debug(count_sql)

            self.total_rows = self.connection.query(count_sql).getresult()[0][0]

            data = self.connection.get_as_list(
                escaped_name,
                limit=self.rows_limit
            )

            self.current_rows = len(data)

            # Generate headers
            headers = []
            for column_name in self.column_names:
                headers.append(
                    urwid.AttrMap(urwid.Text(column_name, wrap="clip"), '', 'item_active')
                )

            rows.append(urwid.Columns(headers, dividechars=1))

            for row in data:
                columns = []

                for column_name in self.column_names:
                    value = getattr(row, column_name) or ''

                    columns.append(
                        urwid.AttrMap(
                            SelectableText(str(value), wrap="clip"),
                            '',
                            'tem_active'
                        )
                    )

                rows.append(urwid.Columns(columns, dividechars=1))

        except Exception as e:
            logging.error(e)

        return rows

class RightPanelWidget(urwid.WidgetWrap):
    def __init__(self, connection, **args):
        self.connection = connection
        self.view = 'Contents'
        self._cached_tables = {}
        self.footer_status = args['footer_status']

        table_contents = TableContentsWidget(connection, None)

        self.widget = urwid.WidgetPlaceholder(
            urwid.LineBox(table_contents, title="No table selected")
        )

        urwid.WidgetWrap.__init__(self, self.widget)

    def on_table_change(self, table_name):
        logging.debug('Changed table to %s' % table_name)
        cached_item = self._cached_tables.get(table_name, None)
        rows_counter = ''

        if cached_item:
            logging.debug('Found cached table contents %s' % table_name)
            self.widget.original_widget = cached_item

            rows_counter = self.build_status_text(
                cached_item.original_widget.current_rows,
                cached_item.original_widget.total_rows
            )
        else:
            logging.debug('No cached table content found for %s' % table_name)

            title = table_name + " [" + self.view + "]"
            table_contents = TableContentsWidget(self.connection, table_name)
            logging.debug(table_contents.total_rows)

            contents_wrap = urwid.LineBox(
                TableContentsWidget(self.connection, table_name),
                title=title
            )

            rows_counter = self.build_status_text(
                table_contents.current_rows,
                table_contents.total_rows
            )

            self._cached_tables[table_name] = contents_wrap
            self.widget.original_widget = contents_wrap

        self.footer_status.set_text(rows_counter)

    def build_status_text(self, current_rows, table_rows):
        return ('%s of %s total rows' %
            (
                format(current_rows, ',d'),
                format(table_rows, ',d')
            )
        )

    def keypress(self, size, key):
        super().keypress(size, key)

class DatabaseExplorerWidget(urwid.WidgetWrap):
    def __init__(self, connection):
        logging.debug('Initializing application widgets...')
        self.footer_status = urwid.Text('')
        self._cached_footer_status = ''
        self.searching = False

        left_panel = LeftPanelWidget(
            connection,
            footer_status=self.footer_status
        )

        right_panel = RightPanelWidget(
            connection,
            footer_status=self.footer_status
        )

        urwid.connect_signal(left_panel, 'changed_table', right_panel.on_table_change)
        urwid.connect_signal(left_panel, 'search_start', self.on_search_start)
        urwid.connect_signal(left_panel, 'search_end', self.on_search_end)
        urwid.connect_signal(left_panel, 'search_term', self.on_search_term)

        left_panel.initial_focus()

        self.columns = urwid.Columns(
            [
                (30, left_panel),
                right_panel
            ],
            focus_column=0
        )

        self.connection_status = urwid.Text(
            connection.user + "@" +
            connection.host + "/" +
            connection.dbname,
            align='center'
        )

        header = urwid.Columns([
             urwid.AttrMap(self.connection_status, 'header', ''),
        ])

        self.footer = urwid.Columns([
             urwid.AttrMap(urwid.Padding(self.footer_status, left=1), 'footer', ''),
        ])

        self.widget = urwid.Frame(
            self.columns,
            header=header,
            footer=self.footer
        )

        urwid.WidgetWrap.__init__(self, self.widget)

    def on_search_start(self):
        logging.debug('Start searching')
        self.searching = True
        self._cached_footer_status = self.footer_status.get_text()[0]
        self.footer_status.set_text('/')

    def on_search_end(self):
        logging.debug('Stop searching')
        self.searching = False
        self.footer_status.set_text(self._cached_footer_status)
        self._cached_footer_status = ''

    def on_search_term(self, term):
        self.footer_status.set_text("/" + term)

    def keypress(self, size, key):
        """
        Navigate bwtweeen left and right panes
        """
        if not self.searching:
            exit_on_q(key)

            if key == 'right':
                self.columns.focus_position = 1

            if key == 'left':
                self.columns.focus_position = 0

            super().keypress(size, key)

        else:
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
        ('item_highlight', 'black', 'yellow', 'standout'),
        ('normal_text', 'black', 'white', 'standout'),
        ('footer', 'black', 'dark cyan', 'standout'),
        ('footer_error', 'white', 'dark red', 'standout'),
        ('header', '', 'dark blue', 'standout'),
    ]

    logging.debug('Initializing PosticliApp')

    layout = PosticliApp()
    loop = urwid.MainLoop(layout, palette, unhandled_input=exit_on_q)
    loop.run()

if __name__ == "__main__":
    main()

