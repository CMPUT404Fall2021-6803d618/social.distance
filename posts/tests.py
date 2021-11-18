import json
import tempfile
import uuid
from django.test import TestCase, Client
from rest_framework.test import APIClient
from django.db.utils import IntegrityError

from django.contrib.auth.models import User
from authors.models import Author
from authors.tests import client_with_auth
from posts.models import Post, Comment, Like
from PIL import Image

# Create your tests here.
client = APIClient() # the mock http client

class PostDetailTestCase(TestCase):
    def setup_objects(self):
        self.user = User.objects.create_superuser('test_username', 'test_email', 'test_pass')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(user=self.user, display_name=self.user.username)
        self.post = Post.objects.create(
            author = self.author,
            title = "test_title",
            description = "test_description",
            content_type = "text/plain",
            content = "test_content",
            visibility = "PUBLIC"
        )
        
    def test_get_post_normal(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/', format='json')
        content = json.loads(res.content)
    
        self.assertEqual(res.status_code, 200)
        self.assertEqual(content['type'], "post")
        self.assertEqual(content['id'], str(self.post.id))
        self.assertEqual(content['title'], 'test_title')
        self.assertEqual(content['description'], 'test_description')
        self.assertEqual(content['contentType'], 'text/plain')
        self.assertEqual(content['content'], 'test_content')
        self.assertEqual(content['visibility'], 'PUBLIC')

    def test_get_post_not_exist(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/this-id-does-not-exist/', format='json')
        assert res.status_code == 404
    
    def test_get_post_private(self):
        self.setup_objects()
        self.post.visibility = "PRIVATE"
        self.post.save()
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/', format='json')
        assert res.status_code == 200

        another_user = User.objects.create_superuser('test_username1', 'test_email', 'test_pass123')
        self.client = client_with_auth(another_user, self.client)
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/', format='json')
        assert res.status_code == 403

    def test_update_post_normal(self):
        self.setup_objects()
        update_data = {
            'title': 'updated_title',
            'description': 'updated_description',
            'contentType': 'text/markdown'
        }
        res = self.client.post(
            f'/author/{self.author.id}/posts/{self.post.id}/', 
            update_data,
            format='json'
        )
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(content['title'], 'updated_title')
        self.assertEqual(content['description'], 'updated_description')
        self.assertEqual(content['contentType'], 'text/markdown')

    def test_update_post_not_exist(self):
        self.setup_objects()
        res = self.client.post(f'/author/{self.author.id}/posts/this-id-does-not-exist/', format='json')
        assert res.status_code == 404
    
    def test_update_post_invalid_entry(self):
        self.setup_objects()
        update_data = {
            # this content type is invalid
            'contentType': 'text/html'
        }
        res = self.client.post(
            f'/author/{self.author.id}/posts/{self.post.id}/', 
            update_data,
            format='json'
        )
        # should return a bad request
        self.assertEqual(res.status_code, 400)

    def test_delete_post_normal(self):
        self.setup_objects()
        res = client.delete(f'/author/{self.author.id}/posts/{self.post.id}/', format='json')
        self.assertEqual(res.status_code, 204)
        
        # test whether we can get the post after the DELETE request
        self.assertRaises(Post.DoesNotExist, lambda: Post.objects.get(pk=self.post.id))

    def test_delete_post_not_exist(self):
        self.setup_objects()
        res = client.delete(f'/author/{self.author.id}/posts/this-id-does-not-exist/', format='json')
        self.assertEqual(res.status_code, 404)

    def test_put_post_normal(self):
        self.setup_objects()
        new_post_id = str(uuid.uuid4())
        put_data = {
            "title": "new_title",
            "description": "new_description",
            "contentType": "application/base64",
            "content": "new_content",
            "visibility": "PUBLIC",
            "unlisted": True
        }
        res = client.put(
            f'/author/{self.author.id}/posts/{new_post_id}/',
            put_data,
            format='json'
        )
        self.assertEqual(res.status_code, 200)

        new_post = Post.objects.get(pk=new_post_id)
        self.assertEqual(new_post.title, put_data["title"])
        self.assertEqual(new_post.description, put_data["description"])
        self.assertEqual(new_post.content_type, put_data["contentType"])
        self.assertEqual(new_post.content, put_data["content"])
        self.assertEqual(new_post.visibility, put_data["visibility"])
        self.assertEqual(new_post.unlisted, True)
        self.assertEqual(new_post.author.id, str(self.author.id))
    
    def test_put_post_conflict(self):
        self.setup_objects()
        put_data = {
            "title": "new_title",
            "description": "new_description",
            "contentType": "application/base64",
            "content": "new_content",
            "visibility": "PUBLIC",
            "unlisted": True
        }
        # here I'm trying to create a post with existing post id
        res = client.put(
            f'/author/{self.author.id}/posts/{self.post.id}/',
            put_data,
            format='json'
        )
        self.assertEqual(res.status_code, 409)
    
    def test_put_post_invalid_author(self):
        self.setup_objects()
        new_post_id = str(uuid.uuid4())
        random_author_id = str(uuid.uuid4())
        put_data = {
            "title": "new_title",
            "description": "new_description",
            "contentType": "application/base64",
            "content": "new_content",
            "visibility": "PUBLIC",
            "unlisted": True
        }
        # here I'm trying to create a post 
        # with a random invalid author id
        res = client.put(
            f'/author/{random_author_id}/posts/{new_post_id}/',
            put_data,
            format='json'
        )
        self.assertEqual(res.status_code, 404)

    def test_put_post_invalid_entry(self):
        self.setup_objects()
        new_post_id = str(uuid.uuid4())
        # here unlisted as string is invalid
        put_data = {
            "title": "new_title",
            "description": "new_description",
            "contentType": "application/base64",
            "content": "new_content",
            "visibility": "PUBLIC",
            "unlisted": "True and False"
        }
        res = client.put(
            f'/author/{self.author.id}/posts/{new_post_id}/', 
            put_data,
            format='json'
        )
        # should return a bad request
        self.assertEqual(res.status_code, 400 )

class PostListTestCase(TestCase):
    def setup_objects(self):
        self.user = User.objects.create_superuser('test_username', 'test_email', 'test_pass')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(user=self.user, display_name=self.user.username)
        self.post1 = Post.objects.create(
            author = self.author,
            title = "test_title1",
            description = "test_description2",
            content_type = "text/plain",
            content = "test_content1",
            visibility = "PUBLIC"
        )
        self.post2 = Post.objects.create(
            author = self.author,
            title = "test_title2",
            description = "test_description2",
            content_type = "text/plain",
            content = "test_content2",
            visibility = "PUBLIC"
        )
    
    def test_get_posts_normal(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/', format='json')
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        assert ("items" in content)
        self.assertEqual(len(content["items"]), 2)

    def test_get_posts_invalid_author(self):
        self.setup_objects()
        res = self.client.get(f'/author/does-not-exist/posts/', format='json')
        assert res.status_code == 404

class CommentListTestCase(TestCase):
    def setup_objects(self):
        self.user = User.objects.create_superuser('test_username', 'test_email', 'test_pass')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(user=self.user, display_name=self.user.username)
        self.post = Post.objects.create(
            author = self.author,
            title = "test_title",
            description = "test_description",
            content_type = "text/plain",
            content = "test_content",
            visibility = "PUBLIC"
        )
        self.comment1 = Comment.objects.create(
            post = self.post,
            author = self.author,
            comment = "test_comment1",
            content_type = "text/plain"
        )
        self.comment2 = Comment.objects.create(
            post = self.post,
            author = self.author,
            comment = "test_comment2",
            content_type = "text/plain"
        )
        self.payload = {
            "author": {
                "displayName": "test",
                "github": "https://github.com/test",
                "host": "http://127.0.0.1:8000/register/",
                "id": self.author.id,
                "type": "author",
                "url": f"http://127.0.0.1:8000/author/{self.author.id}/"
            },
            "comment": "post_comment",
            "contentType": "text/markdown"
        }
    
    def test_get_comment_normal(self):
        self.setup_objects()
        res = self.client.get(
            f'/author/{self.author.id}/posts/{self.post.id}/comment/{self.comment1.id}/', 
            format='json'
        )
        content = json.loads(res.content)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(str(content["id"]), str(self.comment1.id))

    def test_get_comment_not_found(self):
        self.setup_objects()
        res = self.client.get(
            f'/author/{self.author.id}/posts/{self.post.id}/comment/not-found/', 
            format='json'
        )
        self.assertEqual(res.status_code, 404)
    
    def test_get_comments_normal(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/comments/', format='json')
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        assert ("comments" in content)
        self.assertEqual(len(content["comments"]), 2)

    def test_get_comments_paginated_normal(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/comments/?page=1&size=1', format='json')
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        assert ("comments" in content)
        self.assertEqual(len(content["comments"]), 1)
    
    def test_get_comments_paginated_404(self):
        self.setup_objects()
        # we only have 2 comments, page 3 size 1 should return 404
        res = self.client.get(f'/author/{self.author.id}/posts/{self.post.id}/comments/?page=3&size=1', format='json')
        assert res.status_code == 404

    def test_get_comments_invalid_post(self):
        self.setup_objects()
        res = self.client.get(f'/author/{self.author.id}/posts/does-not-exist/comments/', format='json')
        assert res.status_code == 404

    def test_post_comments_normal(self):
        self.setup_objects()
        
        res = self.client.post(
            f'/author/{self.author.id}/posts/{self.post.id}/comments/',
            self.payload,
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(Comment.objects.all()), 3)

    def test_post_comments_invalid_id(self):
        self.setup_objects()

        # invalid post id 
        res = self.client.post(
            f'/author/{self.author.id}/posts/does-not-exist/comments/',
            self.payload,
            format="json"
        )
        self.assertEqual(res.status_code, 404)

        # invalid author id 
        res = self.client.post(
            f'/author/does-not-exist/posts/{self.post.id}/comments/',
            self.payload,
            format="json"
        )
        self.assertEqual(res.status_code, 404)

    
    def test_post_comments_invalid_payload(self):
        self.setup_objects()
        self.payload["author"].pop("id")

        res = self.client.post(
            f'/author/{self.author.id}/posts/{self.post.id}/comments/',
            self.payload,
            format="json"
        )
        self.assertEqual(res.status_code, 400)
    
    def test_post_comments_foreign_author(self):
        self.setup_objects()
        self.payload["author"]["id"] = self.payload["author"]["url"]

        res = self.client.post(
            f'/author/{self.author.id}/posts/{self.post.id}/comments/',
            self.payload,
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(Comment.objects.all()), 3)
        assert len(Author.objects.filter(url=self.payload["author"]["url"])) == 1

class LikeTestCase(TestCase):
    def setup_objects(self):
        self.user = User.objects.create_superuser('test_username', 'test_email', 'test_pass')
        self.user2 = User.objects.create_superuser('test_username2', 'test_email2', 'test_pass2')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(user=self.user, display_name=self.user.username)
        self.author2 = Author.objects.create(user=self.user2, display_name=self.user2.username)
        self.post = Post.objects.create(
            author = self.author,
            title = "test_title",
            description = "test_description",
            content_type = "text/plain",
            content = "test_content",
            visibility = "PUBLIC"
        )
        self.comment = Comment.objects.create(
            post = self.post,
            author = self.author,
            comment = "test_comment1",
            content_type = "text/plain"
        )

    def setup_likes(self, like_object):
        self.like1 = Like.objects.create(
            summary = "test_like1",
            author = self.author,
            object = like_object
        )

        self.like2 = Like.objects.create(
            summary = "test_like2",
            author = self.author2,
            object = like_object
        )
    
    def test_likes_post_normal(self):
        self.setup_objects()
        self.setup_likes(self.post.url)

        res = self.client.get(
            f'/author/{self.author.id}/post/{self.post.id}/likes/',
            format="json"
        )
        content = json.loads(res.content)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(content), 2)
    
    def test_likes_post_invalid_post(self):
        self.setup_objects()
        self.setup_likes(self.post.url)

        res = self.client.get(
            f'/author/{self.author.id}/post/does-not-exist/likes/',
            format="json"
        )
        self.assertEqual(res.status_code, 404)
    
    def test_likes_comment_normal(self):
        self.setup_objects()
        self.setup_likes(self.comment.url)

        res = self.client.get(
            f'/author/{self.author.id}/post/{self.post.id}/comments/{self.comment.id}/likes/',
            format="json"
        )
        content = json.loads(res.content)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(content), 2)

    def test_likes_comment_invalid_comment(self):
        self.setup_objects()
        self.setup_likes(self.comment.url)

        res = self.client.get(
            f'/author/{self.author.id}/post/{self.post.id}/comments/does-not-exist/likes/',
            format="json"
        )
        self.assertEqual(res.status_code, 404)
    
    def test_liked_normal(self):
        self.setup_objects()
        self.setup_likes(self.post.url)
        res = self.client.get(
            f'/author/{self.author.id}/liked/',
            format="json"
        )
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        assert "items" in content
        self.assertEqual(len(content["items"]), 1)
        self.assertEqual(content["items"][0]["object"], self.like1.object)

        res = self.client.get(
            f'/author/{self.author2.id}/liked/',
            format="json"
        )
        content = json.loads(res.content)
        self.assertEqual(res.status_code, 200)
        assert "items" in content
        self.assertEqual(len(content["items"]), 1)
        self.assertEqual(content["items"][0]["object"], self.like2.object)

    def test_liked_invalid_author(self): 
        self.setup_objects()
        self.setup_likes(self.post.url)

        res = self.client.get(
            f'/author/does-not-exist/liked/',
            format="json"
        )
        self.assertEqual(res.status_code, 404)
    
    def test_setup_duplicate_like(self):
        self.setup_objects()
        try:
            # setup two likes with same author on the same object
            self.like1 = Like.objects.create(
                summary = "duplicate_like1",
                author = self.author,
                object = self.post.url
            )

            self.like2 = Like.objects.create(
                summary = "duplicate_like2",
                author = self.author,
                object = self.post.url
            )
            assert False
        except IntegrityError:
            # should fail because of the UniqueConstraint
            # set in the models
            assert True

class ImageUploadTestCase(TestCase):
    file_in_bytes = b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBAMAAADsEZWCAAAAG1BMVEXMzMyWlpaqqqq3t7exsbGcnJy+vr6jo6PFxcUFpPI/AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAQUlEQVQ4jWNgGAWjgP6ASdncAEaiAhaGiACmFhCJLsMaIiDAEQEi0WXYEiMCOCJAJIY9KuYGTC0gknpuHwXDGwAA5fsIZw0iYWYAAAAASUVORK5CYII="
    def setup_objects(self):
        self.user = User.objects.create_superuser('test_username', 'test_email', 'test_pass')
        self.client = client_with_auth(self.user, client)
        self.author = Author.objects.create(user=self.user, display_name=self.user.username)

        # https://stackoverflow.com/a/39775556
        image = Image.new('RGB', (60, 30), color = 'red')
        f = tempfile.NamedTemporaryFile(suffix='.png')
        image.save(f)
        self.image_file = f

    def test_upload_image_normal(self):
        self.setup_objects()
        with open(self.image_file.name, 'rb') as f:
            res = self.client.post(
                f'/author/{self.author.id}/images/',
                {
                    "image": f
                },)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f"{self.author.url}images/" in res.json()["url"])
        self.assertEqual(Post.objects.get(author=self.author).url, res.json()["url"].replace('images', 'posts'))
        self.assertEqual(Post.objects.get(author=self.author).visibility, Post.Visibility.PUBLIC)
        self.assertEqual(Post.objects.get(author=self.author).unlisted, True)

    def test_upload_image_not_unlisted(self):
        self.setup_objects()
        with open(self.image_file.name, 'rb') as f:
            res = self.client.post(
                f'/author/{self.author.id}/images/',
                {
                    "image": f,
                    "unlisted": False
                },)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f"{self.author.url}images/" in res.json()["url"])
        self.assertEqual(Post.objects.get(author=self.author).url, res.json()["url"].replace('images', 'posts'))
        self.assertEqual(Post.objects.get(author=self.author).visibility, Post.Visibility.PUBLIC)
        self.assertEqual(Post.objects.get(author=self.author).unlisted, False)

    def test_upload_image_PRIVATE(self):
        self.setup_objects()
        with open(self.image_file.name, 'rb') as f:
            res = self.client.post(
                f'/author/{self.author.id}/images/',
                {
                    "image": f,
                    "visibility": "PRIVATE",
                },)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f"{self.author.url}images/" in res.json()["url"])
        self.assertEqual(Post.objects.get(author=self.author).url, res.json()["url"].replace('images', 'posts'))
        self.assertEqual(Post.objects.get(author=self.author).visibility, Post.Visibility.PRIVATE)
        self.assertEqual(Post.objects.get(author=self.author).unlisted, True)
