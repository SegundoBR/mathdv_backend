from rest_framework.response import Response


def paginated_response(paginator, page, serializer_fn, many=True):
    """
    Construye una Response paginada estándar.

    Args:
        paginator: Objeto django.core.paginator.Paginator (page.paginator).
        page:      Objeto de página actual (page.number, etc.).
        serializer_fn: Callable que recibe (page, many) y retorna los datos serializados.
                       En CustomPaginator se pasa directamente la data ya serializada.
        many:      Indica si los datos son una lista.

    Returns:
        Response con estructura estándar paginada.
    """
    data = serializer_fn(page, many=many)

    return Response(
        {
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page.number,
            "next": page.next_page_number() if page.has_next() else None,
            "previous": page.previous_page_number() if page.has_previous() else None,
            "results": data,
        }
    )
