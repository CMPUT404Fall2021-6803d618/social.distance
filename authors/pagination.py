from social_distance.pagination import PageSizePagination

class SentFriendRequestPagination(PageSizePagination):
    def __init__(self):
        super().__init__()
        self.type = 'followings'