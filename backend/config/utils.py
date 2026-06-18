import socket
from contextlib import closing


def is_service_available(host: str, port: int, timeout: int = 1) -> bool:
    """
    Executes a socket connection test to verify if downstream services
    (like Postgres or Redis) are actively accepting connections.
    """
    if not host or not port:
        return False
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        try:
            return sock.connect_ex((host, int(port))) == 0
        except (socket.gaierror, TypeError):
            return False
