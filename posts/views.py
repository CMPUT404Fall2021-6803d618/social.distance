import base64
import requests
from itertools import chain

from django.http.response import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from drf_spectacular.types import OpenApiTypes

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework import status, permissions, exceptions
from drf_spectacular.utils import OpenApiExample, extend_schema

from authors.models import Author, InboxObject
from authors.serializers import AuthorSerializer
from nodes.models import connector_service
from github.utils import get_github_activity

from .models import Post, Comment, Like
from .serializers import *
from .pagination import CommentsPagination, PostsPagination


import uuid
import copy

def get_author_and_post(author_id, post_id):
    try:
        author = Author.objects.get(pk=author_id)
        post = Post.objects.get(pk=post_id)
        if (post.author.id != author.id):
            error_msg = "this author is not the post's poster"
            raise exceptions.PermissionDenied(error_msg)
    except (Author.DoesNotExist, Post.DoesNotExist):
        error_msg = "Author or Post id does not exist"
        raise exceptions.NotFound(error_msg)

    return (author, post)

@api_view(['GET'])
def get_all_posts(request):
    """
    THIS IS NOT IN THE SPEC. SOMEONE PLEASE BE MORE RESPONSIBLE FOR THE SPEC.
    IT'S SO BARELY USABLE THAT I HAVE TO SHOUT. -Lucas
    """
    posts = Post.objects.all()
    posts = list(filter(lambda x: x.author.is_internal(), posts))

    return Response(PostSerializer(posts, many=True).data)

class StreamList(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        """
        return a list of posts consist of:
        - posts created by the current author
        - posts sent to the author's inbox
        """
        # https://docs.djangoproject.com/en/3.2/ref/contrib/contenttypes/#methods-on-contenttype-instances
        # the Post type, in content type representation
        author = get_object_or_404(Author, pk=self.kwargs.get('author_id'))

        if not author.user == self.request.user:
            raise exceptions.PermissionDenied("the logged in user cannot access other streams except that of itself")

        post_content_type = ContentType.objects.get(app_label="posts", model="post")

        inbox_posts = [inbox.content_object for inbox in InboxObject.objects.filter(author=author, content_type=post_content_type)]
        own_posts = Post.objects.filter(author=author, unlisted=False)
        github_activities = get_github_activity(author.github_url)

        return sorted(
            filter(lambda post: post is not None, chain(inbox_posts, own_posts, github_activities)),
            key=lambda post: post.published,
            reverse=True
        )

class PostDetail(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return PostSerializer

    def get(self, request, author_id, post_id):
        """
        ## Description:
        Get author post with the post_id
        ## Responses:
        **200**: for successful GET request, see below for example response schema <br>
        **403**: if author and post ids are valid, but post's poster is not the author 
                 OR if the post is not public <br>
        **404**: is either author or post id is not found 
        """
        _, post = get_author_and_post(author_id, post_id)
        
        if post.visibility != Post.Visibility.PUBLIC and request.user != post.author.user:
            raise exceptions.PermissionDenied

        serializer = PostSerializer(post, many=False, context={'author_id': author_id})
        response = serializer.data
        # making an internal API call is not usually the best way to do this
        # but currently only this solution works 
        try:
            # need a try block for unit test because url is not built for testing purpose
            response["commentsSrc"] = requests.get(response["comments"]).json()
        except:
            pass
        return Response(response)
    
    def post(self, request, author_id, post_id):
        """
        ## Description:
        Update the post (authentication required)
        ## Responses: 
        **200**: for successful POST request, updated post detail is returned <br>
        **400**: if the update fields failed the serializer check <br>
        **401**: if the authenticated user is not the post's poster <br>
        **403**: if author and post ids are valid, but post's poster is not the author <br>
        **404**: if either author or post is not found
        """
        author, post = get_author_and_post(author_id, post_id)
        
        # author without a user is a foreign author
        if not author.user or request.user != author.user:
            raise exceptions.AuthenticationFailed

        serializer = PostSerializer(post, data=request.data, partial=True, context={'author_id': author_id})
        if serializer.is_valid():
            post = serializer.save()
            post.update_fields_with_request(request)
            connector_service.notify_post(post, request=request) # TODO should we notify on update post?
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, author_id, post_id): 
        """
        ## Description:
        Delete the post with post_id 
        ## Responses:
        **204**: for successful DELETE request <br>
        **403**: if author and post ids are valid, but post's poster is not the author <br>
        **404**: if either author or post is not found
        """
        _, post = get_author_and_post(author_id, post_id)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, author_id, post_id):
        """
        ## Description:
        Create a Post with the post_id
        ## Responses:
        **200**: for successful PUT request, the post detail is returned <br>
        **400**: if the payload failed the serializer check <br>
        **404**: if the author_id cannot be found <br>
        **409**: if the post_id already exist
        """
        # check whether post with that id already exist
        # and check whether the author exist
        try:
            _ = Post.objects.get(pk=post_id)
            error_msg = "This post id already exist"
            return Response(error_msg, status=status.HTTP_409_CONFLICT)
        except Post.DoesNotExist:
            try:
                author = Author.objects.get(pk=author_id)
            except Author.DoesNotExist:
                error_msg = "Author id not found"
                return Response(error_msg, status=status.HTTP_404_NOT_FOUND)

        serializer = PostSerializer(data=request.data, context={'author_id': author_id})
        if serializer.is_valid():
            # using raw create because we need custom id
            post = Post.objects.create(**serializer.validated_data, author=author, id=post_id)
            post.update_fields_with_request(request)

            connector_service.notify_post(post, request=request)
            serializer = PostSerializer(post, many=False)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostList(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = PostSerializer
    pagination_class = PostsPagination

    # used by the ListCreateAPIView super class
    def get_queryset(self):
        return self.posts

    def get(self, request, *args, **kwargs):
        """
        ## Description:
        Get recent posts of author (paginated)

        unlisted: only show listed posts
        ## Responses:
        **200**: for successful GET request <br>
        **404**: if the author_id cannot be found
        """
        try:
            author_id = kwargs.get("author_id")
            _ = Author.objects.get(pk=author_id)
            self.posts = Post.objects.filter(
                author_id=author_id,
                unlisted=False,
            ).order_by('-published')
        except (KeyError, Author.DoesNotExist):
            error_msg = "Author id not found"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)
 
        response = super().list(request, *args, **kwargs)
        return response
    
    def post(self, request, author_id):
        """
        ## Description:
        Create a Post with generated post id
        ## Responses:
        **200**: for successful PUT request, the post detail is returned <br>
        **400**: if the payload failed the serializer check <br>
        **404**: if the author_id cannot be found 
        """
        post_id = uuid.uuid4()
        return PostDetail().put(request, author_id, post_id)


