from django.urls import path, include, re_path

from authors import views
from .views import *
from posts.views import LikedList, get_image, upload_image, StreamList

urlpatterns = [
    # server to server API
    # NOTE: all paths have to be in sequence of MORE_SPECIFIC > LESS_SPECIFIC,
    # since django url runs in sequence and general will cover all specifc ones
    path('<path:author_id>/inbox/<str:inbox_id>/', InboxDetailView.as_view(), name="inbox-detail"),
    path('<path:author_id>/inbox/', InboxListView.as_view(), name="inbox-list"),

    path('<path:author_id>/stream/', StreamList.as_view(), name="author-stream"), # internal
    path('<path:author_id>/posts/', include("posts.urls_posts")),
    path('<path:author_id>/post/', include("posts.urls_post")),

    path('<path:author_id>/images/<str:image_post_id>/', get_image, name="image-detail"),
    path('<path:author_id>/images/', upload_image, name="upload-image"),

    path('<path:author_id>/liked/', LikedList.as_view(), name="liked-list"),

    path('<path:author_id>/followers/<path:foreign_author_url>', FollowerDetail.as_view(), name="author-follower-detail"),
    path('<path:author_id>/followers/', FollowerList.as_view(), name="author-followers"),

    path('<path:author_id>/followings/<path:foreign_author_url>',
            FollowingDetail.as_view(), name="following-detail"),
    path('<path:author_id>/followings/', FollowingList.as_view(), name='following-list'),

    path('<path:author_id>/', AuthorDetail.as_view(), name="author-detail"),
]
