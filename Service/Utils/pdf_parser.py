"""
Service/Utils/pdf_parser.py — PDF 文本提取工具

从 Service/Utils/recognize_pdf.py 迁移而来，保持原有逻辑不变。
优先使用 PyMuPDF（fitz），降级使用 pdfminer.six。
"""

import asyncio
import io


async def extract_pdf_text(file_content: bytes) -> str:
    """
    异步提取 PDF 文件中的纯文字内容。

    在后台线程中执行 CPU 密集型解析，不阻塞 FastAPI 事件循环。

    参数：
        file_content — PDF 文件的字节数据

    返回：
        提取出的纯文字字符串；解析失败时返回友好错误提示
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_pdf_sync, file_content)


def _extract_pdf_sync(file_content: bytes) -> str:
    """同步 PDF 解析实现，供 run_in_executor 调用。"""
    try:
        # 优先使用 PyMuPDF（速度快，效果好）
        try:
            import fitz

            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            pages = [pdf_document[i].get_text() for i in range(pdf_document.page_count)]
            pdf_document.close()
            return "\n".join(pages)
        except ImportError:
            pass

        # 降级使用 pdfminer.six
        try:
            from pdfminer.high_level import extract_text

            return extract_text(io.BytesIO(file_content))
        except ImportError:
            raise ImportError(
                "请先安装 PyMuPDF 或 pdfminer.six：\n"
                "  pip install pymupdf\n"
                "  pip install pdfminer.six"
            )

    except Exception as exc:
        return f"[警告] 无法读取此 PDF 文件，内容可能已损坏或格式不支持。错误信息：{str(exc)}"
