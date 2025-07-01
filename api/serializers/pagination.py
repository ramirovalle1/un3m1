from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 25  # Número de elementos por página
    page_query_param = 'page'  # Parámetro para especificar el número de página en la URL
    page_size_query_param = 'limit'  # Parámetro para especificar el tamaño de la página en la URL

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'prev': self.get_previous_link(),
            'results': data
        })
