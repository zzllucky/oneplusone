"""语法学习链路集成测试：真实 HTTP + 真实 SQLite，禁用 mock（章程 IV）。

覆盖 US2（学卡三段式）、US3（题库练习）、US4（错题回链）与账号隔离（FR-019）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.grammar_progress import (
    GrammarAttempt,
    GrammarPointProgress,
    GrammarWrongPoint,
)
from app.models import GrammarOption
from tests.conftest import auth_headers, register

pytestmark = pytest.mark.integration


def _token(client, login_name: str) -> str:
    return str(register(client, login_name=login_name)["access_token"])


def _correct_key(db, question_id: str) -> str:
    return db.scalar(
        select(GrammarOption.key).where(
            GrammarOption.question_id == question_id, GrammarOption.is_correct.is_(True)
        )
    )


def _wrong_key(db, question_id: str) -> str:
    return db.scalar(
        select(GrammarOption.key).where(
            GrammarOption.question_id == question_id, GrammarOption.is_correct.is_(False)
        )
    )


def test_card_study_flow_marks_mastered(client, db) -> None:
    """US2：打开学卡 → 标记已学 → 学后检测全对 → 掌握，大纲计数同步。"""
    headers = auth_headers(_token(client, "gflow1"))

    outline = client.get("/api/grammar/outline", headers=headers).json()
    assert outline["mastered_count"] == 0
    point_id = outline["modules"][0]["points"][0]["id"]

    viewed = client.post(f"/api/grammar/points/{point_id}/view", headers=headers, json={})
    assert viewed.status_code == 200, viewed.text
    assert viewed.json()["status"] == "learning"

    started = client.post(
        f"/api/grammar/points/{point_id}/check/start", headers=headers, json={}
    )
    assert started.status_code == 200, started.text
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]

    for question in questions:
        answer = client.post(
            f"/api/grammar/attempts/{attempt_id}/answer",
            headers=headers,
            json={
                "question_id": question["question_id"],
                "choice_key": _correct_key(db, question["question_id"]),
            },
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["is_correct"] is True

    finished = client.post(
        f"/api/grammar/attempts/{attempt_id}/finish", headers=headers, json={}
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["mastered"] is True
    assert finished.json()["status"] == "mastered"

    outline = client.get("/api/grammar/outline", headers=headers).json()
    assert outline["mastered_count"] == 1


def _point_with_questions(client, headers) -> str:
    outline = client.get("/api/grammar/outline", headers=headers).json()
    for module in outline["modules"]:
        for point in module["points"]:
            if point["question_count"] > 0:
                return str(point["id"])
    raise AssertionError("题库题知识点不应为空")


def test_practice_flow_and_restart(client, db) -> None:
    """US3：发起练习 → 逐题作答 → 结算 → 再次发起可重新开始；练习不改变掌握状态。"""
    headers = auth_headers(_token(client, "gflow2"))
    point_id = _point_with_questions(client, headers)

    started = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    assert started.status_code == 200, started.text
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]

    # 第一题故意答错，其余答对
    first = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={
            "question_id": questions[0]["question_id"],
            "choice_key": _wrong_key(db, questions[0]["question_id"]),
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["is_correct"] is False
    assert first.json()["added_to_wrong_points"] is True

    # 答错即进入语法错题本（后续连续答对达标会自动移出，故此处立即校验）
    wrong_points = client.get("/api/grammar/wrong-points", headers=headers).json()
    assert wrong_points["total"] == 1
    assert wrong_points["items"][0]["point_id"] == point_id

    for question in questions[1:]:
        answer = client.post(
            f"/api/grammar/attempts/{attempt_id}/answer",
            headers=headers,
            json={
                "question_id": question["question_id"],
                "choice_key": _correct_key(db, question["question_id"]),
            },
        )
        assert answer.status_code == 200, answer.text

    finished = client.post(
        f"/api/grammar/attempts/{attempt_id}/finish", headers=headers, json={}
    )
    assert finished.status_code == 200, finished.text
    result = finished.json()
    assert result["total_count"] == len(questions)
    assert result["correct_count"] == len(questions) - 1
    assert result["wrong_count"] == 1
    assert result["mastered"] is False
    assert result["duration_seconds"] >= 0

    # 练习不改变掌握状态
    outline = client.get("/api/grammar/outline", headers=headers).json()
    assert outline["mastered_count"] == 0

    # 再次发起：新轮次
    restarted = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["attempt_id"] != attempt_id


def test_wrong_point_closed_loop(client, db) -> None:
    """US4：练习答错入本 → 检测答错同样入本 → 连续答对达标移出。"""
    headers = auth_headers(_token(client, "gflow3"))
    point_id = _point_with_questions(client, headers)

    # 练习答错 → 入本
    started = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers,
        json={"level": None},
    )
    attempt_id = started.json()["attempt_id"]
    question_id = started.json()["questions"][0]["question_id"]
    wrong = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers,
        json={"question_id": question_id, "choice_key": _wrong_key(db, question_id)},
    )
    assert wrong.json()["added_to_wrong_points"] is True

    listed = client.get("/api/grammar/wrong-points", headers=headers).json()
    assert listed["total"] == 1
    assert listed["items"][0]["point_id"] == point_id

    # 学后检测答错同样入本
    checked = client.post(
        f"/api/grammar/points/{point_id}/check/start", headers=headers, json={}
    )
    if checked.status_code == 200:
        card_question = checked.json()["questions"][0]["question_id"]
        answer = client.post(
            f"/api/grammar/attempts/{checked.json()['attempt_id']}/answer",
            headers=headers,
            json={
                "question_id": card_question,
                "choice_key": _wrong_key(db, card_question),
            },
        )
        assert answer.status_code == 200, answer.text
        assert client.get("/api/grammar/wrong-points", headers=headers).json()[
            "items"
        ][0]["wrong_count"] >= 2

    # 连续答对 2 次 → 移出
    for _ in range(2):
        practice = client.post(
            f"/api/grammar/points/{point_id}/practice/start",
            headers=headers,
            json={"level": None},
        )
        qid = practice.json()["questions"][0]["question_id"]
        answer = client.post(
            f"/api/grammar/attempts/{practice.json()['attempt_id']}/answer",
            headers=headers,
            json={"question_id": qid, "choice_key": _correct_key(db, qid)},
        )
        assert answer.status_code == 200, answer.text

    assert client.get("/api/grammar/wrong-points", headers=headers).json()["total"] == 0


def test_grammar_data_isolated_between_accounts(client, db) -> None:
    """FR-019：语法进度、轮次与错题本随账号隔离。"""
    headers_a = auth_headers(_token(client, "gflowA"))
    headers_b = auth_headers(_token(client, "gflowB"))
    point_id = _point_with_questions(client, headers_a)

    started = client.post(
        f"/api/grammar/points/{point_id}/practice/start",
        headers=headers_a,
        json={"level": None},
    )
    attempt_id = started.json()["attempt_id"]
    question_id = started.json()["questions"][0]["question_id"]
    client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers_a,
        json={"question_id": question_id, "choice_key": _wrong_key(db, question_id)},
    )
    client.post(f"/api/grammar/points/{point_id}/view", headers=headers_a, json={})

    # 账号 B 看不到 A 的任何数据
    outline_b = client.get("/api/grammar/outline", headers=headers_b).json()
    assert outline_b["mastered_count"] == 0
    assert outline_b["wrong_count"] == 0
    assert client.get("/api/grammar/wrong-points", headers=headers_b).json()["total"] == 0

    # B 操作 A 的轮次 → 404
    answer = client.post(
        f"/api/grammar/attempts/{attempt_id}/answer",
        headers=headers_b,
        json={"question_id": question_id, "choice_key": "A"},
    )
    assert answer.status_code == 404, answer.text
    assert answer.json()["error"]["code"] == "grammar_attempt_not_found"

    # A 的未结算轮次保持未完成
    unfinished = db.scalar(
        select(GrammarAttempt).where(GrammarAttempt.id == attempt_id)
    )
    assert unfinished.finished_at is None
    progress = db.scalar(
        select(GrammarPointProgress).where(
            GrammarPointProgress.user_id == unfinished.user_id,
            GrammarPointProgress.point_id == point_id,
        )
    )
    assert progress.status == "learning"
