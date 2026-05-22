# Sunday Rota Webapp

A lightweight church rota webapp for managing Sunday teams with shared SQLite storage.

## Features

- Add and deactivate people in a reusable people bank
- Add Sundays manually using a date picker
- Assign people to fixed team slots:
  - Band: 4
  - AV: 2
  - Tea and Coffee: 2
  - Youth: 2
  - Children's Church: 2
  - Welcomers: 2
- Highlight same-Sunday clashes in red before saving
- Reject duplicate same-Sunday assignments on the server too

## Run

```bash
python app.py
```

The app starts on `http://0.0.0.0:8000`.

## Tests

```bash
python -m unittest discover -s tests
```

## Notes

- This implementation uses Python's standard library HTTP server plus SQLite because Node/React tooling was not available in the local environment.
- Data is stored in `rota.db` in the project folder.
