from social_distance.pagination import PageSizePagination

class AuthorsPagination(PageSizePagination):
    def __init__(self):
        super().__init__()
        self.type = 'authors'