class CommentList(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = CommentSerializer
    pagination_class = CommentsPagination

    # used by the ListCreateAPIView super class
    def get_queryset(self):
        return self.comments

    def get(self, request, *args, **kwargs):
        """
        ## Description:
        Get comments of the post (paginated)
        ## Responses:
        **200**: for successful GET request <br>
        **403**: if author and post ids are valid, but post's poster is not the author <br>
        **404**: if either author or post is not found 
        """
        author_id = kwargs.get("author_id")
        post_id = kwargs.get("post_id")
        _, _ = get_author_and_post(author_id, post_id)
       
        self.comments = Comment.objects.filter(
            post_id=post_id
        ).order_by('-published')
 
        response = super().list(request, *args, **kwargs)
        # '?' excludes query parameter
        request_url = request.build_absolute_uri('?')
        response.data["id"] = request_url
        response.data["post"] = request_url.replace("comments/", "")
        return response

    def post(self, request, author_id, post_id):
        """
        ## Description:
        Add a comment to the author_id's post post_id
        ## Responses:
        **200**: for successful POST request <br>
        **400**: if the payload failed the serializer check <br>
        **404**: if the author or post id does not exist
        """
        # check if the post and post's author exist
        try:
            _ = Author.objects.get(pk=author_id)
            post = Post.objects.get(pk=post_id)
            comment_author_json = request.data.pop("author")
            comment_author_url = comment_author_json["url"]
        except (Author.DoesNotExist, Post.DoesNotExist):
            error_msg = "Cannot find either the author or post id"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)
        except KeyError:
            # the author and author.url attributes must exist
            # otherwise we have no idea who made the comment
            error_msg = "Payload must contain author and author.url attribute"
            return Response(error_msg, status=status.HTTP_400_BAD_REQUEST)

        comment_author_set = Author.objects.filter(url=comment_author_url)
        # check if author is local
        if comment_author_set and comment_author_set.get().is_internal():
            # local author
            comment_author = comment_author_set.get()
        else:
            # foreign author
            comment_author_serializer = AuthorSerializer(
                data=comment_author_json)
            if not comment_author_serializer.is_valid():
                return Response(comment_author_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            comment_author = comment_author_serializer.save()

        comment_serializer = CommentSerializer(data=request.data)
        if comment_serializer.is_valid():
            comment = Comment.objects.create(
                author=comment_author,
                post=post,
                **comment_serializer.validated_data
            )
            comment.update_fields_with_request(request)
            serializer = CommentSerializer(comment, many=False)
            return Response(serializer.data)
        else:
            return Response(comment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetail(APIView):
    def get_serializer_class(self):
        return CommentSerializer

    def get(self, request, author_id, post_id, comment_id):
        """
        ## Description:
        Get the comment with the specific post and author
        ## Responses:
        **200**: for successful GET request <br>
        **403**: if post's poster is not author, or comment belongs to another post <br>
        **404**: if either author, post, or comment does not exist
        """
        _, post = get_author_and_post(author_id, post_id)
    
        try:
            comment = Comment.objects.get(pk=comment_id)
            if comment.post.id != post.id:
                error_msg = "the comment id is not related to the post id"
                return Response(error_msg, status=status.HTTP_403_FORBIDDEN)
        except:
            error_msg = "Comment id is not valid"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)
    
        serializer = CommentSerializer(comment, many=False)
        return Response(serializer.data)


class LikesPostList(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        responses=LikeSerializer(many=True),
    )
    def get(self, request, author_id, post_id):
        """
        ## Description:
        Get a list of likes to author_id's post post_id
        ## Responses:
        **200**: for successful GET request <br>
        **404**: if author or post does not exist
        """
        try:
            _ = Author.objects.get(pk=author_id)
            post = Post.objects.get(pk=post_id)
        except (Author.DoesNotExist, Post.DoesNotExist):
            error_msg = "Author or Post id not found"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)

        likes = Like.objects.filter(object=post.url)
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)


