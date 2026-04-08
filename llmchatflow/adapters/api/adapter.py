from typing import Dict, Any


class APIAdapter:
    def parse_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        session_id = str(payload.get("session_id", "default_session"))
        user_input = str(payload.get("user_input", ""))
        return {"session_id": session_id, "user_input": user_input}

    def format_response(self, response_text: str) -> Dict[str, Any]:
        return {"response": response_text}
