import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "rota.db"

ROLE_LIMITS = {
    "band": 4,
    "av": 2,
    "teaCoffee": 2,
    "youth": 2,
    "childrensChurch": 2,
    "welcomers": 2,
}

ROLE_LABELS = {
    "band": "Band",
    "av": "AV",
    "teaCoffee": "Tea and Coffee",
    "youth": "Youth",
    "childrensChurch": "Children's Church",
    "welcomers": "Welcomers",
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_sunday(value: str) -> bool:
    parsed = date.fromisoformat(value)
    return parsed.weekday() == 6


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class RotaRepository:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with closing(self.connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sundays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_date TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sunday_id INTEGER NOT NULL,
                    role_key TEXT NOT NULL,
                    slot_index INTEGER NOT NULL,
                    person_id INTEGER,
                    FOREIGN KEY (sunday_id) REFERENCES sundays (id) ON DELETE CASCADE,
                    FOREIGN KEY (person_id) REFERENCES people (id),
                    UNIQUE (sunday_id, role_key, slot_index)
                );
                """
            )
            conn.commit()

    def list_people(self):
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT id, name, active, created_at, updated_at FROM people ORDER BY active DESC, LOWER(name)"
            ).fetchall()
            return [dict(row) for row in rows]

    def create_person(self, name: str):
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Name is required.")

        now = utc_now()
        try:
            with closing(self.connect()) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO people (name, active, created_at, updated_at)
                    VALUES (?, 1, ?, ?)
                    """,
                    (clean_name, now, now),
                )
                conn.commit()
                return self.get_person(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("That person already exists.") from exc

    def get_person(self, person_id: int):
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT id, name, active, created_at, updated_at FROM people WHERE id = ?",
                (person_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError("Person not found.")
            return dict(row)

    def update_person(self, person_id: int, payload: dict):
        current = self.get_person(person_id)
        name = payload.get("name", current["name"])
        active = payload.get("active", current["active"])

        clean_name = str(name).strip()
        if not clean_name:
            raise ValidationError("Name is required.")
        if active not in (0, 1, False, True):
            raise ValidationError("Active must be true or false.")

        active_value = 1 if bool(active) else 0
        now = utc_now()
        try:
            with closing(self.connect()) as conn:
                conn.execute(
                    """
                    UPDATE people
                    SET name = ?, active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (clean_name, active_value, now, person_id),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValidationError("That person already exists.") from exc

        return self.get_person(person_id)

    def list_sundays(self):
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT id, service_date FROM sundays ORDER BY service_date DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def create_sunday(self, service_date: str):
        if not service_date:
            raise ValidationError("A service date is required.")
        try:
            if not is_sunday(service_date):
                raise ValidationError("Only Sundays can be created.")
        except ValueError as exc:
            raise ValidationError("Service date must be in YYYY-MM-DD format.") from exc

        try:
            with closing(self.connect()) as conn:
                cursor = conn.execute(
                    "INSERT INTO sundays (service_date) VALUES (?)",
                    (service_date,),
                )
                sunday_id = cursor.lastrowid
                for role_key, limit in ROLE_LIMITS.items():
                    for slot_index in range(limit):
                        conn.execute(
                            """
                            INSERT INTO assignments (sunday_id, role_key, slot_index, person_id)
                            VALUES (?, ?, ?, NULL)
                            """,
                            (sunday_id, role_key, slot_index),
                        )
                conn.commit()
                return self.get_sunday(sunday_id)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("That Sunday already exists.") from exc

    def get_sunday(self, sunday_id: int):
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT id, service_date FROM sundays WHERE id = ?",
                (sunday_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError("Sunday not found.")
            return dict(row)

    def delete_sunday(self, sunday_id: int):
        with closing(self.connect()) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            deleted = conn.execute("DELETE FROM sundays WHERE id = ?", (sunday_id,))
            conn.commit()
            if deleted.rowcount == 0:
                raise NotFoundError("Sunday not found.")

    def get_rota(self, sunday_id: int):
        sunday = self.get_sunday(sunday_id)
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT
                    a.role_key,
                    a.slot_index,
                    a.person_id,
                    p.name AS person_name,
                    p.active AS person_active
                FROM assignments a
                LEFT JOIN people p ON p.id = a.person_id
                WHERE a.sunday_id = ?
                ORDER BY a.role_key, a.slot_index
                """,
                (sunday_id,),
            ).fetchall()

        assignments = {role_key: [] for role_key in ROLE_LIMITS}
        for row in rows:
            assignments[row["role_key"]].append(
                {
                    "slotIndex": row["slot_index"],
                    "personId": row["person_id"],
                    "personName": row["person_name"],
                    "personActive": row["person_active"],
                }
            )

        return {
            "sunday": sunday,
            "roles": [
                {
                    "key": role_key,
                    "label": ROLE_LABELS[role_key],
                    "limit": ROLE_LIMITS[role_key],
                    "assignments": assignments[role_key],
                }
                for role_key in ROLE_LIMITS
            ],
        }

    def replace_assignments(self, sunday_id: int, payload: dict):
        self.get_sunday(sunday_id)
        assignments = payload.get("assignments")
        if not isinstance(assignments, dict):
            raise ValidationError("Assignments payload is required.")

        normalized = {}
        chosen_people = []

        for role_key, limit in ROLE_LIMITS.items():
            slots = assignments.get(role_key, [])
            if not isinstance(slots, list) or len(slots) != limit:
                raise ValidationError(f"{role_key} must contain exactly {limit} slots.")

            normalized_slots = []
            for slot_index, person_id in enumerate(slots):
                if person_id in ("", None):
                    normalized_slots.append(None)
                    continue

                if not isinstance(person_id, int):
                    raise ValidationError("Assignments must use person ids or null.")

                person = self.get_person(person_id)
                if not person["active"]:
                    raise ValidationError(f"{person['name']} is inactive and cannot be assigned.")

                normalized_slots.append(person_id)
                chosen_people.append(person_id)

            normalized[role_key] = normalized_slots

        duplicates = {person_id for person_id in chosen_people if chosen_people.count(person_id) > 1}
        if duplicates:
            duplicate_names = [self.get_person(person_id)["name"] for person_id in sorted(duplicates)]
            raise ValidationError(
                "Clashes found for: " + ", ".join(duplicate_names) + ". A person can only serve once per Sunday."
            )

        with closing(self.connect()) as conn:
            for role_key, slots in normalized.items():
                for slot_index, person_id in enumerate(slots):
                    conn.execute(
                        """
                        UPDATE assignments
                        SET person_id = ?
                        WHERE sunday_id = ? AND role_key = ? AND slot_index = ?
                        """,
                        (person_id, sunday_id, role_key, slot_index),
                    )
            conn.commit()

        return self.get_rota(sunday_id)


REPOSITORY = RotaRepository(DB_PATH)


class RotaRequestHandler(BaseHTTPRequestHandler):
    server_version = "SundayRota/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/":
                return self.serve_file("index.html", "text/html; charset=utf-8")
            if path.startswith("/static/"):
                rel_path = path.removeprefix("/static/")
                return self.serve_static(rel_path)
            if path == "/meta":
                return self.send_json(
                    {
                        "roles": [
                            {"key": key, "label": ROLE_LABELS[key], "limit": ROLE_LIMITS[key]}
                            for key in ROLE_LIMITS
                        ]
                    }
                )
            if path == "/people":
                return self.send_json({"people": REPOSITORY.list_people()})
            if path == "/sundays":
                return self.send_json({"sundays": REPOSITORY.list_sundays()})
            if path.startswith("/rotas/"):
                sunday_id = int(path.split("/")[-1])
                return self.send_json(REPOSITORY.get_rota(sunday_id))
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid identifier")
        except NotFoundError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self.read_json_body()
            if path == "/people":
                person = REPOSITORY.create_person(payload.get("name", ""))
                return self.send_json(person, status=HTTPStatus.CREATED)
            if path == "/sundays":
                sunday = REPOSITORY.create_sunday(payload.get("serviceDate", ""))
                return self.send_json(sunday, status=HTTPStatus.CREATED)
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except ValidationError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_PATCH(self):
        path = urlparse(self.path).path
        try:
            if not path.startswith("/people/"):
                return self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            person_id = int(path.split("/")[-1])
            payload = self.read_json_body()
            updated = REPOSITORY.update_person(person_id, payload)
            self.send_json(updated)
        except ValueError:
            self.send_json({"error": "Invalid identifier."}, status=HTTPStatus.BAD_REQUEST)
        except ValidationError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except NotFoundError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            if not path.startswith("/sundays/"):
                return self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            sunday_id = int(path.split("/")[-1])
            REPOSITORY.delete_sunday(sunday_id)
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_cors_headers()
            self.end_headers()
        except ValueError:
            self.send_json({"error": "Invalid identifier."}, status=HTTPStatus.BAD_REQUEST)
        except NotFoundError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        path = urlparse(self.path).path
        try:
            if not path.startswith("/rotas/") or not path.endswith("/assignments"):
                return self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            sunday_id = int(path.split("/")[2])
            payload = self.read_json_body()
            rota = REPOSITORY.replace_assignments(sunday_id, payload)
            self.send_json(rota)
        except ValueError:
            self.send_json({"error": "Invalid identifier."}, status=HTTPStatus.BAD_REQUEST)
        except ValidationError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except NotFoundError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise ValidationError("Request body must be valid JSON.") from exc

    def serve_static(self, relative_path: str):
        file_path = (STATIC_DIR / relative_path).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")

        content_type = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(file_path.suffix, "application/octet-stream")
        return self.serve_file(file_path, content_type)

    def serve_file(self, file_ref, content_type: str):
        file_path = Path(file_ref)
        if not file_path.is_absolute():
            file_path = STATIC_DIR / file_path
        if not file_path.exists():
            return self.send_error(HTTPStatus.NOT_FOUND, "File not found")

        payload = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")

    def log_message(self, format, *args):
        return


def run_server(host: str = "0.0.0.0", port: int = 8000):
    with ThreadingHTTPServer((host, port), RotaRequestHandler) as httpd:
        print(f"Sunday rota app running on http://{host}:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    run_server(host=host, port=port)
