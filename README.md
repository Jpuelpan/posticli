# PostiCLI

An attempt to replicate some [https://eggerapps.at/postico/](Postico) features to the terminal.

It works by reading your `.pgpass` file listing the available PostgreSQL databases for connection.
Then, with the help of PyGreSQL package it establishes a connection to run queries, such as listing
the database's tables and table contents.

# TODO

- [x] List databases from .pgpass
- [X] Display table contents
- [ ] Display table schema
- [ ] Navigate through table rows
- [ ] Table rows pagination
- [ ] Expand single row to have a more detailed view
- [ ] Run SQL Queries

# Development

**Dependencies:**
  - urwid
  - PyGreSQL
  - pgpasslib

**Installation:**

Install virtualenv and virtualenvwrapper, create a new environment and install dependencies:

```
$ mkvirtualenv --python=/usr/bin/python3 posticli
$ workon posticli
$ pip install -r requirements.txt
```

Run the app with:

```
$ python ./posticli.py
```

To see the logs:

```
$ tail -f debug.log
```


