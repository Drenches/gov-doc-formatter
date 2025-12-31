"""
API路由模块
"""
import uuid
import shutil
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, reload_api_key
from app.core.document_parser import DocumentParser
from app.core.llm_analyzer import LLMAnalyzer
from app.core.formatter import DocumentFormatter
from app.models.schemas import FormatResponse, HealthResponse, AnalysisResponse, ProcessingInfo

router = APIRouter()


# ==================== 配置相关接口 ====================

class ConfigStatusResponse(BaseModel):
    """配置状态响应"""
    configured: bool
    message: str = ""
    data_dir: str = ""
    default_data_dir: str = ""


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    api_key: str
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
            default_data_dir=config_manager.get_default_data_dir_str()
        )
    except ImportError:
        # 开发模式下可能没有 config_manager
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        has_key = bool(api_key)
        return ConfigStatusResponse(
            configured=has_key,
            message="已配置（环境变量）" if has_key else "未配置",
            data_dir="",
            default_data_dir=""
        )


@router.post("/config/save", response_model=SaveConfigResponse)
async def save_config(request: SaveConfigRequest):
    """保存 API Key 和数据目录配置"""
    api_key = request.api_key.strip()

    if not api_key:
        return SaveConfigResponse(
            success=False,
            message="API Key 不能为空"
        )

    if len(api_key) < 10:
        return SaveConfigResponse(
            success=False,
            message="API Key 格式不正确"
        )

    try:
        from config_manager import config_manager

        # 如果用户指定了数据目录，先设置数据目录
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

        # 保存 API Key
        config_manager.set_api_key(api_key)

        # 更新环境变量和配置
        os.environ["DASHSCOPE_API_KEY"] = api_key
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
    background_tasks: BackgroundTasks = None
):
    """
    上传并格式化公文文档

    Args:
        file: 上传的Word文档
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
        # 1. 解析文档
        parser = DocumentParser(input_path)
        doc_text = parser.get_text_for_llm()

        # 2. 使用LLM分析结构（现在通过 Multi-Agent 系统）
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

        # 获取处理过程信息
        process_info = analyzer.get_last_process_info()

        # 3. 格式化文档
        formatter = DocumentFormatter()
        formatter.format_document(analysis_result)

        # 4. 保存输出文件
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
                original_confidence=process_info.get("router_confidence", 0.0),
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
    background_tasks: BackgroundTasks = None
):
    """
    直接格式化粘贴的文本内容

    Args:
        text: 粘贴的公文文本内容
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
        # 1. 预处理文本，模拟 DocumentParser.get_text_for_llm() 的输出格式
        doc_text = _preprocess_text(text)

        # 2. 使用LLM分析结构（现在通过 Multi-Agent 系统）
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

        # 获取处理过程信息
        process_info = analyzer.get_last_process_info()

        # 3. 格式化文档
        formatter = DocumentFormatter()
        formatter.format_document(analysis_result)

        # 4. 保存输出文件
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"formatted_text_{unique_id}.docx"
        output_path = OUTPUT_DIR / output_filename
        formatter.save(output_path)

        # 构建处理信息
        processing_info = None
        if process_info:
            processing_info = ProcessingInfo(
                was_cleaned=process_info.get("was_cleaned", False),
                original_confidence=process_info.get("router_confidence", 0.0),
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
