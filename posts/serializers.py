from django.forms.models import model_to_dict
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from authors.models import Author

from .models import Post, Comment, Like
from authors.serializers import AuthorSerializer

class PostSerializer(serializers.ModelSerializer):
    # type is only provided to satisfy API format
    type = serializers.CharField(default="post", source="get_api_type", read_only=True)
    # public id should be the full url
    id = serializers.CharField(source="get_public_id", read_only=True)
    count = serializers.IntegerField(source="count_comments", read_only=True)
    published = serializers.DateTimeField(read_only=True)
    author = AuthorSerializer(required=False)
    comments = serializers.URLField(source="build_comments_url", read_only=True)

    # e.g. 'PUBLIC'
    visibility = serializers.ChoiceField(choices=Post.Visibility.choices)
    # e.g. 'text/markdown'
    contentType = serializers.ChoiceField(choices=Post.ContentType.choices, source='content_type')

    def create(self, validated_data):
        updated_author = AuthorSerializer.extract_and_upcreate_author(validated_data, author_id=self.context.get('author_id'))
        return Post.objects.create(**validated_data, author=updated_author)

    # TODO: missing the following fields
    # categories, size, comments (url), comments (Array of JSON)
    class Meta:
        model = Post
        # show these fields in response
        fields = [
            'type', 
            'title', 
            'id', 
            'source', 
            'origin', 
            'description',
            'contentType',
            'content',
            'author',
            # 'categories',
            'count',
            'comments',
            'published',
            'visibility',
            'unlisted',
        ]

class CommentSerializer(serializers.ModelSerializer):
    # type is only provided to satisfy API format
    type = serializers.CharField(default="comment", source="get_api_type", read_only=True)
    # public id should be the full url
    id = serializers.CharField(source="get_public_id", read_only=True)
    
    # author will be created and validated separately 
    author = AuthorSerializer(required=False)

    contentType = serializers.ChoiceField(choices=Post.ContentType.choices, source='content_type')

    class Meta:
        model = Comment
        fields = [
            "type",
            "author",
            "comment",
            "contentType",
            "published",
            "id"
        ]

class LikeSerializer(serializers.ModelSerializer):
    # type is only provided to satisfy API format
    type = serializers.CharField(default="Like", source="get_api_type", read_only=True)
    
    # author will be created and validated separately 
    author = AuthorSerializer(required=False)
    object = serializers.URLField()

    def create(self, validated_data):
        updated_author = AuthorSerializer.extract_and_upcreate_author(validated_data, author_id=self.context.get('author_id'))
        return Like.objects.create(**validated_data, author=updated_author)

    class Meta:
        model = Like
        fields = [
            "type",
            "summary",
            "author",
            "object",
        ]