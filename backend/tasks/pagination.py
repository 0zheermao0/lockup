from rest_framework.pagination import PageNumberPagination


class DynamicPageNumberPagination(PageNumberPagination):
    """
    自定义分页类，支持动态页面大小
    """
    page_size = 20  # 默认页面大小
    page_size_query_param = 'page_size'  # 允许客户端通过page_size参数控制页面大小
    max_page_size = 100  # 最大页面大小，防止恶意请求