from drf_spectacular.types import OpenApiTypes
import requests
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework import exceptions, status, permissions
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import OpenApiExample, extend_schema
from django.forms.models import model_to_dict

from .models import Author, Follow, FriendRequest, InboxObject
from .serializers import AuthorSerializer, FriendRequestSerializer, InboxObjectSerializer

from posts.models import Post, Like
from posts.serializers import LikeSerializer, PostSerializer

# Create your views here.

# https://www.django-rest-framework.org/tutorial/3-class-based-views/


class AuthorList(APIView):
    """
    List all authors in this server.
    """
    @extend_schema(
        # specify response format for list: https://drf-spectacular.readthedocs.io/en/latest/faq.html?highlight=list#i-m-using-action-detail-false-but-the-response-schema-is-not-a-list
        responses=AuthorSerializer(many=True),
    )
    def get(self, request):
        authors = Author.objects.all()
        serializer = AuthorSerializer(authors, many=True)
        return Response(serializer.data)


class AuthorDetail(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        # used for schema generation for all methods
        # https://drf-spectacular.readthedocs.io/en/latest/customization.html#step-1-queryset-and-serializer-class
        return AuthorSerializer

    """
    Get author profile
    """

    def get(self, request, author_id):
        try:
            author = Author.objects.get(pk=author_id)
        except Author.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AuthorSerializer(author, many=False)
        return Response(serializer.data)

    """
    Update author profile
    """

    def post(self, request, author_id):
        try:
            author = Author.objects.get(pk=author_id)
        except Author.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = AuthorSerializer(author, data=request.data, partial=True)
        if serializer.is_valid():
            author = serializer.save()
            # modify url to be server path
            author.update_fields_with_request(request)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InboxListView(APIView):
    """
    POST to inbox: a foreign server sends some json object to the inbox. server basic auth required
    GET from inbox: get all objects for the current user. user jwt auth required
    """
    # permission_classes = [permissions.permissions.IsAuthenticated]

    def get(self, request, author_id):
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound

        # has to be the current user
        try:
            assert author.user == self.request.user
        except:
            raise exceptions.PermissionDenied

        inbox_objects = author.inbox_objects.all()
        return Response([self.serialize_inbox_item(obj) for obj in inbox_objects])

    # TODO put somewhere else
    @extend_schema(
        examples=[
            OpenApiExample('A post object', value={
                "type": "post",
                "id": "http://127.0.0.1:8000/author/51914b9c-98c6-4a5c-91bf-fb55a53a92fe/posts/d8fb48fe-a014-49d9-ac4c-bfbdf94b097f/",
                "title": "Post1",
                "source": "",
                "origin": "",
                "description": "description for post1",
                "contentType": "text/markdown",
                "author": {
                    "type": "author",
                    "id": "http://127.0.0.1:8000/author/51914b9c-98c6-4a5c-91bf-fb55a53a92fe/",
                    "host": "http://127.0.0.1:8000/",
                    "displayName": "Updated!!!",
                    "url": "http://127.0.0.1:8000/author/51914b9c-98c6-4a5c-91bf-fb55a53a92fe/",
                    "github": None
                },
                "content": "# Hello",
                "count": 0,
                "published": "2021-10-22T20:58:18.072618Z",
                "visibility": "PUBLIC",
                "unlisted": False
            }),
            OpenApiExample('A like object', value={
                "type": "Like",
                "summary": "string",
                "author": {
                    "type": "author",
                    "id": "string",
                    "host": "string",
                    "displayName": "string",
                    "url": "string",
                    "github": "string"
                },
                "object": "string"
            }),
            OpenApiExample('A friend request object', value={
                "type": "Follow",
                "summary": "Greg wants to follow Lara",
                "actor": {
                    "type": "author",
                    "id": "http://127.0.0.1:5454/author/1d698d25ff008f7538453c120f581471",
                    "url": "http://127.0.0.1:5454/author/1d698d25ff008f7538453c120f581471",
                    "host": "http://127.0.0.1:5454/",
                    "displayName": "Greg Johnson",
                    "github": "http://github.com/gjohnson"
                },
                "object": {
                    "type": "author",
                    "id": "http://127.0.0.1:5454/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e",
                    "host": "http://127.0.0.1:5454/",
                    "displayName": "Lara Croft",
                    "url": "http://127.0.0.1:5454/author/9de17f29c12e8f97bcbbd34cc908f1baba40658e",
                    "github": "http://github.com/laracroft"
                }
            }),
        ],
        request={
            'application/json': OpenApiTypes.OBJECT
        },
    )
    def post(self, request, author_id):
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound

        serializer = self.deserialize_inbox_data(
            self.request.data, context={'author', author})
        if serializer.is_valid():
            # save the item to database, could be post or like or FR
            item = serializer.save()
            # wrap the item in an inboxObject, links with author
            item_as_inbox = InboxObject(content_object=item, author=author)
            item_as_inbox.save()
            return Response({'req': self.request.data, 'saved': model_to_dict(item_as_inbox)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def serialize_inbox_item(self, item, context={}):
        model_class = item.content_type.model_class()
        if model_class is FriendRequest:
            serializer = FriendRequestSerializer
        elif model_class is Post:
            serializer = PostSerializer
        elif model_class is Like:
            serializer = LikeSerializer
        return serializer(item.content_object, context=context).data

    def deserialize_inbox_data(self, data, context={}):
        if not data.get('type'):
            raise exceptions.ParseError
        type = data.get('type')
        if type == FriendRequest.get_api_type():
            serializer = FriendRequestSerializer
        elif type == Post.get_api_type():
            serializer = PostSerializer
        elif type == Like.get_api_type():
            serializer = LikeSerializer

        return serializer(data=data, context=context)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
def internally_send_friend_request(request, author_id, foreign_author_url):
    """
    the /author/<author_id>/friend_request/<foreign_author_url>/ endpoint
    - author_id: anything other than slash, but we hope it's a uuid
    - foreign_author_url: anything, but we hope it's a valid url.

    used only by local users, jwt authentication required.
    Its job is to fire a POST to the foreign author's inbox with a FriendRequest json object.

    NOTE: I think putting url inside a url sucks, too. -Lucas

    questions:
    - what to expect from POST result?
    - How do we know the friend request has been accepted?
    """
    import requests

    try:
        author = Author.objects.get(id=author_id)
    except:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # get that foreign author's json object first
    foreign_author_json = requests.get(foreign_author_url).json()

    # TODO do we check for foreign author validity?

    friend_request_payload = {
        'type': 'Follow',
        # TODO
        'summary': f"{author.display_name} wants to follow {foreign_author_json.get('displayName')}",
        'actor': AuthorSerializer(author).data,
        'object': foreign_author_json,
    }
    res = requests.post(foreign_author_url + 'inbox/',
                        json=friend_request_payload).json()
    return Response({'debug_foreign_author_url': foreign_author_url, 'debug_author_id': author_id, 'debug_foreign_response': res, 'req': friend_request_payload})


class FollowerList(ListAPIView):
    # TODO permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    """
    get a list of authors who are their followers
    """
    serializer_class = AuthorSerializer

    def get_queryset(self):
        author_id = self.kwargs.get('author_id')
        if author_id is None:
            raise exceptions.NotFound

        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound
        # find all author following this author
        return Author.objects.filter(followings__followee=author)


class FollowerDetail(APIView):
    # TODO permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(
        responses=AuthorSerializer(),
    )
    def get(self, request, author_id, foreign_author_url):
        """
        check if user at the given foreign url is a follower of the local author
        response: 200 <Author object of the follower>
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound
        return Response(AuthorSerializer(get_object_or_404(
            Author,
            followings__followee=author,  # all author following the author
            url=foreign_author_url  # AND whose url matches param
        )).data)

    def delete(self, request, author_id, foreign_author_url):
        """
        delete a follower by url
        response: 200 successfully deleted
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound("local author is not found")

        try:
            # the following object for this relationship
            follower_following = author.followers.get(
                follower__url=foreign_author_url)
        except:
            raise exceptions.NotFound(
                f"foreign author at {foreign_author_url} is not a follower of the local author")

        follower_following.delete()
        return Response()

    @extend_schema(
        examples=[
            OpenApiExample('A Foreign Author Paylod (Optional)', value={
                "type": "author",
                "id": "http://127.0.0.1:8000/author/change-me-123123/",
                "host": "http://127.0.0.1:8000/",
                "displayName": "Change Me",
                "url": "http://127.0.0.1:8000/author/change-me-123123/",
                "github": "https://github.com/123123123asdafsdfasdfasdfasdf/"
            })
        ],
        request={
            'application/json': OpenApiTypes.OBJECT
        },
    )
    def put(self, request, author_id, foreign_author_url):
        """
        Add a follower (must be authenticated)

        payload: <Author>
        response: 200 successfully created follow relation
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound

        existing_follower_set = Author.objects.filter(url=foreign_author_url)

        # sanity check: muliple cached foreign authors with the same url exists. break.
        if len(existing_follower_set) > 1:
            raise exceptions.server_error(request)

        # check if the follower is a local author
        if existing_follower_set and existing_follower_set.get().is_internal():
            # internal author: do nothing
            follower = existing_follower_set.get()
        else:
            # external author: upcreate it first
            follower_serializer = self.get_follower_serializer_from_request(
                request, foreign_author_url)
            if follower_serializer.is_valid():
                if foreign_author_url != follower_serializer.validated_data['url']:
                    return Response("payload author's url does not match that in request url", status=status.HTTP_400_BAD_REQUEST)
                follower = follower_serializer.save()
            else:
                return Response(follower_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # create the Follow object for this relationship, if not exist already
        if not Follow.objects.filter(followee=author, follower=follower):
            follower_following = Follow.objects.create(
                followee=author, follower=follower)
        return Response()

    def get_follower_serializer_from_request(self, request, foreign_author_url):
        if request.data:
            follower_serializer = AuthorSerializer(data=request.data)
        else:
            # try fetch the foreign user first, upcreate it locally and do it again.
            # TODO server2server basic auth, refactor into server2server connection pool/service
            res = requests.get(foreign_author_url)
            follower_serializer = AuthorSerializer(data=res.text)
        return follower_serializer