class LikesCommentList(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(
        responses=LikeSerializer(many=True),
    )
    def get(self, request, author_id, post_id, comment_id):
        """
        ## Description:
        Get a list of likes to author_id's post post_id comment comment_id
        ## Responses:
        **200**: for successful GET request <br>
        **403**: if post's poster is not author, or comment belongs to another post <br>
        **404**: if either author, post, or comment does not exist
        """
        _, post = get_author_and_post(author_id, post_id)
    
        try:
            comment = Comment.objects.get(pk=comment_id)
            if comment.post.id != post.id:
                error_msg = "the comment id is not related to the post id"
                return Response(error_msg, status=status.HTTP_403_FORBIDDEN)
        except:
            error_msg = "Comment id is not valid"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)

        likes = Like.objects.filter(object=comment.url)
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)


class LikedList(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, author_id):
        """
        ## Description:
        Get a list of likes orginating from author author_id
        ## Responses:
        **200**: for sucessful GET request <br>
        **404**: if the author id does not exist
        """
        try:
            author = Author.objects.get(id=author_id)
        except:
            error_msg = "Author not found"
            return Response(error_msg, status=status.HTTP_404_NOT_FOUND)

        likes = Like.objects.filter(author=author)
        serializer = LikeSerializer(likes, many=True)
        response = {
            "type": "liked",
            "items": serializer.data
        }
        return Response(response)

    @extend_schema(
        examples=[
            OpenApiExample('A like object', value={
                "type": "Like",
                "summary": "lucas1 liked lucas' post",
                "author": {
                    "type": "author",
                    "id": "http://127.0.0.1:8000/author/eb638f5b-38bb-45e1-a882-310a500c63cd/",
                    "host": "http://127.0.0.1:8000/",
                    "displayName": "Lucas1_23333",
                    "url": "http://127.0.0.1:8000/author/eb638f5b-38bb-45e1-a882-310a500c63cd/",
                    "github": None
                },
                "object": "http://127.0.0.1:8000/author/51914b9c-98c6-4a5c-91bf-fb55a53a92fe/posts/d8fb48fe-a014-49d9-ac4c-bfbdf94b097f/"
            })
        ],
        request={
            'application/json': OpenApiTypes.OBJECT
        },
    )
    def post(self, request, author_id):
        """
        **[Internal]** <br>
        ## Description:
        create a like object and send to its target author <br>
        NOTE: authenticated as the sender author itself
        ## Responses:
        **200**: for successful POST request
        **400**: if the payload failed the serializer check
        **404**: if the author does not exist
        """
        return self.internally_send_like(request, author_id)

    def internally_send_like(self, request, author_id):
        try:
            _ = Author.objects.get(id=author_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # get that foreign author's json object first
        like_ser = LikeSerializer(data=request.data, context={
                                  'author_id': author_id})
        if like_ser.is_valid():
            like = like_ser.save()
            res = connector_service.notify_like(like, request=request)
            return Response({'res': res, 'like': like_ser.validated_data})
        return Response(like_ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_image(request, author_id, image_post_id):
    author, post = get_author_and_post(author_id, image_post_id)

    # needs authentication if image is PRIVATE
    if post.visibility == Post.Visibility.PRIVATE:
        if not request.user or not request.user.is_authenticated:
            raise exceptions.PermissionDenied('authentication required for this image')
        # TODO check if user has access to this image: friends of the author, author itself...

    if not 'image' in post.content_type:
        raise exceptions.NotFound

    content = post.content
    if type(content) == str:
        content = content.encode('ascii')

    return HttpResponse(base64.decodestring(content), content_type=post.content_type)

@api_view(['POST'])
def upload_image(request, author_id):
    """
    ## Description
    POST to save a image file under the author.
    returns the link to the image.

    ## Request
    FormData with the following fields, value in JSON format if not otherwise specified:
        - image: the image file, value is a js File object
        - visibility: the visibility of the image, value is 'PUBLIC' or 'PRIVATE' or 'FRIENDS', default is 'PUBLIC'
        - unlisted: whether the image is unlisted or not, value is 'true' or 'false', default is 'true'
    For more examples about using formdata in the frontend, see https://developer.mozilla.org/en-US/docs/Web/API/FormData/append

    An example of a js script:
    ```js
    let form = new FormData();
    form.append("image", input.files[0]); // input is the file input element
    form.append("visibility", "PUBLIC");
    form.append("unlisted", "true");
    fetch("http://127.0.0.1:8000/author/my_author_id/images/", {
        method: "POST",
        body: form
    })
    ```

    ## Response
    **200**: { 'url': <the_url_to_the_image> }
    **400**: image or image type is not valid, OR visibility is not valid, OR unlisted is not valid
    **404**: author does not exist
    """
    # TODO put request description as a schema

    author = get_object_or_404(Author, id=author_id)

    ser = ImageUploadSerializer(data=request.data, context={'author': author})

    if ser.is_valid():
        content_type = ser.validated_data['image'].content_type
        image_data = base64.b64encode(ser.validated_data['image'].read()).decode('ascii')

        image_post = Post(author=author, title='Uploaded Image', description='', content_type=content_type, content=image_data, visibility=ser.validated_data['visibility'], unlisted=ser.validated_data['unlisted'])
        image_post.update_fields_with_request(request)
        return Response({'url': image_post.get_image_url()})
    
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class ShareToFriendsSerializer(serializers.Serializer):
    friends = AuthorSerializer(many=True)

@extend_schema(
    request=ShareToFriendsSerializer,
    responses={
        200: PostSerializer
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def share_post_friends(request, author_id, post_id):
    """
    **[Internal]** <br>

    ## Description
    POST to the endpoint to reshare a post. the server will create a new, reshared post,
    and forward it to the corresponding followers' inboxes.

    ## Request
    nothing, but requires to be authenticated as the author who is trying to reshare.

    ## Response
    **200**: Post that is created
    **403**: if the user is not local or if it's not authenticated
    **404**: author or post does not exist
    """

    last_author, last_post = get_author_and_post(author_id, post_id)
    last_url = last_post.url

    # duplicate the post
    shared_post = last_post
    shared_post.pk = None
    shared_post.save()

    # modify author to be current logged in author
    try:
        shared_post.author = request.user.author
    except:
        raise exceptions.PermissionDenied('only a local, logged-in user can share this post')
    # modify url and source
    shared_post.update_fields_with_request(request)
    shared_post.source = last_url
    shared_post.save()

    ser = ShareToFriendsSerializer(data=request.data)
    if ser.is_valid():
        # find authors whose url matches the uploaded author objects
        target_authors = Author.objects.filter(url__in=list(map(lambda author_data: author_data['url'], ser.validated_data['friends'])))

        # notify the post
        connector_service.notify_post(shared_post, request=request, targets=target_authors)

        # return the post
        ser = PostSerializer(shared_post)
        return Response(status=status.HTTP_200_OK, data=ser.data)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def share_post_followers(request, author_id, post_id):
    """
    **[Internal]** <br>

    ## Description
    POST to the endpoint to reshare a post. the server will create a new, reshared post,
    and forward it to the corresponding followers' inboxes.

    ## Request
    nothing, but requires to be authenticated as the author who is trying to reshare.

    ## Response
    **200**: Post that is created
    **403**: if the user is not local or if it's not authenticated
    **404**: author or post does not exist
    """

    last_author, last_post = get_author_and_post(author_id, post_id)
    last_url = last_post.url

    # duplicate the post
    shared_post = last_post
    shared_post.pk = None
    shared_post.save()

    # modify author to be current logged in author
    try:
        shared_post.author = request.user.author
    except:
        raise exceptions.PermissionDenied('only a local, logged-in user can share this post')
    # modify url and source
    shared_post.update_fields_with_request(request)
    shared_post.source = last_url
    shared_post.save()

    # notify the post
    connector_service.notify_post(shared_post, request=request)

    # return the post
    ser = PostSerializer(shared_post)
    return Response(status=status.HTTP_200_OK, data=ser.data)
