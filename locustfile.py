from locust import HttpUser, task, between

# Тот самый BMC_URL
BMC_URL = "https://127.0.0.1:2443"
BMC_USER = "root"
BMC_PASSWORD = "0penBmc"


class OpenBMCUser(HttpUser):
    """Нагрузка на OpenBMC Redfish API."""
    host = BMC_URL  # Использует переменную

    def on_start(self):
        """Логин при старте пользователя — получаем токен сессии."""
        with self.client.post(
            "/redfish/v1/SessionService/Sessions",
            json={"UserName": BMC_USER, "Password": BMC_PASSWORD},
            verify=False,
            catch_response=True,
            name="POST /Sessions (login)",
        ) as response:
            if response.status_code in (200, 201):
                self.token = response.headers.get("X-Auth-Token")
                self.location = response.headers.get("Location")
                response.success()
            else:
                self.token = None
                response.failure("Login failed: " + str(response.status_code))

    def on_stop(self):
        """Разлогин при остановке пользователя."""
        if getattr(self, "token", None) and getattr(self, "location", None):
            self.client.delete(
                self.location,
                headers={"X-Auth-Token": self.token},
                verify=False,
                name="DELETE /Sessions (logout)",
            )

    @task(3)
    def get_system_info(self):
        """GET информации о системе."""
        if not self.token:
            return
        self.client.get(
            "/redfish/v1/Systems/system",
            headers={"X-Auth-Token": self.token},
            verify=False,
            name="GET /Systems/system",
        )

    @task(1)
    def get_power_state(self):
        """GET состояния питания (проверяем, что поле PowerState есть)."""
        if not self.token:
            return
        with self.client.get(
            "/redfish/v1/Systems/system",
            headers={"X-Auth-Token": self.token},
            verify=False,
            catch_response=True,
            name="GET /Systems/system (PowerState)",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "PowerState" not in data:
                    response.failure("Нет поля PowerState")
                else:
                    response.success()
            else:
                response.failure("Код " + str(response.status_code))


class PublicAPIUser(HttpUser):
    """Нагрузка на публичное API JSONPlaceholder."""
    host = "https://jsonplaceholder.typicode.com"  # Жестко заданный хост

    @task(3)
    def get_posts(self):
        """GET списка постов."""
        self.client.get(
            "/posts", # Относительный путь, склеится с host
            name="GET /posts (JSONPlaceholder)",
        )

    @task(1)
    def get_single_post(self):
        """GET одного поста."""
        self.client.get(
            "/posts/1", # Относительный путь, склеится с host
            name="GET /posts/1 (JSONPlaceholder)",
        )
