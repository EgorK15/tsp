import argparse
import json
from datetime import datetime
from getpass import getpass
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from websockets.exceptions import ConnectionClosed, InvalidHandshake
from websockets.sync.client import connect

from notification_service.messages import render_text


def read_json(url, *, data=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = Request(url, data=data, headers=headers)
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def websocket_url(base, token):
    parts = urlsplit(base)
    scheme = "wss" if parts.scheme == "https" else "ws"
    return urlunsplit((scheme, parts.netloc, parts.path + "/ws/notifications", urlencode({"token": token}), ""))


def show_notice(notice, seen):
    if notice["id"] in seen:
        return
    text = notice.get("text") or render_text(notice["event_type"], notice["payload"])
    local_time = datetime.fromisoformat(notice["created_at"]).astimezone()
    print(f"[{local_time:%d.%m.%Y %H:%M:%S}] {text}", flush=True)
    seen.add(notice["id"])


def watch(base, token):
    seen = set()
    while True:
        try:
            with connect(websocket_url(base, token), open_timeout=5) as websocket:
                unread = read_json(base + "/api/notifications?unread=true", token=token)
                for notice in unread:
                    show_notice(notice, seen)
                print("Подключено. Жду новых уведомлений.", flush=True)
                for raw in websocket:
                    show_notice(json.loads(raw), seen)
        except ConnectionClosed as exc:
            if exc.rcvd is not None and exc.rcvd.code == 4401:
                print("Токен недействителен. Войдите заново.", flush=True)
                return 1
        except HTTPError as exc:
            if exc.code in (401, 403):
                print("Токен недействителен. Войдите заново.", flush=True)
                return 1
        except (OSError, URLError, InvalidHandshake):
            pass
        print("Связь потеряна. Переподключение через 2 с.", flush=True)
        sleep(2)


def main():
    parser = argparse.ArgumentParser(description="Консольный клиент уведомлений ТехОчереди")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password")
    parser.add_argument("--base", default="http://localhost")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.query or parts.fragment:
        parser.error("--base должен быть HTTP(S)-адресом Nginx")
    password = args.password if args.password is not None else getpass("Пароль: ")
    data = urlencode({"username": args.email, "password": password}).encode()
    try:
        token = read_json(base + "/api/auth/login", data=data)["access_token"]
    except HTTPError as exc:
        print(f"Вход не выполнен (HTTP {exc.code}).")
        return 1
    except (OSError, URLError):
        print("Не удалось подключиться к API.")
        return 1
    try:
        return watch(base, token)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
