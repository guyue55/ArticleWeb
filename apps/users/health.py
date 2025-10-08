"""
用户模块健康检查视图
"""
import time
from django.http import JsonResponse
from django.views import View
from django.core.cache import cache
from django.db import connection
from django.contrib.auth import get_user_model
from .config import UserConfig
from .monitoring import PerformanceMonitor


User = get_user_model()


class HealthCheckView(View):
    """健康检查视图"""
    
    def get(self, request):
        """执行健康检查"""
        start_time = time.time()
        health_status = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'checks': {},
            'performance': {},
            'config': {}
        }
        
        try:
            # 检查数据库连接
            health_status['checks']['database'] = self.check_database()
            
            # 检查缓存
            health_status['checks']['cache'] = self.check_cache()
            
            # 检查用户认证功能
            health_status['checks']['authentication'] = self.check_authentication()
            
            # 检查配置
            health_status['config'] = self.get_config_status()
            
            # 获取性能指标
            health_status['performance'] = self.get_performance_metrics()
            
            # 计算总体状态
            all_checks_passed = all(
                check.get('status') == 'ok' 
                for check in health_status['checks'].values()
            )
            
            if not all_checks_passed:
                health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        # 记录检查耗时
        end_time = time.time()
        health_status['response_time'] = round((end_time - start_time) * 1000, 2)  # 毫秒
        
        # 根据状态返回适当的HTTP状态码
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return JsonResponse(health_status, status=status_code)
    
    def check_database(self):
        """检查数据库连接"""
        try:
            start_time = time.time()
            
            # 执行简单查询
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # 检查用户表
            user_count = User.objects.count()
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            return {
                'status': 'ok',
                'response_time_ms': response_time,
                'user_count': user_count,
                'message': 'Database connection successful'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Database connection failed: {str(e)}'
            }
    
    def check_cache(self):
        """检查缓存功能"""
        try:
            start_time = time.time()
            
            # 测试缓存读写
            test_key = 'health_check_test'
            test_value = f'test_{int(time.time())}'
            
            cache.set(test_key, test_value, 60)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            if cached_value == test_value:
                return {
                    'status': 'ok',
                    'response_time_ms': response_time,
                    'message': 'Cache is working properly'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Cache read/write test failed'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Cache check failed: {str(e)}'
            }
    
    def check_authentication(self):
        """检查用户认证功能"""
        try:
            start_time = time.time()
            
            # 检查认证配置
            auth_enabled = UserConfig.is_api_authentication_enabled()
            
            # 检查用户模型
            user_count = User.objects.count()
            active_user_count = User.objects.filter(is_active=True).count()
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            return {
                'status': 'ok',
                'response_time_ms': response_time,
                'auth_enabled': auth_enabled,
                'total_users': user_count,
                'active_users': active_user_count,
                'message': 'Authentication system working'
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Authentication check failed: {str(e)}'
            }
    
    def get_config_status(self):
        """获取配置状态"""
        return {
            'api_authentication_enabled': UserConfig.is_api_authentication_enabled(),
            'protected_paths_count': len(UserConfig.PROTECTED_PATHS),
            'protected_api_endpoints_count': len(UserConfig.PROTECTED_API_ENDPOINTS)
        }
    
    def get_performance_metrics(self):
        """获取性能指标摘要"""
        try:
            all_metrics = PerformanceMonitor.get_all_metrics()
            
            # 提取关键指标
            summary = {}
            for metric_name, metrics in all_metrics.items():
                if metrics:
                    summary[metric_name] = {
                        'avg_time': round(metrics.get('avg', 0), 3),
                        'call_count': metrics.get('count', 0),
                        'max_time': round(metrics.get('max', 0), 3)
                    }
            
            return summary
            
        except Exception as e:
            return {'error': f'Failed to get performance metrics: {str(e)}'}


class ConfigView(View):
    """配置信息视图"""
    
    def get(self, request):
        """获取当前配置信息"""
        config_info = {
            'api_authentication': {
                'enabled': UserConfig.is_api_authentication_enabled(),
                'description': 'API验证是否启用'
            },
            'protection': {
                'protected_paths': UserConfig.PROTECTED_PATHS,
                'protected_api_endpoints': UserConfig.PROTECTED_API_ENDPOINTS,
                'description': '受保护的路径和API端点'
            }
        }
        
        return JsonResponse(config_info)