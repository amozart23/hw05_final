from django.core.paginator import Paginator
from yatube.settings import POSTS_ON_A_PAGE


def paginator(posts, request):
    paginator = Paginator(posts, POSTS_ON_A_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
