from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CoursePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        raw_value = request.query_params.get("page_size")
        if raw_value is None:
            raw_value = request.query_params.get("pageSize")
        if raw_value is not None:
            try:
                size = int(raw_value)
            except (TypeError, ValueError):
                raise ValidationError({"page_size": ["PageSize must be an integer between 1 and 100."]})
            if size < 1 or size > self.max_page_size:
                raise ValidationError({"page_size": ["PageSize must be between 1 and 100."]})
            return size
        return self.page_size

    def get_paginated_response(self, data):
        return Response({
            "items": data,
            "total_count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
        })
