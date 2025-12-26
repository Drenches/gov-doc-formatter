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


class FormatResponse(BaseModel):
    """格式化响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="处理消息")
    output_filename: Optional[str] = Field(None, description="输出文件名")
    download_url: Optional[str] = Field(None, description="下载链接")
    error_message: Optional[str] = Field(None, description="错误信息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
