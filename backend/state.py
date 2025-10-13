# state.py
from typing import Dict, List

chat_sessions: Dict[str, List[dict]] = {}
feedback_store: Dict[str, Dict[int, int]] = {}
# chat_sessions structure: {session_id: [{"role": "user"/"assistant", "content": "..."}, ...]}