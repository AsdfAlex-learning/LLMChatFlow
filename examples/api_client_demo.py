"""API Client Demo: demonstrates calling LLMChatFlow API service.

Usage:
    1. Start the API server: python -m llmchatflow api
    2. Run this demo: python examples/api_client_demo.py

Demonstrates POST /chat request parameters, response parsing,
health check, and error handling paths per plan Section 3.1.
"""
import requests

API_BASE = "http://127.0.0.1:8000"


def check_health() -> bool:
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            print(f"Health check: {resp.json()}")
            return True
        print(f"Health check failed: {resp.status_code}")
        return False
    except requests.ConnectionError:
        print("API server is not running. Start with: python -m llmchatflow api")
        return False


def send_chat(session_id: str, user_input: str) -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"session_id": session_id, "user_input": user_input},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"[{session_id}] User: {user_input}")
            print(f"[{session_id}] Assistant: {data.get('response', '')}")
        else:
            print(f"[{session_id}] Error {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"[{session_id}] Request failed: {e}")


def main() -> None:
    if not check_health():
        return

    # Single session, multiple turns
    send_chat("demo_session", "你好，请介绍一下你自己")
    send_chat("demo_session", "我刚才问了什么？")

    # Different session
    send_chat("another_session", "今天天气怎么样？")

    # Test error handling: empty input
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"session_id": "test", "user_input": ""},
            timeout=5,
        )
        print(f"Empty input error: {resp.status_code} - {resp.text}")
    except requests.RequestException as e:
        print(f"Empty input request failed: {e}")

    print("\nAPI client demo completed.")


if __name__ == "__main__":
    main()
