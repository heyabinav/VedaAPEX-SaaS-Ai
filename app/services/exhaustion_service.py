import os
from datetime import datetime

CRASH_FILE = "api_exhausted_crash.txt"


class ExhaustionService:
    """Manages server crash state when all provider API keys are exhausted for the day."""

    @staticmethod
    def mark_crashed():
        """Mark that the server has crashed for today due to API exhaustion."""
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            with open(CRASH_FILE, "w") as f:
                f.write(today_str)
            print(f"[Exhaustion] Server marked as CRASHED for date: {today_str}")
        except Exception as e:
            print(f"[Exhaustion] Error writing crash file: {e}")

    @staticmethod
    def is_crashed() -> bool:
        """Check if the server is currently crashed for today."""
        if not os.path.exists(CRASH_FILE):
            return False
        try:
            with open(CRASH_FILE, "r") as f:
                crashed_date = f.read().strip()
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            return crashed_date == today_str
        except Exception:
            return False

    @staticmethod
    def clear_crash():
        """Clear the crash state."""
        if os.path.exists(CRASH_FILE):
            try:
                os.remove(CRASH_FILE)
                print("[Exhaustion] Server crash state cleared.")
            except Exception as e:
                print(f"[Exhaustion] Error clearing crash file: {e}")
