from social_distance.pagination import PageSizePagination

class CommentsPagination(PageSizePagination):
    key = 'comments'
    type = 'comments'

class PostsPagination(PageSizePagination):
    type = 'posts'