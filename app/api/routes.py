"""
API路由模块
"""
import uuid
import shutil
import os
import zipfile
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, reload_api_key, reload_base_url, reload_model, SUGGESTED_MODELS
from app.core.document_parser import DocumentParser
from app.core.llm_analyzer import LLMAnalyzer
from app.core.formatter import DocumentFormatter
from app.core.font_config import DocumentFontConfig
from app.models.schemas import FormatResponse, HealthResponse, AnalysisResponse, ProcessingInfo

router = APIRouter()


# ==================== 配置相关接口 ====================

class ConfigStatusResponse(BaseModel):
    """配置状态响应"""
    configured: bool
    message: str = ""
    data_dir: str = ""
    default_data_dir: str = ""
    base_url: str = ""


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    data_dir: Optional[str] = None


class SaveConfigResponse(BaseModel):
    """保存配置响应"""
    success: bool
    message: str = ""


class BrowseFolderResponse(BaseModel):
    """文件夹选择响应"""
    success: bool
    path: str = ""
    message: str = ""


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str


class GetModelsResponse(BaseModel):
    """获取模型列表响应"""
    success: bool
    current_model: str
    suggested_models: list[ModelInfo]
    allow_custom: bool = True


class SetModelRequest(BaseModel):
    """设置模型请求"""
    model: str


class SetModelResponse(BaseModel):
    """设置模型响应"""
    success: bool
    message: str = ""
    current_model: str = ""


@router.get("/config/browse-folder", response_model=BrowseFolderResponse)
async def browse_folder():
    """打开系统文件夹选择对话框"""
    import sys
    if sys.platform != 'win32':
        return BrowseFolderResponse(
            success=False,
            message="此功能仅支持 Windows 系统"
        )

    try:
        import threading
        import queue
        import ctypes

        # 启用 DPI 感知，使对话框跟随系统缩放
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # 备用方案
            except Exception:
                pass

        result_queue = queue.Queue()

        def show_dialog():
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()  # 隐藏主窗口
                root.attributes('-topmost', True)  # 置顶

                folder_path = filedialog.askdirectory(
                    title="选择数据存储位置",
                    mustexist=False
                )

                root.destroy()
                result_queue.put(('success', folder_path or ''))
            except Exception as e:
                result_queue.put(('error', str(e)))

        # 在单独的线程中运行对话框
        dialog_thread = threading.Thread(target=show_dialog)
        dialog_thread.start()
        dialog_thread.join(timeout=120)

        if dialog_thread.is_alive():
            return BrowseFolderResponse(
                success=False,
                message="选择超时，请重试"
            )

        try:
            status, result = result_queue.get_nowait()
            if status == 'success' and result:
                return BrowseFolderResponse(
                    success=True,
                    path=result
                )
            elif status == 'error':
                return BrowseFolderResponse(
                    success=False,
                    message=f"打开文件夹选择器失败: {result}"
                )
            else:
                return BrowseFolderResponse(
                    success=False,
                    message="未选择文件夹"
                )
        except queue.Empty:
            return BrowseFolderResponse(
                success=False,
                message="未获取到选择结果"
            )

    except Exception as e:
        return BrowseFolderResponse(
            success=False,
            message=f"打开文件夹选择器失败: {str(e)}"
        )


@router.get("/config/status", response_model=ConfigStatusResponse)
async def get_config_status():
    """检查是否已配置 API Key"""
    try:
        from config_manager import config_manager
        has_key = config_manager.has_api_key()
        return ConfigStatusResponse(
            configured=has_key,
            message="已配置" if has_key else "未配置",
            data_dir=config_manager.get_data_dir(),
            default_data_dir=config_manager.get_default_data_dir_str(),
            base_url=config_manager.get_base_url() or ""
        )
    except ImportError:
        # 开发模式下可能没有 config_manager
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
        has_key = bool(api_key)
        return ConfigStatusResponse(
            configured=has_key,
            message="已配置（环境变量）" if has_key else "未配置",
            data_dir="",
            default_data_dir="",
            base_url=os.getenv("OPENAI_BASE_URL", "")
        )


