import json
from copy import deepcopy
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from authors.models import Author, Follow, InboxObject
from authors.serializers import AuthorSerializer, FollowSerializer

# Create your tests here.

client = APIClient()  # the mock http client
factory = APIRequestFactory()


def client_with_auth(user, client):
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


class FollowTestCase(TestCase):
    DATA = {
        "type": "Follow",
        "summary": "Greg wants to follow Lara",
        "actor": {
            "type": "author",
            "id": "http://127.0.0.1:5454/author/1d698d25ff008f7538453c120f581471",
            "url": "http://127.0.0.1:5454/author/1d698d25ff008f7538453c120f581471",
            "host": "http://127.0.0.1:5454/",
            "displayName": "Greg Johnson",
            "github": "http://github.com/gjohnson",
            "profileImage": "https://i.imgur.com/k7XVwpB.jpeg"
        },
        "object": {
            "type": "author",
            "id": "http://127.0.0.1:5454/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e",
            "host": "http://127.0.0.1:5454/",
            "displayName": "Lara Croft",
            "url": "http://127.0.0.1:5454/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e",
            "github": "http://github.com/laracroft",
            "profileImage": "https://i.imgur.com/k7XVwpB.jpeg"
        }
    }

    def setUp(self):
        # create an object author first, mock an existing local author
        local_author = deepcopy(self.DATA['object'])
        local_author['id'] = '9de17f29c12e8f97bcbbd34cc908f1baba40658e'
        self.user = User.objects.create_superuser(
            'test_user', 'test_email', 'test_pass')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(id='9de17f29c12e8f97bcbbd34cc908f1baba40658e',
                                            url='http://127.0.0.1:5454/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e',
                                            display_name='Lara Croft',
                                            github_url='http://github.com/laracroft',
                                            profile_image='https://i.imgur.com/k7XVwpB.jpeg',
                                            host='http://127.0.0.1:5454/',
                                            user=self.user,
                                            is_internal=True)

    def test_deserializing_friend_request(self):
        # try parse the data
        serialzier = FollowSerializer(data=deepcopy(self.DATA))
        if not serialzier.is_valid():
            print(serialzier.errors)
        assert serialzier.is_valid()
        f = serialzier.save()
        self.assertEqual(f.actor.display_name,
                         self.DATA['actor']['displayName'])
        self.assertEqual(f.object.display_name,
                         self.DATA['object']['displayName'])

    def test_inbox_post(self):
        user = User.objects.get(username='test_user')
        new_client = client_with_auth(user, client)
        _ = new_client.post(
            '/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e/inbox/', data=self.DATA, format='json')

        inbox_items = new_client.get(
            '/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e/inbox/', format='json')
        items = inbox_items.data.get('items')
        self.assertEqual(len(items), 1)

        status = items[0].pop('status')
        self.assertEqual(status, Follow.FollowStatus.PENDING)

        inbox_object_id = items[0].pop('inbox_object')
        inbox_object_in_db = InboxObject.objects.get(id=inbox_object_id)
        self.assertIsNotNone(inbox_object_in_db)
        self.assertDictContainsSubset(self.DATA['actor'], items[0]['actor'])
        self.assertDictContainsSubset(self.DATA['object'], items[0]['object'])

        local_author = Author.objects.get(
            id='9de17f29c12e8f97bcbbd34cc908f1baba40658e')
        self.assertEqual(len(local_author.inbox_objects.all()), 1)


class AuthorSerializerTestCase(TestCase):
    # mock the raw requests.data['actor'] dict, not validated yet.
    FOREIGN_AUTHOR_A_DATA = {
        'type': 'author',
        'id': 'http://localhost:8001/author/123321123321',
        'url': 'http://localhost:8001/author/123321123321',
        'host': 'http://localhost:8001/',
        'displayName': 'Foreign Author A',
        'github': 'https://github.com/asasdf@#$!d'
    }

    FOREIGN_AUTHOR_B_DATA = {
        'type': 'author',
        'id': 'http://localhost:8001/author/123321123321',
        'url': 'http://localhost:8001/author/123321123321',
        'host': 'http://localhost:8001/',
        'displayName': 'Foreign Author B'
    }

    def test_create_external_author_object_happy(self):
        foreign_author_data = self.FOREIGN_AUTHOR_A_DATA

        s = AuthorSerializer(data=foreign_author_data)

        assert s.is_valid()
        foreign_author = s.save()  # an Author object

        fake_response = AuthorSerializer(foreign_author).data

        self.assertEqual(fake_response['id'],
                         self.FOREIGN_AUTHOR_A_DATA['url'])
        self.assertEqual(foreign_author.url, self.FOREIGN_AUTHOR_A_DATA['url'])
        self.assertEqual(foreign_author.display_name,
                         self.FOREIGN_AUTHOR_A_DATA['displayName'])
        self.assertEqual(foreign_author.host,
                         self.FOREIGN_AUTHOR_A_DATA['host'])
        self.assertEqual(foreign_author.github_url,
                         self.FOREIGN_AUTHOR_A_DATA['github'])
        assert foreign_author.user is None

    def test_create_external_author_object_bare(self):
        foreign_author_data = self.FOREIGN_AUTHOR_B_DATA

        s = AuthorSerializer(data=foreign_author_data)
        if not s.is_valid():
            print(s.errors)
        assert s.is_valid()
        foreign_author = s.save()  # an Author object

        fake_response = AuthorSerializer(foreign_author).data

        self.assertEqual(fake_response['id'],
                         self.FOREIGN_AUTHOR_A_DATA['url'])
        self.assertEqual(foreign_author.url, self.FOREIGN_AUTHOR_B_DATA['url'])
        self.assertEqual(foreign_author.host,
                         self.FOREIGN_AUTHOR_B_DATA['host'])
        self.assertEqual(foreign_author.display_name,
                         self.FOREIGN_AUTHOR_B_DATA['displayName'])
        assert foreign_author.user is None


