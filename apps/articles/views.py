from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Article, Category, ArticleClaim
import json


def article_list(request):
    """文章列表页面"""
    return render(request, 'articles/list.html')


def article_detail(request, article_id):
    """文章详情页面"""
    return render(request, 'articles/detail.html', {'article_id': article_id})


# API Views (这些可以被Django Ninja替代，但保留作为备用)
def api_articles(request):
    """获取文章列表API"""
    # 获取查询参数
    search = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    sort = request.GET.get('sort', '-create_time')
    limit = int(request.GET.get('limit', 12))
    offset = int(request.GET.get('offset', 0))
    
    # 构建查询
    queryset = Article.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | 
            Q(summary__icontains=search) |
            Q(content__icontains=search)
        )
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    # 排序
    queryset = queryset.order_by(sort)
    
    # 分页
    total = queryset.count()
    articles = queryset[offset:offset + limit]
    
    # 序列化数据
    data = []
    for article in articles:
        data.append({
            'id': article.id,
            'title': article.title,
            'summary': article.summary,
            'author': {
                'id': article.author.id,
                'username': article.author.username,
            },
            'category': {
                'id': article.category.id,
                'name': article.category.name,
            },
            'is_featured': article.is_featured,
            'is_top': article.is_top,
            'is_claimable': article.is_claimable,
            'is_downloadable': article.is_downloadable,
            'view_count': article.view_count,
            'claim_count': article.claim_count,
            'download_count': article.download_count,
            'create_time': article.create_time.isoformat(),
            'update_time': article.update_time.isoformat(),
        })
    
    return JsonResponse({
        'code': 200,
        'message': 'success',
        'data': {
            'items': data,
            'total': total,
            'limit': limit,
            'offset': offset,
        }
    })


def api_categories(request):
    """获取分类列表API"""
    categories = Category.objects.all().order_by('name')
    data = [{
        'id': category.id,
        'name': category.name,
        'description': category.description,
    } for category in categories]
    
    return JsonResponse({
        'code': 200,
        'message': 'success',
        'data': data
    })