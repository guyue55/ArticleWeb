"""文章序列化器，用于处理UUID关系的数据序列化。"""

from typing import List, Dict, Any, Optional
from apps.articles.models import Article, Category
from apps.users.models import User


class ArticleUUIDSerializer:
    """处理基于UUID关系的文章序列化器。"""
    
    @staticmethod
    def get_user_by_uuid(user_uuid: str) -> Optional[Dict[str, Any]]:
        """根据UUID获取用户信息。"""
        try:
            user = User.objects.get(uuid=user_uuid, is_active=True)
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'phone': user.phone or '',
                'bio': user.bio or '',
                'birth_date': user.birth_date.isoformat() if user.birth_date else None,
                'location': user.location or '',
                'website': user.website or '',
                'is_verified': getattr(user, 'is_verified', False),
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'avatar_url': '',  # 暂时为空，后续可以添加头像逻辑
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username,
                'profile': None,  # 暂时为空，后续可以添加用户资料逻辑
            }
        except User.DoesNotExist:
            return {
                'id': 0,
                'username': '未知用户',
                'email': '',
                'first_name': '',
                'last_name': '',
                'phone': '',
                'bio': '',
                'birth_date': None,
                'location': '',
                'website': '',
                'is_verified': False,
                'is_active': False,
                'date_joined': '2025-01-01T00:00:00+00:00',
                'last_login': None,
                'avatar_url': '',
                'full_name': '未知用户',
                'profile': None,
            }
    
    @staticmethod
    def get_category_by_uuid(category_uuid: str) -> Optional[Dict[str, Any]]:
        """根据UUID获取分类信息。"""
        try:
            category = Category.objects.get(uuid=category_uuid, is_active=True)
            return {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
            }
        except Category.DoesNotExist:
            return {
                'id': 0,
                'name': '未知分类',
                'slug': 'unknown',
                'description': '',
            }
    

    @classmethod
    def serialize_article_list(cls, articles: List[Article]) -> List[Dict[str, Any]]:
        """序列化文章列表。"""
        result = []
        for article in articles:
            author = cls.get_user_by_uuid(article.author_uuid)
            category = cls.get_category_by_uuid(article.category_uuid)
            
            result.append({
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'summary': article.summary,
                'author': author,
                'category': category,
                'featured_image': article.featured_image,
                'status': article.status,
                'is_featured': article.is_featured,
                'is_top': article.is_top,
            'view_count': article.view_count,
            'download_count': article.download_count,
            'publish_time': article.published_at.isoformat() if article.published_at else None,
                'create_time': article.create_time.isoformat(),
            })
        
        return result
    
    @classmethod
    def serialize_article_detail(cls, article: Article) -> Dict[str, Any]:
        """序列化文章详情。"""
        author = cls.get_user_by_uuid(article.author_uuid)
        category = cls.get_category_by_uuid(article.category_uuid)
        
        # 读取元数据内容
        meta_content = cls._read_meta_content(article)
        
        return {
            'id': article.id,
            'title': article.title,
            'slug': article.slug,
            'summary': article.summary,
            'content': article.content,
            'meta_content': meta_content,  # 添加元数据内容
            'file_info': article.file_info,  # 添加文件信息
            'author': author,
            'category': category,
            'featured_image': article.featured_image,
            'status': article.status,
            'is_featured': article.is_featured,
            'is_top': article.is_top,
            'view_count': article.view_count,
            'download_count': article.download_count,
            'claim_count': article.claim_count,
            'file_attachment': str(article.file_attachment) if article.file_attachment else '',
            'file_size': article.file_size,
            'is_downloadable': article.is_downloadable,
            'is_claimable': article.is_claimable,
            'publish_time': article.published_at.isoformat() if article.published_at else None,
            'create_time': article.create_time.isoformat(),
            'update_time': article.update_time.isoformat() if article.update_time else None,
        }
    
    @staticmethod
    def _read_meta_content(article: Article) -> Optional[Dict[str, Any]]:
        """读取文章的元数据内容。"""
        import json
        import os
        from django.conf import settings
        
        try:
            file_info = article.file_info or {}
            meta_file_path = None
            
            # 尝试获取元数据文件路径
            if "meta" in file_info:
                meta_file_path = file_info["meta"]
            elif "meta_file" in file_info:
                meta_file_path = file_info["meta_file"]
            
            if not meta_file_path:
                return None
            
            # 构建完整的文件路径
            if meta_file_path.startswith('/'):
                full_path = meta_file_path
            else:
                # 如果是相对路径，添加静态文件URL前缀
                full_path = f"{settings.STATIC_URL}{meta_file_path}"
                full_path = full_path.replace("/", "", 1)
            
            # 读取并解析JSON文件
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return json.loads(content)
            
            return None
            
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            print(f"读取元数据文件失败: {str(e)}")
            return None