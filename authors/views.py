from drf_spectacular.types import OpenApiTypes
from urllib.parse import unquote
import requests
from requests.models import HTTPBasicAuth
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveDestroyAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework import exceptions, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from drf_spectacular.utils import OpenApiExample, extend_schema
from django.forms.models import model_to_dict
from django.db.models.query_utils import Q

from posts.models import Post, Like
from posts.serializers import LikeSerializer, PostSerializer
from nodes.models import connector_service, Node

from .serializers import AuthorSerializer, FollowSerializer, InboxObjectSerializer
from .pagination import *
from .models import Author, Follow, Follow, InboxObject

# https://www.django-rest-framework.org/tutorial/3-class-based-views/


class AuthorList(ListAPIView):
    serializer_class = AuthorSerializer
    pagination_class = AuthorsPagination

    # used by the ListCreateAPIView super class 
    def get_queryset(self):
        all_authors = Author.objects.all()
        return [author for author in all_authors if author.is_internal]

    @extend_schema(
        # specify response format for list: https://drf-spectacular.readthedocs.io/en/latest/faq.html?highlight=list#i-m-using-action-detail-false-but-the-response-schema-is-not-a-list
        responses=AuthorSerializer(many=True)
    )
    def get(self, request, *args, **kwargs):
        """
        ## Description:
        List all authors in this server.
        ## Responses:
        **200**: for successful GET request
        """
        return super().list(request, *args, **kwargs)

