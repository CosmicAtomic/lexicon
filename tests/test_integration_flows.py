import pytest
from app.models.post import Post
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_create_post_and_fetch_it(client, auth_headers):
    create_resp = await client.post("v1/posts", json= {"title": "My First Post", "body": "Hello World"}, headers =auth_headers)
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    fetch_resp = await client.get(f"v1/posts/{post_id}")
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["title"] == "My First Post"

@pytest.mark.asyncio
async def test_paginated_posts_list(client, auth_headers):
    for i in range(15):
        await client.post("v1/posts", json= {"title": f"Post{i}", "body": "body"}, headers =auth_headers)

    page_1 = await client.get("v1/posts", params= {"limit": 10, "page": 1})
    page_2 = await client.get("v1/posts", params= {"limit": 10, "page": 2})
    assert page_1.status_code == 200
    assert page_2.status_code == 200
    assert len(page_1.json()["posts"]) == 10
    assert len(page_2.json()["posts"]) == 5

@pytest.mark.asyncio
async def test_filter_posts_by_author(client, auth_headers, other_auth_headers):
    myPost = await client.post("v1/posts", json={"title": "Mine", "body": "body"}, headers = auth_headers)
    my_post = myPost.json()
    await client.post("v1/posts", json={"title": "Not mine", "body": "body"}, headers= other_auth_headers)

    resp = await client.get("v1/posts", params={"author_id": my_post["author_id"]})
    assert resp.status_code == 200

    returned_ids = {p["id"] for p in resp.json()["posts"]}
    assert my_post["id"] in returned_ids
    assert all(p["author_id"] == my_post["author_id"] for p in resp.json()["posts"])


@pytest.mark.asyncio
@patch("app.routes.comment.httpx2.AsyncClient") 
async def test_comment_creation_fires_webhook(mock_client_class, client, auth_headers):
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_instance.post.return_value = mock_response

    post_resp = await client.post(
        "v1/posts", 
        json={"title": "Post for comment", "body": "body"}, 
        headers=auth_headers
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"v1/posts/{post_id}/comments", 
        json={"body": "Nice Post"}, 
        headers=auth_headers
    )
    assert comment_resp.status_code == 201

    mock_instance.post.assert_called_once()
    sent_payload = mock_instance.post.call_args.kwargs.get("json")
    assert sent_payload["body"] == "Nice Post"
    assert sent_payload["post_id"] == post_id


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_does_not_create_second_post(client, auth_headers, db_session):
    headers = {**auth_headers, "Idempotency-Key": "test-key-123"}

    first = await client.post(
        "/v1/posts",
        json={"title": "Idempotent post", "body": "body"},
        headers=headers,
    )
    second = await client.post(
        "/v1/posts",
        json={"title": "Idempotent post", "body": "body"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()

    matching_posts = (
        db_session.query(Post).filter(Post.title == "Idempotent post").all()
    )
    assert len(matching_posts) == 1

