# PostiCLI

An attempt to replicate some (https://eggerapps.at/postico/)[Postico] features to the terminal
Reads your `.pgpass` file and list the available PostgreSQL databases for connection

# TODO

- [x] List databases from .pgpass
- [X] Display table contents
- [] Display table schema
- [] Navigate through table rows
- [] Table rows pagination
- [] Expand single row to have a more detailed view
- [] Run SQL Queries

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

