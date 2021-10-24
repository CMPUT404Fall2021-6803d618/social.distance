from social_distance.pagination import PageSizePagination

class AuthorsPagination(PageSizePagination):
    type = 'authors'

class FollowersPagination(PageSizePagination):
    type = 'followers'

class SentFriendRequestPagination(PageSizePagination):
    type = 'followings'
