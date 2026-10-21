"""语法模块契约测试（contracts/api.md）：端点形状、错误码与登录守卫。"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, register

pytestmark = pytest.mark.contract

POINT_ID = "G-A01"

# 9 个端点：未登录一律 401 `unauthorized`（FR-018）
UNAUTH_CASES = [
    ("get", "/api/grammar/outline", None),
    ("get", f"/api/grammar/points/{POINT_ID}", None),
    ("post", f"/api/grammar/points/{POINT_ID}/view", {}),
    ("post", f"/api/grammar/points/{POINT_ID}/guess", {"choice_key": "A"}),
    ("post", f"/api/grammar/points/{POINT_ID}/check/start", {}),
    ("post", f"/api/grammar/points/{POINT_ID}/practice/start", {"level": None}),
    ("post", "/api/grammar/attempts/1/answer", {"question_id": "X", "choice_key": "A"}),
    ("post", "/api/grammar/attempts/1/finish", {}),
    ("get", "/api/grammar/wrong-points", None),
]


def _token(client, login_name: str = "guser1") -> str:
    return str(register(client, login_name=login_name)["access_token"])


@pytest.mark.parametrize(("method", "path", "body"), UNAUTH_CASES)
def test_grammar_endpoints_require_login(client, method, path, body) -> None:
    response = client.get(path) if method == "get" else client.post(path, json=body)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_outline_shape(client) -> None:
    response = client.get("/api/grammar/outline", headers=auth_headers(_token(client)))

    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"total_points", "mastered_count", "wrong_count", "modules"}
    assert data["total_points"] == 82
    assert data["mastered_count"] == 0
    assert data["wrong_count"] == 0
    assert data["modules"], "大纲至少包含一个模块"

    for module in data["modules"]:
        assert set(module) == {"module", "module_name", "points"}
        for point in module["points"]:
            assert set(point) == {
                "id",
                "title",
                "depth",
                "card_type",
                "status",
                "has_wrong",
                "question_count",
            }
            assert point["status"] == "not_started"
            assert point["depth"] in ("核心", "了解")
            assert point["card_type"] in ("rule", "contrast", "memorize")


# ------------------------------------------------------------------ US2 学卡

ANSWER_LEAKING_KEYS = ("is_correct", "correct_key", "explanation", "feedback", "answer")


def _assert_no_answer_leak(node) -> None:
    """递归断言：响应中不得出现答案相关字段（FR-007）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in ANSWER_LEAKING_KEYS, f"泄露答案字段: {key}"
            _assert_no_answer_leak(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_answer_leak(item)


def test_point_card_shape_and_answer_protection(client) -> None:
    headers = auth_headers(_token(client, "guser2"))
    response = client.get(f"/api/grammar/points/{POINT_ID}", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"point", "payload", "check_questions"}
    assert set(data["point"]) == {
        "id",
        "module",
        "module_name",
        "title",
        "depth",
        "card_type",
        "status",
        "has_wrong",
    }

    guess = data["payload"].get("guess", {})
    assert "answer" not in guess, "guess.answer 不得下发"
    for option in guess.get("options", []):
        assert set(option) == {"key", "text"}, "猜一猜选项只能有 key / text"

    for question in data["check_questions"]:
        assert set(question) == {"question_id", "level", "stem", "options"}
        for option in question["options"]:
            assert set(option) == {"key", "text"}

    _assert_no_answer_leak(data)


def test_point_card_not_found(client) -> None:
    headers = auth_headers(_token(client, "guser2"))
    response = client.get("/api/grammar/points/G-ZZ99", headers=headers)

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "grammar_point_not_found"


def test_guess_feedback_after_choice(client) -> None:
    headers = auth_headers(_token(client, "guser2"))
    response = client.post(
        f"/api/grammar/points/{POINT_ID}/guess",
        headers=headers,
        json={"choice_key": "A"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"point_id", "choice_key", "feedback"}
    assert data["choice_key"] == "A"
    assert data["feedback"], "应返回所选选项的反馈"


def test_guess_invalid_choice_key(client) -> None:
    headers = auth_headers(_token(client, "guser2"))
    response = client.post(
        f"/api/grammar/points/{POINT_ID}/guess",
        headers=headers,
        json={"choice_key": "Z"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "invalid_choice_key"


def test_check_start_has_no_answers(client) -> None:
    headers = auth_headers(_token(client, "guser2"))
    response = client.post(
        f"/api/grammar/points/{POINT_ID}/check/start", headers=headers, json={}
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"attempt_id", "source", "point_id", "questions"}
    assert data["source"] == "card"
    assert data["questions"]
    _assert_no_answer_leak(data)


def test_answer_and_finish_flow(client) -> None:
    headers = auth_headers(_token(client, "guser3"))
    started = client.post(
        f"/api/grammar/points/{POINT_ID}/check/start", headers=headers, json={}
    )
    assert started.status_code == 200, started.text
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]

    # 逐题以 A 作答（不论对错），推进到结算
    for question in questions:
        answer = client.post(
            f"/api/grammar/attempts/{attempt_id}/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_key": "A"},
        )
        assert answer.status_code == 200, answer.text
        assert set(answer.json()) == {
            "question_id",
            "is_correct",
            "correct_key",
            "explanation",
            "feedback",
            "attempt",
            "added_to_wrong_points",
            "removed_from_wrong_points",
            "correct_streak",
        }

    finished = client.post(
        f"/api/grammar/attempts/{attempt_id}/finish", headers=headers, json={}
    )
    assert finished.status_code == 200, finished.text
    result = finished.json()
    assert set(result) == {
        "attempt_id",
        "source",
        "point_id",
        "total_count",
        "correct_count",
        "wrong_count",
        "accuracy",
        "duration_seconds",
        "mastered",
        "status",
    }

    # 已结束轮次：再作答 / 再结算均 409
    again = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={"question_id": questions[0]["question_id"], "choice_key": "A"},
    )
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "grammar_attempt_already_finished"

    refinish = client.post(
        f"/api/grammar/attempts/{attempt_id}/finish", headers=headers, json={}
    )
    assert refinish.status_code == 409, refinish.text


# ------------------------------------------------------------------ US3 练习


def _point_with_questions(client, headers) -> str:
    outline = client.get("/api/grammar/outline", headers=headers).json()
    for module in outline["modules"]:
        for point in module["points"]:
            if point["question_count"] > 0:
                return str(point["id"])
    raise AssertionError("题库题知识点不应为空")


def _point_without_questions(client, headers) -> str:
    outline = client.get("/api/grammar/outline", headers=headers).json()
    for module in outline["modules"]:
        for point in module["points"]:
            if point["question_count"] == 0:
                return str(point["id"])
    raise AssertionError("应存在无题库题的知识点")


def test_practice_start_orders_and_protects_answers(client) -> None:
    headers = auth_headers(_token(client, "guser5"))
    point_id = _point_with_questions(client, headers)

    response = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source"] == "bank"
    levels = [question["level"] for question in data["questions"]]
    assert levels == sorted(levels)
    _assert_no_answer_leak(data)


def test_practice_start_without_questions(client) -> None:
    headers = auth_headers(_token(client, "guser5"))
    point_id = _point_without_questions(client, headers)

    response = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "no_grammar_questions"


# ------------------------------------------------------------ US4 语法错题本


def test_wrong_points_empty(client) -> None:
    headers = auth_headers(_token(client, "guser6"))
    response = client.get("/api/grammar/wrong-points", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data == {"total": 0, "items": []}


def test_wrong_points_shape_after_wrong_answer(client) -> None:
    headers = auth_headers(_token(client, "guser6"))
    point_id = _point_with_questions(client, headers)
    started = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    question = started.json()["questions"][0]
    # 依次尝试 A/B/C/D，第一个判为错误的答案即制造一条错题
    for key in ("A", "B", "C", "D"):
        answer = client.post(
            f"/api/grammar/attempts/{started.json()['attempt_id']}/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_key": key},
        )
        if answer.json()["is_correct"] is False:
            break

    response = client.get("/api/grammar/wrong-points", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert set(item) == {
            "point_id",
            "title",
            "module",
            "module_name",
            "wrong_count",
            "correct_streak",
            "added_at",
            "last_wrong_at",
        }
    added = [item["added_at"] for item in data["items"]]
    assert added == sorted(added), "列表按加入时间升序"


def test_practice_start_invalid_level(client) -> None:
    headers = auth_headers(_token(client, "guser5"))
    point_id = _point_with_questions(client, headers)

    response = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": "L9"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_answer_invalid_choice_key_and_idempotent(client) -> None:
    headers = auth_headers(_token(client, "guser4"))
    started = client.post(
        f"/api/grammar/points/{POINT_ID}/check/start", headers=headers, json={}
    )
    attempt_id = started.json()["attempt_id"]
    question_id = started.json()["questions"][0]["question_id"]

    invalid = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={"question_id": question_id, "choice_key": "Z"},
    )
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["error"]["code"] == "invalid_choice_key"

    first = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={"question_id": question_id, "choice_key": "A"},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={"question_id": question_id, "choice_key": "B"},
    )
    assert second.status_code == 200, second.text
    # 重复提交返回首次结果：选项键与计数都不变
    assert second.json()["correct_key"] == first.json()["correct_key"]
    assert second.json()["attempt"] == first.json()["attempt"]
    assert second.json()["is_correct"] == first.json()["is_correct"]
