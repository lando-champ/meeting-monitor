"""
Placeholder for a future dedicated meeting-bot worker (queue + isolated process).

Meeting capture and STT currently run inside the main FastAPI app lifecycle; see ``docs/meeting-bot.md``.
"""
from __future__ import annotations


def main() -> None:
    print("Meeting bots are started from the main API (POST /api/v1/meetings/{meeting_id}/start).")
    print("Run the API with: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001")


if __name__ == "__main__":
    main()
