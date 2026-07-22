from rest_framework import pagination
from rest_framework.response import Response


class PageNumberPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"

    def get_page_size(self, request):
        page_size = super().get_page_size(request)
        view = request.parser_context["view"]
        page_size = getattr(view, self.page_size_query_param, page_size)
        query_param = request.query_params.get(self.page_size_query_param, page_size)

        if query_param:
            return query_param

        return self.page_size

    def get_paginated_response(self, data, merge_data=None):
        response = {
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "count": self.page.paginator.count,
            "page": self.page.number,
            "num_pages": self.page.paginator.num_pages,
            "results": data,
        }

        if merge_data:
            response.update(merge_data)

        return Response(response)
