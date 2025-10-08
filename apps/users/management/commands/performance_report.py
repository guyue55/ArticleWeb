"""
查看用户模块性能指标的管理命令
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.users.monitoring import PerformanceMonitor, CacheMonitor
from apps.users.config import UserConfig
import json


class Command(BaseCommand):
    help = '查看用户模块的性能指标'

    def add_arguments(self, parser):
        parser.add_argument(
            '--metric',
            type=str,
            help='指定要查看的性能指标名称'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='输出格式 (默认: table)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除所有性能指标缓存'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_metrics()
            return

        if options['metric']:
            self.show_single_metric(options['metric'], options['format'])
        else:
            self.show_all_metrics(options['format'])

    def clear_metrics(self):
        """清除性能指标缓存"""
        try:
            # 清除性能监控缓存
            cache_keys = [
                PerformanceMonitor.get_cache_key("anonymous_user_creation"),
                PerformanceMonitor.get_cache_key("cache_hit_rate"),
                PerformanceMonitor.get_cache_key("db_query_time"),
                PerformanceMonitor.get_cache_key("middleware_processing"),
            ]
            
            for key in cache_keys:
                cache.delete(key)
            
            # 清除匿名用户缓存
            cache.delete(UserConfig.ANONYMOUS_USER_CACHE_KEY)
            
            self.stdout.write(
                self.style.SUCCESS('✅ 已清除所有性能指标缓存')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 清除缓存失败: {e}')
            )

    def show_single_metric(self, metric_name, format_type):
        """显示单个性能指标"""
        metrics = PerformanceMonitor.get_metrics(metric_name)
        
        if not metrics:
            self.stdout.write(
                self.style.WARNING(f'⚠️  未找到指标: {metric_name}')
            )
            return

        if format_type == 'json':
            self.stdout.write(json.dumps({metric_name: metrics}, indent=2))
        else:
            self.print_metric_table(metric_name, metrics)

    def show_all_metrics(self, format_type):
        """显示所有性能指标"""
        all_metrics = PerformanceMonitor.get_all_metrics()
        
        # 添加缓存状态
        cache_status = self.get_cache_status()
        all_metrics['cache_status'] = cache_status
        
        if format_type == 'json':
            self.stdout.write(json.dumps(all_metrics, indent=2))
        else:
            self.print_all_metrics_table(all_metrics)

    def get_cache_status(self):
        """获取缓存状态"""
        anonymous_user_cached = cache.get(UserConfig.ANONYMOUS_USER_CACHE_KEY) is not None
        
        return {
            'anonymous_user_cached': anonymous_user_cached,
            'cache_timeout': UserConfig.ANONYMOUS_USER_CACHE_TIMEOUT
        }

    def print_metric_table(self, metric_name, metrics):
        """打印单个指标表格"""
        self.stdout.write(f"\n📊 性能指标: {metric_name}")
        self.stdout.write("=" * 50)
        
        if metrics:
            self.stdout.write(f"调用次数: {metrics.get('count', 0)}")
            self.stdout.write(f"平均耗时: {metrics.get('avg', 0):.3f}s")
            self.stdout.write(f"最小耗时: {metrics.get('min', 0):.3f}s")
            self.stdout.write(f"最大耗时: {metrics.get('max', 0):.3f}s")
            self.stdout.write(f"总耗时: {metrics.get('total', 0):.3f}s")
        else:
            self.stdout.write("暂无数据")

    def print_all_metrics_table(self, all_metrics):
        """打印所有指标表格"""
        self.stdout.write("\n📊 用户模块性能报告")
        self.stdout.write("=" * 80)
        
        # 缓存状态
        cache_status = all_metrics.get('cache_status', {})
        self.stdout.write(f"\n🗄️  缓存状态:")
        self.stdout.write(f"   匿名用户已缓存: {'✅' if cache_status.get('anonymous_user_cached') else '❌'}")
        self.stdout.write(f"   缓存超时时间: {cache_status.get('cache_timeout', 0)}秒")
        
        # 性能指标
        performance_metrics = {k: v for k, v in all_metrics.items() if k != 'cache_status'}
        
        if any(performance_metrics.values()):
            self.stdout.write(f"\n⚡ 性能指标:")
            self.stdout.write("-" * 80)
            self.stdout.write(f"{'指标名称':<25} {'调用次数':<10} {'平均耗时':<12} {'最小耗时':<12} {'最大耗时':<12}")
            self.stdout.write("-" * 80)
            
            for metric_name, metrics in performance_metrics.items():
                if metrics:
                    count = metrics.get('count', 0)
                    avg = metrics.get('avg', 0)
                    min_time = metrics.get('min', 0)
                    max_time = metrics.get('max', 0)
                    
                    # 性能状态指示器
                    status = "🟢" if avg < 0.1 else "🟡" if avg < 0.5 else "🔴"
                    
                    self.stdout.write(
                        f"{status} {metric_name:<22} {count:<10} {avg:<12.3f} {min_time:<12.3f} {max_time:<12.3f}"
                    )
                else:
                    self.stdout.write(f"⚪ {metric_name:<22} {'无数据':<10}")
        else:
            self.stdout.write(f"\n⚠️  暂无性能数据")
        
        # 性能建议
        self.print_performance_recommendations(performance_metrics)

    def print_performance_recommendations(self, metrics):
        """打印性能建议"""
        self.stdout.write(f"\n💡 性能建议:")
        self.stdout.write("-" * 40)
        
        recommendations = []
        
        # 检查匿名用户创建性能
        anonymous_metrics = metrics.get('anonymous_user_creation', {})
        if anonymous_metrics and anonymous_metrics.get('avg', 0) > 0.1:
            recommendations.append("• 匿名用户创建耗时较长，建议检查数据库连接和缓存配置")
        
        # 检查缓存命中率
        cache_metrics = metrics.get('cache_hit_rate', {})
        if cache_metrics and cache_metrics.get('avg', 0) < 0.8:
            recommendations.append("• 缓存命中率较低，建议优化缓存策略")
        
        # 检查数据库查询时间
        db_metrics = metrics.get('db_query_time', {})
        if db_metrics and db_metrics.get('avg', 0) > 0.05:
            recommendations.append("• 数据库查询耗时较长，建议优化查询语句或添加索引")
        
        if recommendations:
            for rec in recommendations:
                self.stdout.write(rec)
        else:
            self.stdout.write("✅ 当前性能表现良好，无需特别优化")
        
        self.stdout.write("")