from rest_framework.pagination import PageNumberPagination
from utils.common.response_utils import paginated_response


class CustomPaginator(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return paginated_response(
            self.page.paginator, self.page, lambda p, many=False: data
        )
