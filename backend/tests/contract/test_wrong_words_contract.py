"""错题本接口契约测试（contracts/api.md —— Wrong Words 段）。"""

from __future__ import annotations

import pytest

from tests.conftest import (
    auth_headers,
    register,
    today_word_ids,
    view_all_today,
    wrong_word_ids,
)

pytestmark = pytest.mark.contract


def test_empty_wrong_word_list_shape(client):
    token = register(client)["access_token"]

    response = client.get("/api/wrong-words", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1


def test_wrong_word_item_shape_after_wrong_answer(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()
    question = start["questions"][0]

    probe = client.post(
        "/api/quiz/today/answer",
        headers=headers,
        json={"question_id": question["question_id"], "choice_index": 0},
    ).json()
    if probe["is_correct"]:
        wrong_index = next(
            index for index in range(4) if index != probe["correct_index"]
        )
        client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": wrong_index},
        )

    response = client.get("/api/wrong-words", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    for key in ("word_id", "spelling", "meaning_zh", "phrase", "phonetic", "added_at"):
        assert key in item
    assert item["word_id"] == question["word_id"]
    assert item["added_at"]


def test_pagination_parameters_are_honoured(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    view_all_today(client, token)
    start = client.post("/api/quiz/today/start", headers=headers).json()

    for question in start["questions"]:
        probe = client.post(
            "/api/quiz/today/answer",
            headers=headers,
            json={"question_id": question["question_id"], "choice_index": 0},
        ).json()
        if probe["is_correct"]:
            wrong_index = next(
                index for index in range(4) if index != probe["correct_index"]
            )
            client.post(
                "/api/quiz/today/answer",
                headers=headers,
                json={
                    "question_id": question["question_id"],
                    "choice_index": wrong_index,
                },
            )

    first_page = client.get(
        "/api/wrong-words?page=1&page_size=5", headers=headers
    ).json()
    assert first_page["page_size"] == 5
    assert len(first_page["items"]) == 5
    assert first_page["total"] == 20

    # 列表顺序按加入时间升序（非 word_id 升序）；两次查询结果稳定
    listed = wrong_word_ids(client, token)
    assert len(listed) == 20
    assert listed == wrong_word_ids(client, token)
    added_times = [
        item["added_at"] for item in client.get("/api/wrong-words", headers=headers).json()["items"]
    ]
    assert added_times == sorted(added_times)
