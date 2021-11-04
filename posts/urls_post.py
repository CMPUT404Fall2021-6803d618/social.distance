from django.urls import path

from .views import *

urlpatterns = [
    path('<str:post_id>/likes/', LikesPostList.as_view(), name="like-post-list"),
    path('<str:post_id>/comments/<str:comment_id>/likes/', LikesCommentList.as_view(), name="like-comment-list"),
]