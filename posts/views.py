import requests
from django.shortcuts import render
from rest_framework.decorators import api_view
from drf_spectacular.types import OpenApiTypes

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status, permissions, exceptions
from drf_spectacular.utils import OpenApiExample, extend_schema

from authors.models import Author
from authors.serializers import AuthorSerializer
from nodes.models import connector_service

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

class PostDetail(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return PostSerializer

    def get(self, request, author_id, post_id):
        """
        ## Description:  
        Get author post with the post_id  
        ## Responses:  
        **200**: for successful GET request, see below for example response schema  
        **403**: if author and post ids are valid, but post's poster is not the author 
                 OR if the post is not public     
        **404**: is either author or post id is not found 
        """
        _, post = get_author_and_post(author_id, post_id)
        
        # TODO: what if the author itself want to get friends/private posts?
        if (post.visibility != Post.Visibility.PUBLIC):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializer(post, many=False, context={'author_id', author_id})
        return Response(serializer.data)
    
    def post(self, request, author_id, post_id):
        """
        ## Description:  
        Update the post (authentication required)   
        ## Responses:
        **200**: for successful POST request, updated post detail is returned  
        **400**: if the update fields failed the serializer check  
        **403**: if author and post ids are valid, but post's poster is not the author   
        **404**: if either author or post is not found
        """
        _, post = get_author_and_post(author_id, post_id)
        
        serializer = PostSerializer(post, data=request.data, partial=True, context={'author_id': author_id})
        if serializer.is_valid():
            post = serializer.save()
            post.update_fields_with_request(request)
            connector_service.notify_post(post) # TODO should we notify on update post?
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, author_id, post_id): 
        """
        ## Description:  
        Delete the post with post_id 
        ## Responses:
        **204**: for successful DELETE request  
        **403**: if author and post ids are valid, but post's poster is not the author  
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
        **200**: for successful PUT request, the post detail is returned  
        **400**: if the payload failed the serializer check  
        **404**: if the author_id cannot be found  
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

            connector_service.notify_post(post)
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
        ## Responses:  
        **200**: for successful GET request  
        **404**: if the author_id cannot be found
        """
        try:
            author_id = kwargs.get("author_id")
            _ = Author.objects.get(pk=author_id)
            self.posts = Post.objects.filter(
                author_id=author_id
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
        **200**: for successful PUT request, the post detail is returned  
        **400**: if the payload failed the serializer check  
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
        **200**: for successful GET request  
        **403**: if author and post ids are valid, but post's poster is not the author  
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
        **204**: for successful POST request  
        **400**: if the payload failed the serializer check  
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
            return Response(status=status.HTTP_204_NO_CONTENT)
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
        **200**: for successful GET request  
        **403**: if post's poster is not author, or comment belongs to another post  
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
        **200**: for successful GET request  
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
        **200**: for successful GET request  
        **403**: if post's poster is not author, or comment belongs to another post  
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
    
    def get(self, request, author_id):
        """
        ## Description:  
        Get a list of likes orginating from author author_id  
        ## Responses:  
        **200**: for sucessful GET request  
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
        create a like object and send to its target author
        NOTE: authenticated as the sender author itself
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
            res = connector_service.notify_like(like)
            return Response({'res': res, 'like': like_ser.validated_data})
        return Response(like_ser.errors, status=status.HTTP_400_BAD_REQUEST)
