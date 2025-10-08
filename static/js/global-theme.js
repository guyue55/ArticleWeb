/**
 * 全局主题管理器
 * 负责管理深色模式和自动刷新功能的全局设置
 * 
 * @author ArticleWeb Team
 * @version 1.0.0
 */

class GlobalThemeManager {
    /**
     * 构造函数 - 初始化主题管理器
     */
    constructor() {
        this.autoRefreshInterval = null;
        this.autoRefreshDelay = 30000; // 30秒自动刷新间隔
        this.darkModeInitialized = false; // 标记深色模式是否已初始化
        
        // 页面加载完成后初始化
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    /**
     * 初始化主题管理器
     * 恢复用户的深色模式和自动刷新设置
     */
    init() {
        this.initializeDarkMode();
        this.initializeAutoRefresh();
        this.addGlobalStyles();
    }

    /**
     * 初始化深色模式
     * 从localStorage读取设置并应用
     */
    initializeDarkMode() {
        // 避免重复初始化
        if (this.darkModeInitialized) {
            return;
        }
        
        const isDarkMode = localStorage.getItem('darkMode') === 'true';
        if (isDarkMode) {
            document.body.classList.add('dark-mode');
        }
        
        this.darkModeInitialized = true;
    }

    /**
     * 初始化自动刷新功能
     * 从localStorage读取设置并启动自动刷新
     */
    initializeAutoRefresh() {
        const isAutoRefresh = localStorage.getItem('autoRefresh') === 'true';
        if (isAutoRefresh) {
            this.startAutoRefresh();
        }
    }

    /**
     * 切换深色模式
     * @param {boolean} enabled - 是否启用深色模式
     */
    toggleDarkMode(enabled) {
        if (enabled) {
            document.body.classList.add('dark-mode');
            localStorage.setItem('darkMode', 'true');
        } else {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('darkMode', 'false');
        }
        
        // 显示提示消息
        this.showToast(enabled ? '深色模式已开启' : '深色模式已关闭', 'success');
    }

    /**
     * 切换自动刷新功能
     * @param {boolean} enabled - 是否启用自动刷新
     */
    toggleAutoRefresh(enabled) {
        if (enabled) {
            this.startAutoRefresh();
            localStorage.setItem('autoRefresh', 'true');
            this.showToast('自动刷新已开启（30秒间隔）', 'success');
        } else {
            this.stopAutoRefresh();
            localStorage.setItem('autoRefresh', 'false');
            this.showToast('自动刷新已关闭', 'success');
        }
    }

    /**
     * 启动自动刷新
     */
    startAutoRefresh() {
        // 清除现有的定时器
        this.stopAutoRefresh();
        
        // 启动新的定时器
        this.autoRefreshInterval = setInterval(() => {
            location.reload();
        }, this.autoRefreshDelay);
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    /**
     * 获取当前深色模式状态
     * @returns {boolean} 是否启用深色模式
     */
    isDarkModeEnabled() {
        return localStorage.getItem('darkMode') === 'true';
    }

    /**
     * 获取当前自动刷新状态
     * @returns {boolean} 是否启用自动刷新
     */
    isAutoRefreshEnabled() {
        return localStorage.getItem('autoRefresh') === 'true';
    }

    /**
     * 添加全局深色模式样式
     * 为所有页面添加统一的深色模式CSS变量和样式
     */
    addGlobalStyles() {
        // 检查是否已经添加过样式
        if (document.getElementById('global-dark-mode-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'global-dark-mode-styles';
        style.textContent = `
            /* 深色模式全局CSS变量 */
            body.dark-mode {
                --bg-color: #1a1a1a;
                --card-bg: #2d2d2d;
                --text-primary: #ffffff;
                --text-secondary: #cccccc;
                --text-muted: #999999;
                --border-color: #404040;
                --primary-color: #4a9eff;
                --success-color: #52c41a;
                --warning-color: #faad14;
                --danger-color: #ff4d4f;
                --info-color: #1677ff;
                --shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }

            /* 深色模式基础样式 */
            body.dark-mode {
                background-color: var(--bg-color);
                color: var(--text-primary);
            }

            /* 页面头部深色模式 */
            body.dark-mode .page-header {
                background: linear-gradient(135deg, #333, #555);
            }

            /* 卡片组件深色模式 */
            body.dark-mode .card,
            body.dark-mode .tool-container > div,
            body.dark-mode .input-section,
            body.dark-mode .output-section,
            body.dark-mode .controls-section,
            body.dark-mode .category-card,
            body.dark-mode .article-card,
            body.dark-mode .profile-card,
            body.dark-mode .menu-section {
                background: var(--card-bg);
                border-color: var(--border-color);
                color: var(--text-primary);
            }

            /* 输入框深色模式 */
            body.dark-mode input,
            body.dark-mode textarea,
            body.dark-mode select,
            body.dark-mode .text-area,
            body.dark-mode .preview-area {
                background: var(--card-bg);
                border-color: var(--border-color);
                color: var(--text-primary);
            }

            body.dark-mode input::placeholder,
            body.dark-mode textarea::placeholder {
                color: var(--text-muted);
            }

            /* 按钮深色模式 */
            body.dark-mode .btn-tool,
            body.dark-mode .btn-category,
            body.dark-mode .btn-action {
                background: var(--card-bg);
                border-color: var(--border-color);
                color: var(--text-secondary);
            }

            body.dark-mode .btn-tool:hover,
            body.dark-mode .btn-category:hover,
            body.dark-mode .btn-action:hover {
                background: var(--primary-color);
                color: white;
                border-color: var(--primary-color);
            }

            /* 链接深色模式 */
            body.dark-mode a {
                color: var(--primary-color);
            }

            body.dark-mode a:hover {
                color: #66b3ff;
            }

            /* 表格深色模式 */
            body.dark-mode table {
                background: var(--card-bg);
                color: var(--text-primary);
            }

            body.dark-mode th,
            body.dark-mode td {
                border-color: var(--border-color);
            }

            body.dark-mode th {
                background: var(--bg-color);
            }

            /* 模态框深色模式 */
            body.dark-mode .modal-content {
                background: var(--card-bg);
                color: var(--text-primary);
            }

            /* 导航深色模式 */
            body.dark-mode .nav-link {
                color: var(--text-secondary);
            }

            body.dark-mode .nav-link:hover,
            body.dark-mode .nav-link.active {
                color: var(--primary-color);
            }

            /* 分页深色模式 */
            body.dark-mode .pagination .page-link {
                background: var(--card-bg);
                border-color: var(--border-color);
                color: var(--text-secondary);
            }

            body.dark-mode .pagination .page-link:hover {
                background: var(--primary-color);
                color: white;
            }

            /* 提示框深色模式 */
            body.dark-mode .alert {
                background: var(--card-bg);
                border-color: var(--border-color);
                color: var(--text-primary);
            }
        `;

        document.head.appendChild(style);
    }

    /**
     * 显示提示消息
     * @param {string} message - 提示消息内容
     * @param {string} type - 消息类型 ('success', 'error', 'warning', 'info')
     */
    showToast(message, type = 'info') {
        // 移除现有的提示框
        const existingToast = document.querySelector('.global-toast');
        if (existingToast) {
            existingToast.remove();
        }

        // 创建新的提示框
        const toast = document.createElement('div');
        toast.className = 'global-toast';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;

        // 根据类型设置颜色
        const colors = {
            success: '#52c41a',
            error: '#ff4d4f',
            warning: '#faad14',
            info: '#1677ff'
        };
        toast.style.backgroundColor = colors[type] || colors.info;
        toast.textContent = message;

        // 添加动画样式
        if (!document.getElementById('toast-animations')) {
            const animationStyle = document.createElement('style');
            animationStyle.id = 'toast-animations';
            animationStyle.textContent = `
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOutRight {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(animationStyle);
        }

        document.body.appendChild(toast);

        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, 3000);
    }
}

// 创建全局实例
window.globalThemeManager = new GlobalThemeManager();

// 为了向后兼容，提供全局函数
window.toggleDarkMode = function(enabled) {
    window.globalThemeManager.toggleDarkMode(enabled);
};

window.toggleAutoRefresh = function(enabled) {
    window.globalThemeManager.toggleAutoRefresh(enabled);
};

window.isDarkModeEnabled = function() {
    return window.globalThemeManager.isDarkModeEnabled();
};

window.isAutoRefreshEnabled = function() {
    return window.globalThemeManager.isAutoRefreshEnabled();
};