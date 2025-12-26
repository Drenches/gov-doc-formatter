"""
API路由模块
"""
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from app.core.document_parser import DocumentParser
from app.core.llm_analyzer import LLMAnalyzer
from app.core.formatter import DocumentFormatter
from app.models.schemas import FormatResponse, HealthResponse, AnalysisResponse

router = APIRouter()


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

        # 2. 使用LLM分析结构
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

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

        return FormatResponse(
            success=True,
            message="文档格式化成功",
            output_filename=output_filename,
            download_url=f"/api/download/{output_filename}"
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

        # 2. 使用LLM分析结构
        analyzer = LLMAnalyzer()
        analysis_result = analyzer.analyze(doc_text)

        if not analysis_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"文档分析失败: {analysis_result.error_message}"
            )

        # 3. 格式化文档
        formatter = DocumentFormatter()
        formatter.format_document(analysis_result)

        # 4. 保存输出文件
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"formatted_text_{unique_id}.docx"
        output_path = OUTPUT_DIR / output_filename
        formatter.save(output_path)

        return FormatResponse(
            success=True,
            message="文档格式化成功",
            output_filename=output_filename,
            download_url=f"/api/download/{output_filename}"
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