@router.post("/config/save", response_model=SaveConfigResponse)
async def save_config(request: SaveConfigRequest):
    """保存 API Key、Base URL 和数据目录配置"""
    try:
        from config_manager import config_manager

        # 如果用户指定了数据目录,先设置数据目录
        if request.data_dir and request.data_dir.strip():
            data_dir = request.data_dir.strip()
            # 验证路径是否有效
            from pathlib import Path
            data_path = Path(data_dir)

            # 自动在用户选择的目录下创建"公文自动排版工具"子文件夹
            # 避免文件散落在用户选择的目录中
            if not data_path.name == "公文自动排版工具":
                data_path = data_path / "公文自动排版工具"

            try:
                # 尝试创建目录（如果不存在）
                data_path.mkdir(parents=True, exist_ok=True)
                config_manager.set_data_dir(str(data_path))
            except Exception as e:
                return SaveConfigResponse(
                    success=False,
                    message=f"数据目录无效或无法创建: {str(e)}"
                )

        # 保存 Base URL（如果提供）
        if request.base_url is not None and request.base_url.strip():
            config_manager.set_base_url(request.base_url.strip())
            reload_base_url()

        # 保存 API Key（如果提供且非空）
        if request.api_key and request.api_key.strip():
            api_key = request.api_key.strip()
            if len(api_key) < 10:
                return SaveConfigResponse(
                    success=False,
                    message="API Key 格式不正确"
                )
            config_manager.set_api_key(api_key)
            # 更新环境变量和配置
            os.environ["OPENAI_API_KEY"] = api_key
            reload_api_key()

        return SaveConfigResponse(
            success=True,
            message="配置保存成功"
        )
    except Exception as e:
        return SaveConfigResponse(
            success=False,
            message=f"保存失败: {str(e)}"
        )


@router.get("/models", response_model=GetModelsResponse)
async def get_models():
    """获取当前模型和可用模型列表"""
    try:
        from config_manager import config_manager
        current_model = config_manager.get_model()
    except ImportError:
        from app.config import LLM_MODEL
        current_model = LLM_MODEL

    return GetModelsResponse(
        success=True,
        current_model=current_model,
        suggested_models=[ModelInfo(**model) for model in SUGGESTED_MODELS],
        allow_custom=True
    )


@router.post("/models/set", response_model=SetModelResponse)
async def set_model(request: SetModelRequest):
    """设置当前使用的模型"""
    model = request.model.strip()

    if not model:
        return SetModelResponse(
            success=False,
            message="模型名称不能为空"
        )

    try:
        from config_manager import config_manager

        # 保存模型配置
        config_manager.set_model(model)

        # 更新环境变量和配置
        os.environ["LLM_MODEL"] = model
        reload_model()

        return SetModelResponse(
            success=True,
            message="模型切换成功",
            current_model=model
        )
    except Exception as e:
        return SetModelResponse(
            success=False,
            message=f"切换失败: {str(e)}"
        )


# ==================== 原有接口 ====================


