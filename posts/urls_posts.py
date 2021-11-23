from django.urls import path

from .views import *

urlpatterns = [
    path('', PostList.as_view(), name="post-list"),
    path('<str:post_id>/', PostDetail.as_view(), name="post-detail"),
    path('<str:post_id>/share/followers/', share_post_followers, name="share-post-followers"),
    path('<str:post_id>/share/friends/', share_post_friends, name="share-post-friends"),
    path('<str:post_id>/comments/', CommentList.as_view(), name="comment-list"),
    path('<str:post_id>/comment/<str:comment_id>/', CommentDetail.as_view(), name="comment-detail"),
]
