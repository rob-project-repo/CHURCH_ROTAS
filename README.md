# Sunday Rota Webapp

A lightweight church rota webapp for managing Sunday ministry rotas with shared SQLite storage.

This project is intentionally simple:
- Python backend using the standard library HTTP server
- SQLite database stored in the project folder
- Plain HTML, CSS, and JavaScript frontend with no build step

That means you can run it and edit it without installing Node, npm, or a frontend toolchain.

## What the app does

- Manage a reusable people bank
- Add Sundays manually
- Assign people to fixed ministry roles for each Sunday
- Highlight same-Sunday clashes in red
- Prevent duplicate same-Sunday assignments from being saved

## Roles and slot limits

- `Band`: 4 people
- `AV`: 2 people
- `Tea and Coffee`: 2 people
- `Youth`: 2 people
- `Children's Church`: 2 people
- `Welcomers`: 2 people

## Tech stack

- Python `3.13` was used in this environment
- SQLite for persistence
- Standard library `http.server` for the web server
- Browser-based frontend in `static/`
- `unittest` for tests

## Project structure

```text
CHURCH_ROTAS/
|-- app.py
|-- rota.db
|-- README.md
|-- .gitignore
|-- static/
|   |-- index.html
|   |-- styles.css
|   `-- app.js
`-- tests/
    `-- test_app.py
```

## Prerequisites

Install these on the machine where you want to run or edit the app:

- Python 3.11 or newer
- Git, if you want to commit and push changes
- A code editor

Recommended editor options:
- VS Code
- PyCharm
- Cursor
- Any editor that can work with Python, HTML, CSS, and JavaScript

## First-time setup for editing

### 1. Open the project folder

Open a terminal in:

```text
c:\Users\rjgil\OneDrive\Documents\PROJECTS\CHURCH_ROTAS
```

### 2. Check Python

Run:

```bash
python --version
```

If that does not work, try:

```bash
py --version
```

### 3. Create a virtual environment

This app does not currently need third-party Python packages, but a virtual environment is still a good habit for future edits.

Windows PowerShell:

```bash
python -m venv .venv
```

Activate it:

```bash
.\.venv\Scripts\Activate.ps1
```

If your machine uses the `py` launcher instead of `python`:

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

When activated, your terminal usually shows `(.venv)` at the start of the prompt.

### 4. Open the code in your editor

If using VS Code and the `code` command is installed:

```bash
code .
```

Inside the editor:
- open `app.py` for backend and database logic
- open `static/app.js` for frontend behavior
- open `static/styles.css` for styling
- open `static/index.html` for page structure

## Running the app locally

Start the server:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

The server binds to `0.0.0.0:8000`, so it can also be reached from other machines on the same network if your firewall allows it.

To stop the server, press `Ctrl+C` in the terminal.

## Running tests

Run:

```bash
python -m unittest discover -s tests
```

What the tests currently cover:
- creating and listing people
- rejecting non-Sunday dates
- saving assignments
- rejecting clashes
- rejecting inactive people in assignments
- deleting Sundays cleanly

## How data is stored

The app stores its data in:

- [rota.db](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/rota.db)

That file contains:
- `people`
- `sundays`
- `assignments`

If you close the app and run it again later, the data remains in `rota.db`.

## Dummy database note

The current repository includes a blank `rota.db` with the required schema so the project can be committed with an example database file.

If you want a fresh blank database later, you can:
- delete `rota.db`, then run `python app.py`
- or overwrite it with a new SQLite file using the same schema in `app.py`

## How the code is organized

### Backend

The backend lives in [app.py](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/app.py).

Main responsibilities:
- create the database schema if needed
- validate people, Sundays, and assignments
- expose HTTP endpoints
- serve the frontend files from `static/`

Important sections:
- `ROLE_LIMITS` and `ROLE_LABELS`: ministry definitions
- `RotaRepository`: all database reads and writes
- `RotaRequestHandler`: HTTP routes and JSON responses
- `run_server()`: starts the app

### Frontend

The frontend lives in `static/`.

- [static/index.html](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/static/index.html): layout and main UI containers
- [static/styles.css](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/static/styles.css): look and responsive layout
- [static/app.js](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/static/app.js): data loading, form handling, clash detection, and saving

### Tests

The tests live in [tests/test_app.py](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/tests/test_app.py).

These focus on repository and rule behavior, which is where most of the important rota logic lives.

## Editing workflow

A simple safe workflow when making changes:

1. Activate the virtual environment.
2. Start the app with `python app.py`.
3. Open `http://127.0.0.1:8000`.
4. Make a small code change.
5. Refresh the browser.
6. Run tests with `python -m unittest discover -s tests`.

For backend changes:
- stop and restart the Python server after editing `app.py`

For frontend changes:
- save the file and refresh the browser

## Common edit points

### Change role names or slot counts

Edit these in [app.py](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/app.py):
- `ROLE_LIMITS`
- `ROLE_LABELS`

Be careful:
- slot counts affect validation
- existing Sundays create assignment rows based on the configured limits at creation time

### Change styling

Edit:

- [static/styles.css](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/static/styles.css)

### Change frontend behavior

Edit:

- [static/app.js](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/static/app.js)

Useful areas include:
- `loadPeople()`
- `loadSundays()`
- `loadRota()`
- `getClashes()`
- `renderRota()`

### Change backend rules

Edit:

- [app.py](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/app.py)

Useful areas include:
- `is_sunday()`
- `create_sunday()`
- `replace_assignments()`
- the `do_GET`, `do_POST`, `do_PATCH`, `do_DELETE`, and `do_PUT` handlers

## API endpoints

The app currently exposes these routes:

- `GET /`
- `GET /static/...`
- `GET /meta`
- `GET /people`
- `POST /people`
- `PATCH /people/:id`
- `GET /sundays`
- `POST /sundays`
- `DELETE /sundays/:id`
- `GET /rotas/:sundayId`
- `PUT /rotas/:sundayId/assignments`

## Troubleshooting

### `python` is not recognized

Install Python, then restart the terminal.

### PowerShell blocks virtual environment activation

Run PowerShell as your normal user and use:

```bash
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then try activating the virtual environment again.

### Port 8000 is already in use

Stop the other app using that port, or run this project with a different port:

Windows PowerShell:

```bash
$env:PORT=8001
python app.py
```

Then open:

```text
http://127.0.0.1:8001
```

### The UI loads but data looks wrong

Check:
- the server terminal for errors
- that `rota.db` exists
- that you are editing the project you think you are editing

### Tests fail after changing role counts

If you change role definitions, update the test payloads in [tests/test_app.py](/abs/c:/Users/rjgil/OneDrive/Documents/PROJECTS/CHURCH_ROTAS/tests/test_app.py) so they match the new slot limits.

## Git and GitHub notes

If you want to track the database file:
- `rota.db` is currently not ignored

If you do not want to commit live rota data in future:
- add `rota.db` back into `.gitignore`
- keep a separate dummy database for the repo if needed

## Future improvements

Possible next steps:
- deploy the app to an internet host
- add authentication
- add monthly or rolling Sunday generation
- add export to CSV or PDF
- add availability or fairness rules
- add editing for role definitions in the UI

## Quick command reference

Create virtual environment:

```bash
python -m venv .venv
```

Activate virtual environment in PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Run app:

```bash
python app.py
```

Run tests:

```bash
python -m unittest discover -s tests
```
