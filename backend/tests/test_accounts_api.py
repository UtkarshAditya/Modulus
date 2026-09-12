import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import EmployerFactory

pytestmark = pytest.mark.django_db


def test_csrf_endpoint_sets_cookie():
    client = APIClient()
    response = client.get(reverse("auth-csrf"))
    assert response.status_code == 200
    assert "csrftoken" in response.cookies


def test_me_when_anonymous():
    client = APIClient()
    response = client.get(reverse("auth-me"))
    assert response.status_code == 200
    assert response.data == {"authenticated": False}


def test_signup_creates_employer_and_logs_in():
    client = APIClient(enforce_csrf_checks=False)
    response = client.post(
        reverse("auth-signup"),
        {"username": "newgrad", "email": "newgrad@example.com", "password": "correct-horse-battery"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["username"] == "newgrad"
    assert response.data["role"] == "EMPLOYER"

    me = client.get(reverse("auth-me"))
    assert me.data["authenticated"] is True
    assert me.data["username"] == "newgrad"


def test_signup_rejects_duplicate_username():
    EmployerFactory(username="taken")
    client = APIClient(enforce_csrf_checks=False)
    response = client.post(
        reverse("auth-signup"),
        {"username": "taken", "email": "someone-else@example.com", "password": "correct-horse-battery"},
        format="json",
    )
    assert response.status_code == 400
    assert "username" in response.data


def test_signup_rejects_weak_password():
    client = APIClient(enforce_csrf_checks=False)
    response = client.post(
        reverse("auth-signup"),
        {"username": "weakpass", "email": "weakpass@example.com", "password": "password"},
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.data


def test_login_with_valid_credentials():
    EmployerFactory(username="alice")
    client = APIClient(enforce_csrf_checks=False)
    response = client.post(
        reverse("auth-login"), {"username": "alice", "password": "password123!"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["username"] == "alice"
    assert response.data["role"] == "EMPLOYER"

    me = client.get(reverse("auth-me"))
    assert me.data["authenticated"] is True
    assert me.data["username"] == "alice"


def test_login_with_invalid_credentials():
    EmployerFactory(username="bob")
    client = APIClient(enforce_csrf_checks=False)
    response = client.post(
        reverse("auth-login"), {"username": "bob", "password": "wrong"}, format="json"
    )
    assert response.status_code == 401


def test_logout_clears_session():
    EmployerFactory(username="carol")
    client = APIClient(enforce_csrf_checks=False)
    client.post(
        reverse("auth-login"), {"username": "carol", "password": "password123!"}, format="json"
    )
    assert client.get(reverse("auth-me")).data["authenticated"] is True

    response = client.post(reverse("auth-logout"))
    assert response.status_code == 204
    assert client.get(reverse("auth-me")).data["authenticated"] is False
