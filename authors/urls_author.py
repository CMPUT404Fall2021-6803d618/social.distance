from django.urls import path, include, re_path

from authors import views
from .views import *
from posts.views import LikedList

urlpatterns = [
    # server to server API
    path('<str:author_id>/inbox/', InboxListView.as_view(), name="inbox-list"),
    path('<str:author_id>/inbox/<str:inbox_id>/', InboxDetailView.as_view(), name="inbox-detail"),

    path('<str:author_id>/', AuthorDetail.as_view(), name="author-detail"),
    path('<str:author_id>/posts/', include("posts.urls_posts")),
    path('<str:author_id>/post/', include("posts.urls_post")),

    path('<str:author_id>/liked/', LikedList.as_view(), name="liked-list"),

    path('<str:author_id>/followers/', FollowerList.as_view(), name="author-followers"),
    re_path(r'^(?P<author_id>[^/]*)/followers/(?P<foreign_author_url>.*)$', FollowerDetail.as_view(), name="author-follower-detail"),

    path('<str:author_id>/followings/', FollowingList.as_view(), name='following-list'),
    re_path(r'^(?P<author_id>[^/]*)/followings/(?P<foreign_author_url>.*)$',
            internally_send_friend_request, name="friend-request"),
]