class AuthorDetail(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        # used for schema generation for all methods
        # https://drf-spectacular.readthedocs.io/en/latest/customization.html#step-1-queryset-and-serializer-class
        return AuthorSerializer

    def get(self, request, author_id):
        """
        ## Description:
        Get author profile
        ## Responses:
        **200**: for successful GET request <br>
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(pk=author_id)
        except Author.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AuthorSerializer(author, many=False)
        return Response(serializer.data)

    def post(self, request, author_id):
        """
        ## Description:
        Update author profile
        ## Responses:
        **200**: for successful POST request <br>
        **400**: if the payload failed the serializer check <br>
        **404**: if the author id does not exist
        """
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


class InboxSerializerMixin:
    def serialize_inbox_item(self, item, context={}):
        model_class = item.content_type.model_class()
        if model_class is Follow:
            serializer = FollowSerializer
        elif model_class is Post:
            serializer = PostSerializer
        elif model_class is Like:
            serializer = LikeSerializer
        return serializer(item.content_object, context=context).data

    def deserialize_inbox_data(self, data, context={}):
        if not data.get('type'):
            raise exceptions.ParseError
        type = data.get('type')
        if type == Follow.get_api_type():
            serializer = FollowSerializer
        elif type == Post.get_api_type():
            serializer = PostSerializer
        elif type == Like.get_api_type():
            serializer = LikeSerializer

        return serializer(data=data, context=context)

class InboxListView(ListCreateAPIView, InboxSerializerMixin):
    # permission_classes = [permissions.IsAuthenticated]
    pagination_class = InboxObjectsPagination
    serializer_class = InboxObjectSerializer

    def get(self, request, author_id):
        """
        ## Description:
        Get all objects for the current user. user jwt auth required
        ## Responses:
        **200**: for successful GET request <br>
        **401**: if the authenticated user is not the post's poster <br>
        **403**: if the request user is not the same as the author <br> 
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound

        # has to be the current user
        # and author without a user is a foreign author
        if not author.user or request.user != author.user:
            raise exceptions.AuthenticationFailed

        inbox_objects = author.inbox_objects.all()
        paginated_inbox_objects = self.paginate_queryset(inbox_objects)
        return self.get_paginated_response([self.serialize_inbox_item(obj) for obj in paginated_inbox_objects])

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
        """
        ## Description:
        A foreign server sends some json object to the inbox. server basic auth required
        ## Responses:
        **200**: for successful POST request <br>
        **400**: if the payload failed the serializer check <br>
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound

        serializer = self.deserialize_inbox_data(
            self.request.data, context={'author': author})
        if serializer.is_valid():
            # save the item to database, could be post or like or FR
            item = serializer.save()
            if hasattr(item, 'update_fields_with_request'):
                item.update_fields_with_request(request)
            # wrap the item in an inboxObject, links with author
            item_as_inbox = InboxObject(content_object=item, author=author)
            item_as_inbox.save()
            return Response({'req': self.request.data, 'saved': model_to_dict(item_as_inbox)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class InboxDetailView(RetrieveDestroyAPIView, InboxSerializerMixin):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, author_id, inbox_id):
        """
        ## Description:
        Get an inbox item by id
        ## Responses:
        **200**: for successful GET request <br>
        **404**: if the author id or the inbox id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound('author not found')

        try:
            inbox_item = author.inbox_objects.get(id=inbox_id)
        except:
            raise exceptions.NotFound('inbox object not found')

        # has to be the current user
        # and author without a user is a foreign author
        if not author.user or request.user != author.user:
            raise exceptions.AuthenticationFailed

        # can only see your own inbox items!
        if inbox_item.author != author:
            raise exceptions.NotFound('inbox object not found')

        return Response(self.serialize_inbox_item(inbox_item))
    
    def delete(self, request, author_id, inbox_id):
        """
        ## Description:
        Delete an inbox item by id
        ## Responses:
        **204**: for successful DELETE request <br>
        **404**: if the author id or the inbox id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound('author not found')

        try:
            inbox_item = author.inbox_objects.get(id=inbox_id)
        except:
            raise exceptions.NotFound('inbox object not found')

        # has to be the current user
        # and author without a user is a foreign author
        if not author.user or request.user != author.user:
            raise exceptions.AuthenticationFailed

        # can only delete your own inbox items!
        if inbox_item.author != author:
            raise exceptions.NotFound('inbox object not found')

        inbox_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FollowerList(ListAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = AuthorSerializer
    pagination_class = FollowersPagination

    def get_queryset(self):
        author_id = self.kwargs.get('author_id')
        if author_id is None:
            raise exceptions.NotFound

        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound
        # find all author following this author
        return Author.objects.filter(followings__object=author, followings__status=Follow.FollowStatus.ACCEPTED)

    def get(self, request, *args, **kwargs):
        """
        ## Description:
        Get a list of author who are their followers
        ## Responses:
        **200**: for successful GET request <br>
        **404**: if the author id does not exist
        """
        return super().list(request, *args, **kwargs)

class FollowerDetail(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(
        responses=AuthorSerializer(),
    )
    def get(self, request, author_id, foreign_author_url):
        """
        ## Description:
        check if user at the given foreign url is a follower of the local author
        ## Responses:
        **200**: for successful GET request, return <Author object of the follower> <br>
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound
        return Response(AuthorSerializer(get_object_or_404(
            Author,
            followings__object=author,  # the author being followed
            followings__status=Follow.FollowStatus.ACCEPTED,
            url=foreign_author_url  # the foreign author following the author
        )).data)

    def delete(self, request, author_id, foreign_author_url):
        """
        ## Description:
        delete a follower by url
        ## Responses:
        **200**: for successful DELETE request <br>
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            raise exceptions.NotFound("local author is not found")

        try:
            # the following object for this relationship
            follower_following = author.followers.get(
                actor__url=foreign_author_url)
        except:
            raise exceptions.NotFound(
                f"foreign author at {foreign_author_url} is not a follower of the local author")

        follower_following.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        ## Description: 
        Add a follower (must be authenticated)
        ## Responses:
        **200**: for successful PUT request <br>
        **400**: if the payload failed the serializer check <br>
        **401**: if the authenticated user is not the post's poster <br> 
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
            if not author.user or request.user != author.user:
                raise exceptions.AuthenticationFailed
        except Author.DoesNotExist:
            raise exceptions.NotFound("author does not exist")

        # decode first if it's uri-encoded url
        foreign_author_url = unquote(foreign_author_url)
        existing_follower_set = Author.objects.filter(url=foreign_author_url)

        # sanity check: muliple cached foreign authors with the same url exists. break.
        if len(existing_follower_set) > 1:
            raise exceptions.server_error(request)

        # check if the follower is a local author
        if existing_follower_set and existing_follower_set.get().is_internal:
            # internal author: do nothing
            follower = existing_follower_set.get()
        else:
            # external author: upcreate it first
            follower_serializer = self.get_follower_serializer_from_request(
                request, foreign_author_url)
            print("foreign author url: ", foreign_author_url)
            print("follow serializer: ", follower_serializer)
            if follower_serializer.is_valid():
                if foreign_author_url != follower_serializer.validated_data['url']:
                    return Response("payload author's url does not match that in request url", status=status.HTTP_400_BAD_REQUEST)
                follower = follower_serializer.save()
            else:
                return Response(follower_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # accept the follow request (activate the relationship), or create it if not exist already
        try:
            pending_follow = Follow.objects.get(object=author, actor=follower, status=Follow.FollowStatus.PENDING)
            pending_follow.status = Follow.FollowStatus.ACCEPTED
            pending_follow.save()
        except Follow.DoesNotExist:
            _ = Follow.objects.create(
                object=author, actor=follower, status=Follow.FollowStatus.ACCEPTED)
        except Follow.MultipleObjectsReturned:
            raise exceptions.ParseError("There exists multiple Follow objects. Please report how you reached this error")
        return Response()

    def get_follower_serializer_from_request(self, request, foreign_author_url):
        if request.data:
            follower_serializer = AuthorSerializer(data=request.data)
        else:
            # try fetch the foreign user first, upcreate it locally and do it again.
            # TODO server2server basic auth, refactor into server2server connection pool/service
            res = requests.get(foreign_author_url)
            follower_serializer = AuthorSerializer(data=res.json())
        return follower_serializer

class FollowingList(ListAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = FollowSerializer
    pagination_class = FollowingsPagination


    def get_queryset(self):
        try:
            author = Author.objects.get(id=self.kwargs.get('author_id'))
        except Author.DoesNotExist:
            raise exceptions.NotFound
    
        followings = author.followings.all()

        followings_to_delete = []
        for following in followings:
            if following.object.is_internal:
                continue
            foreign_author_url = following.object.url

            if foreign_author_url.endswith("/"):
                request_url = foreign_author_url + "followers/" + author.url
            else:
                request_url = foreign_author_url + "/followers/" + author.url
            response = requests.get(request_url)

            if response.status_code > 204:
                # try again but with author.id instead of author.url
                if foreign_author_url.endswith("/"):
                    request_url = foreign_author_url + "followers/" + author.id
                else:
                    request_url = foreign_author_url + "/followers/" + author.id
                response = requests.get(request_url)

            # any status code < 400 indicate success
            if response.status_code < 400 and following.status == Follow.FollowStatus.PENDING:
                # foreign author accepted the follow request
                following.status = Follow.FollowStatus.ACCEPTED
                following.save()
            elif response.status_code >= 400 and following.status == Follow.FollowStatus.ACCEPTED:
                # foreign author removed the author as a follower 
                followings_to_delete.append(following.id)

        # https://stackoverflow.com/a/34890230
        followings.filter(id__in=followings_to_delete).delete()
       
        return followings.exclude(id__in=followings_to_delete)

    @extend_schema(
        responses=FollowSerializer(many=True)
    )
    def get(self, request, *args, **kwargs):
        """
        **[INTERNAL]**
        ## Description:
        List all the authors that this author is currently following
        ## Responses:
        **200**: for successful GET request
        """
        return super().list(request, *args, **kwargs)

class FollowingDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=FollowSerializer()
    )
    def post(self, request, author_id, foreign_author_url):
        """
        **[INTERNAL]** <br>
        ## Description:
        the /author/<author_id>/friend_request/<foreign_author_url>/ endpoint
        - author_id: anything other than slash, but we hope it's a uuid
        - foreign_author_url: anything, but we hope it's a valid url.

        used only by local users, jwt authentication required. <br>
        Its job is to fire a POST to the foreign author's inbox with a FriendRequest json object.
        ## Responses:
        **200**: for successful POST request <br>
        **403**: if the follow request already exist <br>
        **404**: if the author_id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        # get that foreign author's json object first
        print("following: foreign author url: ", foreign_author_url)

        # try without the auth
        # can either be a local author being followed or foreign server does not require auth
        response = requests.get(foreign_author_url)
        
        if response.status_code != 200:
            nodes = [x for x in Node.objects.all() if x.host_url in foreign_author_url]
            if len(nodes) != 1:
                raise exceptions.NotFound("cannot find the node from foreign author url")

            node = nodes[0]
            response = requests.get(foreign_author_url, auth=node.get_basic_auth_tuple())
        
        foreign_author_json = response.json()
        print("following: foreign author: ", foreign_author_json)

        # check for foreign author validity
        foreign_author_ser = AuthorSerializer(data=foreign_author_json)

        if foreign_author_ser.is_valid():
            foreign_author = foreign_author_ser.save()

            if Follow.objects.filter(actor=author, object=foreign_author):
                raise exceptions.PermissionDenied("duplicate follow object exists for the authors")

            follow = Follow(
                summary=f"{author.display_name} wants to follow {foreign_author.display_name}",
                actor=author,
                object=foreign_author
            )

            follow.save()
            connector_service.notify_follow(follow, request=request)
            return Response(FollowSerializer(follow).data)

        return Response({'parsing foreign author': foreign_author_ser.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, author_id, foreign_author_url):
        """
        **[INTERNAL]** <br>
        ## Description: 
        Should be called when author_id's author no longer wants to follow foreign_author_url's author <br>
        This can happen when the author is already following (status ACCEPTED) <br>
        Or author wants to remove its friend/follow request (status PENDING)
        ## Responses:
        **204**: For successful DELETE request <br>
        **400**: When the author is not following the other author <br>
        **404**: When the follower or followee does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
            foreign_author = Author.objects.get(url=foreign_author_url)
            follow_object = Follow.objects.get(actor=author, object=foreign_author)
        except Author.DoesNotExist as e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        except Follow.DoesNotExist:
            error_msg = "the follow relationship does not exist between the two authors"
            return Response(error_msg, status=status.HTTP_400_BAD_REQUEST)
        
        follow_object.delete()

        # send a request to the foreign server telling them to delete the follower
        if (foreign_author_url.endswith("/")):
            request_url = foreign_author_url + "followers/" + author.url
        else:
            request_url = foreign_author_url + "/followers/" + author.url
        
        try:
            host_url = foreign_author.host
            node = Node.objects.get(Q(host_url=host_url) | Q(host_url=host_url[:-1]))
            # ignoring the response here as we can't control the remote server
            # but at least we tried to notify them 
            requests.delete(request_url, auth=node.get_basic_auth_tuple())
        except Node.DoesNotExist:
            print("failed to notify remote server of the unfollowing")
            print("Reason: Remote Server not connected")
        except requests.exceptions.RequestException as e:
            print("failed to notify remote server of the unfollowing")
            print("Reason: Remote Request Failed: " + e)

        return Response(status=status.HTTP_204_NO_CONTENT)
        
class ForeignAuthorList(ListAPIView):
    serializer_class = AuthorSerializer
    pagination_class = AuthorsPagination

    def get(self, request, node_id):
        """
        **[INTERNAL]** <br>
        ## Description:
        Get all authors from a foreign server node by calling their /authors/ endpoint
        ## Responses:
        Whatever the foreign server /authors/ endpoint returned to us <br>
        Or **404** if the node_id does not exist
        """
        try:
            node = Node.objects.get(pk=node_id)
        except Node.DoesNotExist:
            error_msg = "Cannot find the node with specific id"
            raise exceptions.NotFound(error_msg)
        
        request_url = node.host_url
        if request_url[-1] != "/":
            request_url += "/"

        query_params = request.query_params.dict()
        page = query_params["page"] if "page" in query_params else 1
        size = query_params["size"] if "size" in query_params else 100
        request_url += "authors/?page=" + str(page) + "&size=" + str(size)

        try:
            response = requests.get(request_url, auth=node.get_basic_auth_tuple())
        except requests.exceptions.RequestException as err:
            return Response(err, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(response.json(), status=response.status_code)
