"""
数据模型定义
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentElement(BaseModel):
    """文档元素"""
    index: int = Field(..., description="段落索引")
    element_type: str = Field(..., description="元素类型")
    content: str = Field(..., description="内容")


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool = Field(..., description="是否成功")
    title: Optional[str] = Field(None, description="公文标题")
    elements: List[DocumentElement] = Field(default_factory=list, description="文档元素列表")
    issuing_authority: Optional[str] = Field(None, description="发文机关")
    date: Optional[str] = Field(None, description="成文日期")
    error_message: Optional[str] = Field(None, description="错误信息")


class ProcessingInfo(BaseModel):
    """处理过程信息"""
    was_cleaned: bool = Field(False, description="是否经过文本清洗")
    original_confidence: float = Field(0.0, description="原始规范性置信度")
    retry_count: int = Field(0, description="重试次数")
    issues_fixed: List[str] = Field(default_factory=list, description="修复的问题列表")


class FormatResponse(BaseModel):
    """格式化响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="处理消息")
    output_filename: Optional[str] = Field(None, description="输出文件名")
    download_url: Optional[str] = Field(None, description="下载链接")
    error_message: Optional[str] = Field(None, description="错误信息")
    processing_info: Optional[ProcessingInfo] = Field(None, description="处理过程信息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