class AuthorTestCase(TestCase):
    def setup_single_user_and_author(self):
        self.user = User.objects.create_user(
            'test_username', 'test_email', 'test_pass')
        self.author = Author.objects.create(
            user=self.user, display_name=self.user.username, is_internal=True)

    def setUp(self):
        pass

    def test_get_author_list(self):
        self.setup_single_user_and_author()
        res = client.get('/authors/', format='json')
        res_content = json.loads(res.content)
        assert "items" in res_content
        content = res_content["items"]

        # content should look like [{'id': 'adfsadfasdfasdf', 'displayName': 'test_username', 'url': '', 'host': '', 'user': 1, 'friends': []}]
        self.assertEqual(len(content), 1)

        # API fields as per spec, not model fields.
        self.assertEqual(content[0]['displayName'], 'test_username')
        self.assertEqual(content[0]['id'], str(self.author.id))
        self.assertEqual(res.status_code, 200)

    def test_get_author_detail(self):
        self.setup_single_user_and_author()
        res = client.get(f'/author/{self.author.id}/', format='json')
        content = json.loads(res.content)

        # content should look like {'id': 'adfsadfasdfasdf', 'displayName': 'test_username', 'url': '', 'host': '', 'user': 1, 'friends': []}
        self.assertEqual(content['displayName'], 'test_username')
        self.assertEqual(content['id'], str(self.author.id))
        self.assertEqual(res.status_code, 200)

    def test_update_author_detail(self):
        # first register a user
        register_payload = {
            'username': 'test_register_simple_happy',
            'password': ';askdjfxzc0-v8923k5jm0-Z*xklcasxcKLjKj()*^$!^',
        }
        res = client.post('/register/', register_payload, format='json')
        '''
        expected sample response
        {
            "displayName": "LUcasdf",
            "github": "https://github.com/asdf",
            "host": "http://127.0.0.1:8000/register/",
            "id": "http://127.0.0.1:8000/author/8d2718f8-a957-418c-b826-f51bbb34f57f/",
            "type": "author",
            "url": "http://127.0.0.1:8000/author/8d2718f8-a957-418c-b826-f51bbb34f57f/"
        }
        '''
        self.assertEqual(res.data['author']['displayName'],
                         register_payload['username'])
        self.assertTrue(res.data['author']['id'] == res.data['author']
                        ['url'] and res.data['author']['id'].startswith('http'))
        self.assertEqual(res.data['author']['type'], 'author')
        assert res.data['author']['github'] is None
        self.assertEqual(res.status_code, 200)

        # assert user is created correctly
        user = User.objects.get(username=register_payload['username'])
        assert user is not None

        # authenticate with jwt token
        authed_client = client_with_auth(user, client)
        # update details
        payload = {
            'displayName': 'Test Name',
            'github': 'https://github.com/asdfas'
        }
        res = authed_client.post(
            res.data['author']['id'], payload, format='json')
        self.assertEqual(res.data['displayName'], payload['displayName'])
        self.assertEqual(res.data['github'], payload['github'])

    def test_local_author_is_internal(self):
        self.setup_single_user_and_author()
        self.assertTrue(self.author.is_internal)

    def test_foreign_author_is_not_internal(self):
        foreign_author_data = AuthorSerializerTestCase.FOREIGN_AUTHOR_A_DATA
        s = AuthorSerializer(data=foreign_author_data)
        assert s.is_valid()
        foreign_author = s.save()  # an Author object
        self.assertFalse(foreign_author.is_internal)
