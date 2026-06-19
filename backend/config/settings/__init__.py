import os

if os.getenv("DJANGO_ENV") == "production":
    from .production import *  # type: ignore
else:
    from .local import *  # type: ignore