def cleanup_file(file_path: Path):
    """后台任务：清理临时文件"""
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@router.post("/format", response_model=FormatResponse)
async def format_document(
    file: UploadFile = File(...),
    font_config: str = Form("{}"),  # JSON格式的字体配置
    background_tasks: BackgroundTasks = None
):
    """
    上传并格式化公文文档

    Args:
        file: 上传的Word文档
        font_config: 字体配置(JSON格式),格式如:
            {
                "global_english_font": "Times New Roman",  # 或 "follow" 表示跟随中文字体
                "title": {"chinese_font": "方正小标宋简体", "bold": false, "size": 22},
                "body": {"chinese_font": "仿宋_GB2312", "bold": false, "size": 16},
                ...
            }
            如果为空或{},则使用GB/T 9704-2012默认配置
        background_tasks: 后台任务

    Returns:
        FormatResponse: 格式化结果
    """
    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，仅支持 .docx, .doc"
        )

    # 验证文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 生成唯一文件名
    unique_id = str(uuid.uuid4())[:8]
    input_filename = f"{unique_id}_{file.filename}"
    input_path = UPLOAD_DIR / input_filename

    # 保存上传的文件
    try:
        with open(input_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        # 1. 解析字体配置（在分析前，因为需要传递给 analyzer）
        import json
        try:
            font_config_dict = json.loads(font_config) if font_config and font_config != "{}" else {}
            doc_font_config = DocumentFontConfig.from_dict(font_config_dict) if font_config_dict else DocumentFontConfig()
        except json.JSONDecodeError:
            doc_font_config = DocumentFontConfig()  # 解析失败则使用默认配置

        # 2. 解析文档
        parser = DocumentParser(input_path)
        doc_text = parser.get_text_for_llm()

        # 3. 使用LLM分析结构（传递字体配置）
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text, font_config=doc_font_config)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

        # 获取处理过程信息
        process_info = analyzer.get_last_process_info()

        # 4. 格式化文档（使用之前解析的 doc_font_config）
        formatter = DocumentFormatter(font_config=doc_font_config)
        formatter.format_document(analysis_result)

        # 5. 保存输出文件
        output_filename = f"formatted_{input_filename}"
        output_path = OUTPUT_DIR / output_filename
        formatter.save(output_path)

        # 清理上传的临时文件
        if background_tasks:
            background_tasks.add_task(cleanup_file, input_path)

        # 构建处理信息
        processing_info = None
        if process_info:
            processing_info = ProcessingInfo(
                was_cleaned=process_info.get("was_cleaned", False),
                original_confidence=0.0,  # 新架构不再使用置信度
                retry_count=process_info.get("retry_count", 0),
                issues_fixed=process_info.get("issues_fixed", [])
            )

        return FormatResponse(
            success=True,
            message="文档格式化成功",
            output_filename=output_filename,
            download_url=f"/api/download/{output_filename}",
            processing_info=processing_info
        )

    except HTTPException:
        raise
    except Exception as e:
        # 清理临时文件
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/format-text", response_model=FormatResponse)
async def format_text(
    text: str = Form(...),
    font_config: str = Form("{}"),  # JSON格式的字体配置
    background_tasks: BackgroundTasks = None
):
    """
    直接格式化粘贴的文本内容

    Args:
        text: 粘贴的公文文本内容
        font_config: 字体配置(JSON格式),格式如:
            {
                "global_english_font": "Times New Roman",  # 或 "follow" 表示跟随中文字体
                "title": {"chinese_font": "方正小标宋简体", "bold": false, "size": 22},
                "body": {"chinese_font": "仿宋_GB2312", "bold": false, "size": 16},
                ...
            }
            如果为空或{},则使用GB/T 9704-2012默认配置
        background_tasks: 后台任务

    Returns:
        FormatResponse: 格式化结果
    """
    # 验证文本内容
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    # 限制文本长度（50000字符）
    max_chars = 50000
    if len(text) > max_chars:
        raise HTTPException(
            status_code=400,
            detail=f"文本过长，最大支持 {max_chars} 字符"
        )

    try:
        # 1. 解析字体配置（在分析前，因为需要传递给 analyzer）
        import json
        try:
            font_config_dict = json.loads(font_config) if font_config and font_config != "{}" else {}
            doc_font_config = DocumentFontConfig.from_dict(font_config_dict) if font_config_dict else DocumentFontConfig()
        except json.JSONDecodeError:
            doc_font_config = DocumentFontConfig()  # 解析失败则使用默认配置

        # 2. 预处理文本，模拟 DocumentParser.get_text_for_llm() 的输出格式
        doc_text = _preprocess_text(text)

        # 3. 使用LLM分析结构（传递字体配置）
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text, font_config=doc_font_config)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

        # 获取处理过程信息
        process_info = analyzer.get_last_process_info()

        # 4. 格式化文档（使用之前解析的 doc_font_config）
        formatter = DocumentFormatter(font_config=doc_font_config)
        formatter.format_document(analysis_result)

        # 5. 保存输出文件
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"formatted_text_{unique_id}.docx"
        output_path = OUTPUT_DIR / output_filename
        formatter.save(output_path)

        # 构建处理信息
        processing_info = None
        if process_info:
            processing_info = ProcessingInfo(
                was_cleaned=process_info.get("was_cleaned", False),
                original_confidence=0.0,  # 新架构不再使用置信度
                retry_count=process_info.get("retry_count", 0),
                issues_fixed=process_info.get("issues_fixed", [])
            )

        return FormatResponse(
            success=True,
            message="文档格式化成功",
            output_filename=output_filename,
            download_url=f"/api/download/{output_filename}",
            processing_info=processing_info
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


def _preprocess_text(text: str) -> str:
    """
    预处理文本，将纯文本转换为LLM分析所需的格式

    Args:
        text: 原始文本

    Returns:
        str: 格式化后的文本（带段落索引）
    """
    lines = []
    index = 0

    # 按换行符分割段落
    paragraphs = text.split('\n')

    for para in paragraphs:
        para = para.strip()
        if para:  # 过滤空行
            lines.append(f"[{index}] {para}")
            index += 1

    return "\n".join(lines)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    分析文档结构（不进行格式化）

    Args:
        file: 上传的Word文档

    Returns:
        AnalysisResponse: 分析结果
    """
    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}"
        )

    # 生成唯一文件名并保存
    unique_id = str(uuid.uuid4())[:8]
    input_filename = f"{unique_id}_{file.filename}"
    input_path = UPLOAD_DIR / input_filename

    content = await file.read()
    try:
        with open(input_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        # 解析并分析文档
        parser = DocumentParser(input_path)
        doc_text = parser.get_text_for_llm()

        analyzer = LLMAnalyzer()
        result = analyzer.analyze(doc_text)

        # 清理临时文件
        if background_tasks:
            background_tasks.add_task(cleanup_file, input_path)

        return AnalysisResponse(
            success=result.success,
            title=result.title,
            elements=[
                {
                    "index": e.index,
                    "element_type": e.element_type,
                    "content": e.content
                }
                for e in result.elements
            ],
            issuing_authority=result.issuing_authority,
            date=result.date,
            error_message=result.error_message
        )

    except Exception as e:
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str, background_tasks: BackgroundTasks):
    """
    下载格式化后的文档

    Args:
        filename: 文件名

    Returns:
        FileResponse: 文件下载响应
    """
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 设置下载后清理文件（可选，根据需求决定是否保留）
    # background_tasks.add_task(cleanup_file, file_path)

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ==================== 批量处理接口 ====================

class BatchFileResult(BaseModel):
    """单个文件的批量处理结果"""
    filename: str
    success: bool
    output_filename: Optional[str] = None
    error_message: Optional[str] = None
    processing_info: Optional[ProcessingInfo] = None


class BatchFormatResponse(BaseModel):
    """批量格式化响应"""
    success: bool
    message: str
    total_files: int
    successful_files: int
    failed_files: int
    results: List[BatchFileResult]
    batch_id: str  # 批次ID，用于下载打包文件


@router.post("/format-batch", response_model=BatchFormatResponse)
async def format_batch(
    files: List[UploadFile] = File(...),
    font_config: str = Form("{}"),
    background_tasks: BackgroundTasks = None
):
    """
    批量上传并格式化多个公文文档

    Args:
        files: 上传的多个Word文档
        font_config: 字体配置(JSON格式)
        background_tasks: 后台任务

    Returns:
        BatchFormatResponse: 批量处理结果
    """
    # 生成批次ID
    batch_id = f"batch_{uuid.uuid4().hex[:12]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = OUTPUT_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    # 解析字体配置
    import json
    try:
        font_config_dict = json.loads(font_config) if font_config and font_config != "{}" else {}
        doc_font_config = DocumentFontConfig.from_dict(font_config_dict) if font_config_dict else DocumentFontConfig()
    except json.JSONDecodeError:
        doc_font_config = DocumentFontConfig()

    results = []
    successful_count = 0
    failed_count = 0

    # 处理每个文件
    for file in files:
        file_result = await _process_single_file_in_batch(
            file,
            doc_font_config,
            batch_dir
        )
        results.append(file_result)

        if file_result.success:
            successful_count += 1
        else:
            failed_count += 1

    # 如果所有文件都处理成功，创建ZIP包
    if successful_count > 0:
        zip_filename = f"{batch_id}.zip"
        zip_path = OUTPUT_DIR / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for result in results:
                if result.success and result.output_filename:
                    file_path = batch_dir / result.output_filename
                    if file_path.exists():
                        zipf.write(file_path, result.output_filename)

        # 清理批次目录（可选）
        if background_tasks:
            background_tasks.add_task(cleanup_batch_dir, batch_dir)

    return BatchFormatResponse(
        success=True,
        message=f"批量处理完成: {successful_count} 个成功, {failed_count} 个失败",
        total_files=len(files),
        successful_files=successful_count,
        failed_files=failed_count,
        results=results,
        batch_id=batch_id
    )


async def _process_single_file_in_batch(
    file: UploadFile,
    doc_font_config: DocumentFontConfig,
    batch_dir: Path
) -> BatchFileResult:
    """
    在批量处理中处理单个文件

    Args:
        file: 上传的文件
        doc_font_config: 字体配置
        batch_dir: 批次输出目录

    Returns:
        BatchFileResult: 单个文件的处理结果
    """
    try:
        # 验证文件类型
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return BatchFileResult(
                filename=file.filename,
                success=False,
                error_message=f"不支持的文件类型: {file_ext}"
            )

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        if len(content) > MAX_FILE_SIZE:
            return BatchFileResult(
                filename=file.filename,
                success=False,
                error_message=f"文件过大，超过 {MAX_FILE_SIZE / 1024 / 1024}MB 限制"
            )

        # 保存临时文件
        input_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        input_path = UPLOAD_DIR / input_filename

        with open(input_path, "wb") as f:
            f.write(content)

        try:
            # 解析文档
            parser = DocumentParser(input_path)
            doc_text = parser.get_text_for_llm()

            # LLM分析
            analyzer = LLMAnalyzer()
            analysis_result = analyzer.analyze(doc_text, font_config=doc_font_config)

            if not analysis_result.success:
                return BatchFileResult(
                    filename=file.filename,
                    success=False,
                    error_message=f"文档分析失败: {analysis_result.error_message}"
                )

            # 获取处理信息
            process_info = analyzer.get_last_process_info()

            # 格式化文档
            formatter = DocumentFormatter(font_config=doc_font_config)
            formatter.format_document(analysis_result)

            # 保存到批次目录
            output_filename = f"formatted_{file.filename}"
            output_path = batch_dir / output_filename
            formatter.save(output_path)

            # 清理临时文件
            if input_path.exists():
                input_path.unlink()

            # 构建处理信息
            processing_info = None
            if process_info:
                processing_info = ProcessingInfo(
                    was_cleaned=process_info.get("was_cleaned", False),
                    original_confidence=0.0,
                    retry_count=process_info.get("retry_count", 0),
                    issues_fixed=process_info.get("issues_fixed", [])
                )

            return BatchFileResult(
                filename=file.filename,
                success=True,
                output_filename=output_filename,
                processing_info=processing_info
            )

        except Exception as e:
            # 清理临时文件
            if input_path.exists():
                input_path.unlink()

            return BatchFileResult(
                filename=file.filename,
                success=False,
                error_message=f"处理失败: {str(e)}"
            )

    except Exception as e:
        return BatchFileResult(
            filename=file.filename,
            success=False,
            error_message=f"文件读取失败: {str(e)}"
        )


@router.get("/download-batch/{batch_id}")
async def download_batch(batch_id: str, background_tasks: BackgroundTasks):
    """
    下载批量处理后的ZIP文件

    Args:
        batch_id: 批次ID
        background_tasks: 后台任务

    Returns:
        FileResponse: ZIP文件下载响应
    """
    zip_filename = f"{batch_id}.zip"
    zip_path = OUTPUT_DIR / zip_filename

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="批量处理文件不存在")

    # 设置下载后清理文件
    if background_tasks:
        background_tasks.add_task(cleanup_file, zip_path)

    return FileResponse(
        path=str(zip_path),
        filename=zip_filename,
        media_type="application/zip"
    )


def cleanup_batch_dir(batch_dir: Path):
    """清理批次目录"""
    try:
        if batch_dir.exists() and batch_dir.is_dir():
            shutil.rmtree(batch_dir)
    except Exception as e:
        print(f"清理批次目录失败: {e}")
