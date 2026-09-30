"""端到端冒烟脚本：对运行中的服务跑一遍核心链路（quickstart 场景 A–G 的最小版）。

用法：python scripts/smoke_check.py [base_url]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read().decode()
            return response.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as error:
        payload = error.read().decode()
        return error.code, (json.loads(payload) if payload else None)


def main() -> int:
    status, health = call("GET", "/api/health")
    print("health:", status, health)
    assert status == 200

    # 每次冒烟使用新账号：脚本假定"当日尚未浏览"，复用旧账号会跳过锁定校验
    login_name = f"smoke_{int(time.time()) % 1000000}"  # 登录名上限 20 字符
    status, session = call(
        "POST",
        "/api/auth/register",
        body={
            "login_name": login_name,
            "nickname": "冒烟测试",
            "password": "abc123",
        },
    )
    if status == 409:  # 已注册则直接登录
        status, session = call(
            "POST",
            "/api/auth/login",
            body={"login_name": login_name, "password": "abc123"},
        )
    print("register/login:", status)
    assert status in (200, 201)
    token = session["access_token"]

    status, today = call("GET", "/api/study/today", token)
    print("study.today:", status, today["total_count"], "viewed", today["viewed_count"])
    assert status == 200

    status, locked = call("POST", "/api/quiz/today/start", token, {})
    print("quiz start before viewing:", status, locked)
    assert status == 409 and locked["error"]["code"] == "quiz_locked"

    for item in today["items"]:
        status, _ = call("POST", f"/api/study/today/items/{item['word_id']}/view", token)
        assert status == 200

    status, start = call("POST", "/api/quiz/today/start", token, {})
    print("quiz start after viewing:", status, len(start["questions"]))
    assert status == 200

    for question in start["questions"]:
        status, answer = call(
            "POST",
            "/api/quiz/today/answer",
            token,
            {"question_id": question["question_id"], "choice_index": 0},
        )
        assert status == 200
        if not answer["is_correct"]:
            call(
                "POST",
                "/api/quiz/today/answer",
                token,
                {
                    "question_id": question["question_id"],
                    "choice_index": answer["correct_index"],
                },
            )

    status, report = call("POST", "/api/quiz/today/finish", token, {})
    print("quiz finish:", status, report)
    assert status == 200

    status, wrong = call("GET", "/api/wrong-words", token)
    print("wrong words:", status, wrong["total"])
    assert status == 200

    if wrong["total"]:
        status, review = call("POST", "/api/quiz/review/start", token, {})
        print("review start:", status, len(review["questions"]))
        assert status == 200
        for question in review["questions"]:
            status, answer = call(
                "POST",
                "/api/quiz/review/answer",
                token,
                {"question_id": question["question_id"], "choice_index": 0},
            )
            if not answer["is_correct"]:
                call(
                    "POST",
                    "/api/quiz/review/answer",
                    token,
                    {
                        "question_id": question["question_id"],
                        "choice_index": answer["correct_index"],
                    },
                )
        status, review_report = call("POST", "/api/quiz/review/finish", token, {})
        print("review finish:", status, review_report)
        assert status == 200

    status, summary = call("GET", "/api/home/summary", token)
    print("home summary:", status, summary["today"], "wrong", summary["wrong_word_count"])
    assert status == 200

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
