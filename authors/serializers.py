import uuid
from django.forms.models import model_to_dict
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from rest_framework import exceptions, serializers

from .models import Author, Follow, InboxObject


class AuthorSerializer(serializers.ModelSerializer):
    # type is only provided to satisfy API format
    type = serializers.CharField(default="author", read_only=True)
    # public id should be the full url
    id = serializers.CharField()
    displayName = serializers.CharField(
        source='display_name', required=False, allow_null=True)
    github = serializers.CharField(
        source='github_url', required=False, allow_null=True)
    url = serializers.URLField(required=False)
    host = serializers.URLField(required=False)

    def to_representation(self, instance):
        return {
            **super().to_representation(instance),
            'id': instance.get_public_id()
        }

    def update(self, instance, validated_data):
        return AuthorSerializer._update(instance, validated_data)

    def create(self, validated_data):
        return AuthorSerializer._upcreate(validated_data)

    @staticmethod
    def _update(instance, validated_data):
        """
        method used to modify model, if serializer is used as `partial=True`

        use static method to avoid creating a serializer when data is already valid,
        which happens often in other objects like Post, Like where Author is nested inside.
        """
        instance.github_url = validated_data.get(
            'github_url', instance.github_url)
        instance.display_name = validated_data.get(
            'display_name', instance.display_name)
        instance.save()
        return instance

    @staticmethod
    def _upcreate(validated_data):
        """
        update or create Author from validated data, based on url OR id.
        """
        try:
            author = Author.objects.get(
                Q(id=validated_data['id']) | Q(url=validated_data['url']))
            updated_author = AuthorSerializer._update(author, validated_data)
        except Author.MultipleObjectsReturned:
            raise exceptions.ParseError(
                "multiple author objects with the same id or url is detected. How did you do that?")
        except:
            updated_author = Author.objects.create(**validated_data)

        return updated_author

    def validate_github(self, value):
        """
        validator that will run on `github` field on .is_valid() call
        """
        if value and not 'github.com' in value:
            raise ValidationError(
                _('Author github url has to be a github url.'))
        return value

    class Meta:
        model = Author
        # show these fields in response
        fields = ['type', 'id', 'host', 'displayName', 'url', 'github']


class FollowSerializer(serializers.ModelSerializer):
    """
    used to parse incoming POST /inbox/ where the json object is a Follow,
    sent from another server.

    It expects the author object to conform to our AuthorSerializer.
    """
    type = serializers.CharField(default='Follow', read_only=True)
    summary = serializers.CharField()
    status = serializers.ChoiceField(required=False, read_only=True, choices=Follow.FollowStatus.choices)
    actor = AuthorSerializer()
    object = AuthorSerializer()

    def create(self, validated_data):
        actor_data = validated_data.pop('actor')
        object_data = validated_data.pop('object')

        actor = AuthorSerializer._upcreate(actor_data)
        object = Author.objects.get(url=object_data['url'])
        return Follow.objects.create(summary=validated_data['summary'], actor=actor, object=object)

    def validate_object(self, data):
        serializer = AuthorSerializer(data=data)
        if not serializer.is_valid():
            print(serializer.errors)
            raise exceptions.ParseError

        try:
            Author.objects.get(Q(id=serializer.validated_data.get('id')) | Q(
                url=serializer.validated_data.get('url')))
        except:
            # the object author does not exist. we cannot create a new author out of nothing
            raise exceptions.ParseError
        return serializer.validated_data

    class Meta:
        model = Follow
        fields = ['summary', 'actor', 'object', 'type', 'status']


class InboxObjectSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    object = serializers.JSONField()

    class Meta:
        model = InboxObject
        fields = ['author', 'object']

    def to_internal_value(self, data):
        # author is only used internally
        author = self.context.get('author')
        validated_data = {
            'author': author,
            'object': data
        }
        return validated_data

    def to_representation(self, instance):
        # the representation/external output is just the json object
        return instance.object

    def create(self, validated_data):
        return InboxObject.objects.create(**validated_data)
