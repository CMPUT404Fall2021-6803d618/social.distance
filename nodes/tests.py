
import json
import uuid
from django.test import TestCase, Client
from rest_framework.test import APIClient
from django.db.utils import IntegrityError

from django.contrib.auth.models import User
from authors.models import Author
from nodes.models import ConnectorService, connector_service
from posts.models import Post, Comment, Like

# Create your tests here.
client = APIClient() # the mock http client

class NodeTestCase(TestCase):
    def setUp(self):
        self.connector = connector_service

    def test_get_inbox_url_from_longer_url(self):
        host_url = "http://somehost/"
        inbox_url = host_url + "author/9de17f29c12e8f97bcbbd34cc908f1baba40658e/inbox/"
        post = host_url + "author/9de17f29c12e8f97bcbbd34cc908f1baba40658e/posts/764efa883dda1e11db47671c4a3bbd9e/"
        self.assertEqual(ConnectorService.get_inbox_and_host_from_url(post)[0], inbox_url)

    def test_get_host_url_from_longer_url(self):
        host_url = "http://somehost/"
        post = host_url + "author/9de17f29c12e8f97bcbbd34cc908f1baba40658e/posts/764efa883dda1e11db47671c4a3bbd9e/"
        self.assertEqual(ConnectorService.get_inbox_and_host_from_url(post)[1], host_url)