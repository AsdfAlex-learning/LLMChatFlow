from typing import Dict, Any


class APIAdapter:
    """HTTP API adapter: parses incoming JSON payloads and formats outgoing responses."""

    def parse_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract session_id and user_input from an API request payload."""
        session_id = str(payload.get("session_id", "default_session"))
        user_input = str(payload.get("user_input", ""))
        return {"session_id": session_id, "user_input": user_input}

    def format_response(self, response_text: str) -> Dict[str, Any]:
        """Wrap response text into a JSON-serializable response dict."""
        return {"response": response_text}
