from locust import HttpUser, task, between

# Run with: locust -f performance/locustfile.py --host http://localhost:8000

class ApiUser(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def login(self):
        self.client.post(
            "/v1/auth/jwt/login", 
            json={
                "email": "user@example.com",
                "username": "test_user",
                "password": "string"
            }
        )

    @task(5)
    def list_posts(self):
        self.client.get("/v1/posts")