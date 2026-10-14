import random

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from game import lobby


@pytest.fixture
def host(db):
    return get_user_model().objects.create_superuser("host", password="secret")


@pytest.fixture
def seeded(db):
    call_command("seed", stdout=None)


@pytest.fixture
def game(host):
    return lobby.create_game(host, max_players=4)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def host_api(host):
    client = APIClient()
    client.force_authenticate(host)
    return client


@pytest.fixture
def rnd():
    return random.Random(1)
