from __future__ import annotations
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Primary library name since 2024 is lseg-data (aka LSEG Data Library v2)
import lseg.data as ld

# If you only have the older refinitiv-data library, uncomment the next two lines
# import refinitiv.data as ld  # same API surface for this project

load_dotenv()

APP_KEY = os.getenv("LSEG_APP_KEY")
SESSION_TYPE = (os.getenv("LSEG_SESSION_TYPE") or "desktop").lower()


def _open_session():
    """Open a Desktop or Platform session depending on env.
    Desktop requires LSEG Workspace/Eikon running locally.
    Platform requires proper RDP credentials configured in your JSON config.
    """
    if SESSION_TYPE == "platform":
        # relies on lseg-data.config.json with platform credentials, or env vars
        return ld.open_platform_session(app_key=APP_KEY)
    else:
        return ld.open_desktop_session(app_key=APP_KEY)


@contextmanager
def session_scope():
    """Context manager to open/close an LSEG session safely."""
    with _open_session() as sess:
        yield sess
