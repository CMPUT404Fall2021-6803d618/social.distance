from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class PageSizePagination(PageNumberPagination):
    page_size_query_param = 'size' # use query param 'size'
    key = 'items'
    type = 'objects'

    def __init__(self):
        super().__init__()

    def get_paginated_response(self, data):
        response = {}
        # include the response type if it exist
        if hasattr(self, 'type'):
            response['type'] = self.type
        response.update({
            'page': int(self.get_page_number(request=self.request, paginator=self.page.paginator)),
            'size': int(self.get_page_size(request=self.request)),
            'count': self.page.paginator.count,
            self.key: data
        })
        return Response(response) 

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                    'example': 'objects'
                },
                'page': {
                    'type': 'integer',
                    'example': 123,
                },
                'size': {
                    'type': 'integer',
                    'example': 123,
                },
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                self.key: schema,
            },
        }
