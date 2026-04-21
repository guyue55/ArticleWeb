# -*- coding: utf-8 -*-
"""
AI核心服务类，集成 LiteLLM 和 Jinja2
实现提示词渲染、多供应商模型调用及生成记录管理
"""

import logging
from typing import Any, Dict, List, Optional

import litellm
import requests
from django.utils import timezone
from jinja2 import Template

from ..models import AIModel, AIProvider, GenerationHistory, PromptTemplate

logger = logging.getLogger(__name__)


class AIService:
    """AI核心服务类"""

    @staticmethod
    def _wrap_prompt_in_chinese(prompt: str) -> str:
        return (
            "请用简体中文理解并完成以下任务，最终输出必须为简体中文。"
            "如果任务描述中包含英文内容，请先自行理解并转述为中文后再执行。\n\n"
            f"任务描述：\n{prompt}"
        )

    @classmethod
    def scan_provider_models(cls, provider_id: int) -> Dict[str, Any]:
        """
        通过 OpenAPI 接口扫描供应商支持的模型。

        Args:
            provider_id: AIProvider 模型 ID

        Returns:
            dict: 扫描结果统计
        """
        try:
            provider = AIProvider.objects.get(id=provider_id, is_active=True)
            if not provider.is_openapi:
                return {"success": False, "error": "该供应商不支持 OpenAPI 标准扫描"}

            # 拼接 /v1/models 接口
            models_url = f"{provider.api_base.rstrip('/')}/models"
            headers = {"Authorization": f"Bearer {provider.api_key}"}

            logger.info(f"正在扫描供应商 {provider.name} 的模型")
            response = requests.get(models_url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            model_list = data.get("data", [])

            created_count = 0
            updated_count = 0

            for m in model_list:
                model_id = m.get("id")
                if not model_id:
                    continue

                # 自动创建或更新 AIModel
                ai_model, created = AIModel.objects.update_or_create(
                    provider=provider,
                    name=model_id,
                    defaults={
                        "display_name": model_id,
                        "is_available": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            # 更新最后扫描时间
            provider.last_scanned_at = timezone.now()
            provider.save(update_fields=["last_scanned_at"])

            return {
                "success": True,
                "created": created_count,
                "updated": updated_count,
                "total": len(model_list),
            }

        except AIProvider.DoesNotExist:
            return {"success": False, "error": "未找到供应商"}
        except requests.exceptions.RequestException as e:
            logger.error(f"供应商 {provider_id} 请求失败: {type(e).__name__}")
            return {"success": False, "error": "网络请求失败，请检查配置或网络"}
        except Exception as e:
            logger.error(f"模型扫描失败: {type(e).__name__}")
            return {"success": False, "error": "系统内部错误"}

    @staticmethod
    def render_prompt(template_content: str, inputs: Dict[str, Any]) -> str:
        """
        使用 Jinja2 渲染提示词模板。

        Args:
            template_content: Jinja2 模板字符串
            inputs: 填充模板的变量字典

        Returns:
            str: 渲染后的完整提示词
        """
        template = Template(template_content)
        return template.render(**inputs)

    @classmethod
    def generate_content(
        cls,
        provider_id: int,
        model_name: str,
        prompt: str,
        user_uuid: str,
        sources: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        调用 AI 模型生成内容。

        Args:
            provider_id: AIProvider 模型 ID
            model_name: 模型名称（如 ernie-bot-4, gpt-4）
            prompt: 完整的提示词内容
            user_uuid: 执行操作的用户 UUID
            sources: 参考来源链接列表

        Returns:
            dict: 包含生成结果和状态的字典
        """
        try:
            provider = AIProvider.objects.get(id=provider_id, is_active=True)
        except AIProvider.DoesNotExist:
            return {
                "success": False,
                "error": f"未找到 ID 为 {provider_id} 的活跃 AI 供应商",
            }

        litellm_model = model_name
        if "/" not in litellm_model and getattr(provider, "is_openapi", False):
            litellm_model = f"openai/{litellm_model}"

        final_prompt = cls._wrap_prompt_in_chinese(prompt)

        # 创建初始生成记录
        history = GenerationHistory.objects.create(
            user_uuid=user_uuid,
            prompt=final_prompt,
            sources=sources or [],
            status="pending",
        )

        try:
            # 调用 LiteLLM
            # litellm 会根据 model_name 和 provider 配置自动路由
            response = litellm.completion(
                model=litellm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的中文写作助手，输出必须为简体中文。",
                    },
                    {"role": "user", "content": final_prompt},
                ],
                api_base=provider.api_base,
                api_key=provider.api_key,
                **provider.config,
            )

            result_text = response.choices[0].message.content

            # 更新成功记录
            history.result = result_text
            history.status = "success"
            history.save()

            return {
                "success": True,
                "result": result_text,
                "history_id": history.id,
            }

        except Exception as e:
            err_type = type(e).__name__
            err_detail = str(e)
            logger.error(
                "AI 生成失败 (供应商: %s): %s: %s", provider_id, err_type, err_detail
            )
            history.status = "failed"
            history.error_message = f"{err_type}: {err_detail}"[:500]
            history.save()

            if provider and (
                provider.name.lower() == "ollama"
                or "127.0.0.1:11434" in (provider.api_base or "")
            ):
                user_error = (
                    "Ollama 未启动或不可访问，请先启动 Ollama"
                    "（OpenAI 兼容接口默认 http://127.0.0.1:11434/v1），"
                    "或切换到其他供应商。"
                )
            else:
                user_error = f"AI内容生成失败：{err_type}"

            return {
                "success": False,
                "error": user_error,
                "history_id": history.id,
            }

    @classmethod
    def generate_from_template(
        cls,
        template_id: int,
        provider_id: int,
        model_name: str,
        inputs: Dict[str, Any],
        user_uuid: str,
        sources: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        基于模板生成内容。

        Args:
            template_id: PromptTemplate 模型 ID
            provider_id: AIProvider 模型 ID
            model_name: 模型名称
            inputs: 模板变量输入值
            user_uuid: 用户 UUID
            sources: 参考来源

        Returns:
            dict: 生成结果
        """
        try:
            template = PromptTemplate.objects.get(
                id=template_id,
                is_active=True,
            )
            rendered_prompt = cls.render_prompt(template.content, inputs)

            return cls.generate_content(
                provider_id=provider_id,
                model_name=model_name,
                prompt=rendered_prompt,
                user_uuid=user_uuid,
                sources=sources,
            )
        except PromptTemplate.DoesNotExist:
            return {
                "success": False,
                "error": f"未找到 ID 为 {template_id} 的活跃提示词模板",
            }
        except Exception as e:
            logger.error(f"模板生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    @classmethod
    def generate_image_prompt(
        cls,
        provider_id: int,
        model_name: str,
        article_content: str,
        user_uuid: str,
    ) -> Dict[str, Any]:
        """
        基于文章内容生成图片生成提示词。

        Args:
            provider_id: AIProvider 模型 ID
            model_name: 模型名称 (文本模型)
            article_content: 文章内容
            user_uuid: 用户 UUID

        Returns:
            dict: 包含生成的图片提示词
        """
        prompt = (
            "请根据以下文章内容，生成一段用于 AI 绘图模型（如 DALL-E 3）的提示词。"
            "要求：描述准确、富有美感、适合作为文章配图。"
            "只需返回提示词内容，不要有其他解释。\n\n"
            f"文章内容：\n{article_content[:2000]}"
        )

        result = cls.generate_content(
            provider_id=provider_id,
            model_name=model_name,
            prompt=prompt,
            user_uuid=user_uuid,
        )

        if result["success"]:
            # 清理可能存在的引号或多余文字
            image_prompt = result["result"].strip().strip('"').strip("'")
            return {"success": True, "prompt": image_prompt}

        return result

    @classmethod
    def generate_image(
        cls,
        provider_id: int,
        model_name: str,
        prompt: str,
        user_uuid: str,
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """
        调用 AI 模型生成图片。

        Args:
            provider_id: AIProvider 模型 ID
            model_name: 模型名称 (图片模型，如 dall-e-3)
            prompt: 图片生成提示词
            user_uuid: 用户 UUID
            size: 图片尺寸
            quality: 图片质量

        Returns:
            dict: 包含图片 URL 或本地路径
        """
        try:
            provider = AIProvider.objects.get(id=provider_id, is_active=True)
        except AIProvider.DoesNotExist:
            return {"success": False, "error": "未找到活跃的 AI 供应商"}

        # 创建生成记录
        history = GenerationHistory.objects.create(
            user_uuid=user_uuid,
            prompt=f"[IMAGE GENERATION] {prompt}",
            status="pending",
        )

        try:
            # 调用 LiteLLM 图片生成
            # 注意：某些供应商可能需要特定的参数格式
            response = litellm.image_generation(
                model=model_name,
                prompt=prompt,
                api_base=provider.api_base,
                api_key=provider.api_key,
                size=size,
                quality=quality,
                **provider.config,
            )

            # LiteLLM 返回的数据结构通常包含 URL
            # 兼容不同版本的返回格式 (对象或字典)
            image_data = response.data[0]
            if hasattr(image_data, "url"):
                image_url = image_data.url
            elif isinstance(image_data, dict):
                image_url = image_data.get("url")
            else:
                image_url = str(image_data)

            # 更新成功记录
            history.result = image_url
            history.status = "success"
            history.save()

            return {
                "success": True,
                "image_url": image_url,
                "history_id": history.id,
            }

        except Exception as e:
            logger.error(f"AI 图片生成失败: {type(e).__name__}: {str(e)}")
            history.status = "failed"
            history.error_message = str(e)
            history.save()

            return {
                "success": False,
                "error": f"图片生成失败: {str(e)}",
                "history_id": history.id,
            }

    @classmethod
    def polish_content(
        cls,
        provider_id: int,
        model_name: str,
        content: str,
        instruction: str,
        user_uuid: str,
    ) -> Dict[str, Any]:
        """
        根据用户指令对内容进行润色/修改。

        Args:
            provider_id: AIProvider 模型 ID
            model_name: 模型名称
            content: 原始内容
            instruction: 修改指令 (如 "扩写"、"精简"、"改变风格")
            user_uuid: 用户 UUID

        Returns:
            dict: 包含修改后的内容
        """
        prompt = (
            "你是一个专业的文章编辑。请根据以下修改指令，对提供的文章内容进行优化或修改。"
            "只需返回修改后的完整内容，不要有任何解释或多余的文字。\n\n"
            f"修改指令：{instruction}\n\n"
            f"原始内容：\n{content}"
        )

        return cls.generate_content(
            provider_id=provider_id,
            model_name=model_name,
            prompt=prompt,
            user_uuid=user_uuid,
        )
