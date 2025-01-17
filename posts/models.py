import uuid
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from authors.models import Author
from django.utils.translation import gettext_lazy as _
from django.urls import reverse 
from django.contrib.postgres import fields

from authors.models import InboxObject

class Post(models.Model):
    # https://docs.djangoproject.com/en/3.2/ref/models/fields/#enumeration-types
    class ContentType(models.TextChoices):
        MARKDOWN = 'text/markdown'
        PLAIN = 'text/plain'
        APPLICATION = 'application/base64'
        IMAGE_PNG = 'image/png;base64'
        IMAGE_JPEG = 'image/jpeg;base64'

    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC'
        FRIENDS = 'FRIENDS'
        PRIVATE = 'PRIVATE'

    id = models.CharField(primary_key=True, editable=False, max_length=500, default=uuid.uuid4)
    url = models.URLField(editable=False, max_length=500)
    author = models.ForeignKey(Author, related_name="post", on_delete=models.CASCADE)
    
    title = models.CharField(max_length=200) # title should not be super long
    source = models.URLField(editable=False, max_length=500)
    origin = models.URLField(editable=False, max_length=500)
    description = models.CharField(max_length = 200, blank=True, default="")
    content_type = models.CharField(max_length=30, choices=ContentType.choices, default=ContentType.PLAIN)
    content = models.TextField()
    published = models.DateTimeField(auto_now_add=True)
    unlisted = models.BooleanField(default=False)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)

    inbox_object = GenericRelation(InboxObject, related_query_name='post')
    is_github = models.BooleanField(default=False)

    # make the admin page looks pretty
    def __str__(self):
        return self.title + " (" + str(self.id) + ")"

    # This will return the label of the enum (e.g. "PUBLIC")
    # instead of the value of the enum (e.g. "PUB")
    def get_visilibility_label(self):
        return self.Visibility(self.visibility).label

    def get_content_type_label(self):
        return self.ContentType(self.content_type).label

    # used by serializer
    def get_public_id(self):
        return self.url or self.id

    @staticmethod
    def get_api_type():
        return 'post'

    # used internally
    def get_absolute_url(self):
        url = reverse('post-detail', args=[str(self.author.id), str(self.id)])
        return url[:-1] if url.endswith('/') else url # get rid of slash for url

    def get_image_url(self):
        return self.url.replace('/posts/', '/images/')

    def build_comments_url(self):
        if (self.url.endswith("/")):
            return self.url + "comments/"
        else:
            return self.url + "/comments/"

    def count_comments(self):
        return self.comment_set.count()

    # used by serializer
    def update_fields_with_request(self, request=None):
        if not request:
            return
        self.url = request.build_absolute_uri(self.get_absolute_url())
        self.host = request.build_absolute_uri('/') # points to the server root
        if not self.origin:
            self.origin = self.url
        if not self.source:
            self.source = self.url
        self.save()

class Comment(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=500, default=uuid.uuid4)
    url = models.URLField(editable=False, max_length=500)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment = models.TextField()
    published = models.DateTimeField(auto_now_add=True)

    content_type = models.CharField(max_length=30, choices=Post.ContentType.choices, default=Post.ContentType.PLAIN)

    # used by serializer
    def get_public_id(self):
        return self.url or self.id

    @staticmethod
    def get_api_type():
        return 'comment'

    # used internally
    def get_absolute_url(self):
        url = reverse(
            'comment-detail', 
            args=[
                str(self.post.author.id), 
                str(self.post.id),
                str(self.id)
            ]
        )
        return url[:-1] if url.endswith('/') else url # get rid of slash for url

    # used by serializer
    def update_fields_with_request(self, request):
        self.url = request.build_absolute_uri(self.get_absolute_url())
        self.save()

class Like(models.Model):
    summary = models.CharField(max_length=50)
    author = models.ForeignKey(Author, related_name = "likes", on_delete=models.CASCADE)
    # object can either be a post or comment
    object = models.URLField(max_length=500)

    inbox_object = GenericRelation(InboxObject, related_query_name='like')

    @staticmethod
    def get_api_type():
        return 'Like'

    # https://docs.djangoproject.com/en/3.2/ref/models/constraints/#django.db.models.UniqueConstraint
    class Meta:
        # ensure one author can only like a post or comment once
        constraints = [
            models.UniqueConstraint(fields=['author', 'object'], name='unique_like')
        ]
