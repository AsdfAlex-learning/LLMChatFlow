import requests


def main() -> None:
    response = requests.post(
        "http://127.0.0.1:8000/chat",
        json={"session_id": "demo_session", "user_input": "你好"},
        timeout=30,
    )
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    main()
