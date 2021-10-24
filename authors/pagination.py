from social_distance.pagination import PageSizePagination

class AuthorsPagination(PageSizePagination):
    type = 'authors'

class FollowingsPagination(PageSizePagination):
    type = 'followings'
