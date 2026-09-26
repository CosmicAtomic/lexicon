import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
@patch("app.routes.comment.httpx2.AsyncClient") 
async def test_full_user_journey(mock_client_class, client):
    #Set up webhook mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_instance.post.return_value = mock_response

    # User signs up
    user_details = {"email": "test_e2e@example.com","username": "e2e_test_user", "password": "supersecret123"}
    signup_resp = await client.post('v1/auth/signup', json=user_details)
    assert signup_resp.status_code == 201
    
    # User logins in
    login_response = await client.post('v1/auth/jwt/login', json=user_details)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # User creates a post
    create_post_resp= await client.post(
        "v1/posts", 
        json= {"title": "User Post Title", "body": "User Post Body"}, 
        headers =auth_header
    )
    assert create_post_resp.status_code == 201
    post_id = create_post_resp.json()["id"]

    # User fetches post
    fetch_post_resp = await client.get(f"v1/posts/{post_id}")
    assert fetch_post_resp.json()["title"] == "User Post Title"

    # User creates comment
    create_comment_resp = await client.post(
            f"v1/posts/{post_id}/comments", 
            json={"body": "User Comment Body"}, 
            headers=auth_header
        )
    assert create_comment_resp.status_code == 201

    # Confirm webhook fired
    mock_instance.post.assert_called_once()
    sent_payload = mock_instance.post.call_args.kwargs.get("json")
    assert sent_payload["body"] == "User Comment Body"
    assert sent_payload["post_id"] == post_id