import asyncio
import io


async def extract_pdf_text(file_content: bytes) -> str:
    """
    异步提取 PDF 文件中的纯文字内容
    file_content: PDF文件的字节数据
    return: 提取出来的纯文字字符串
    """
    # 创建一个异步任务，在后台线程里跑 CPU 密集型的 PDF 解析工作
    # 这样不会卡住主线程，FastAPI 还能继续处理其他请求
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _extract_pdf_sync, file_content)
    return text


def _extract_pdf_sync(file_content: bytes) -> str:
    """
    同步函数：真正负责解析 PDF 的干活人
    """
    try:
        # 先试试 PyMuPDF（也叫 fitz），速度快，效果好
        try:
            # 导入 PyMuPDF 库，用来读取 PDF
            import fitz
            # 把字节数据转成一个"内存文件"，PyMuPDF 可以直接读这个
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            # 准备一个大袋子，用来装所有页面的文字
            all_text = []
            # 挨页翻 PDF，一页一页读文字
            for page_num in range(pdf_document.page_count):
                # 拿到某一页
                page = pdf_document[page_num]
                # 把这一页的文字抽出来，存入袋子
                all_text.append(page.get_text())
            # 关上 PDF 文件（释放内存）
            pdf_document.close()
            # 把所有页的文字用换行符拼起来，返回
            return "\n".join(all_text)
        except ImportError:
            # 如果没装 PyMuPDF，走备用路线：用 pdfminer.six
            pass

        # 备用方案：pdfminer.six
        try:
            # 导入 pdfminer 的 PDF 解析器
            from pdfminer.high_level import extract_text
            # 直接调用 pdfminer 的提取函数，参数是字节流转成的文件对象
            return extract_text(io.BytesIO(file_content))
        except ImportError:
            # 两个库都没装，直接投降
            raise ImportError("请先安装 PyMuPDF 或 pdfminer.six：pip install pymupdf 或 pip install pdfminer.six")

    except Exception as e:
        # 不管啥错误（文件损坏、加密、格式不对……），都不让系统崩
        # 吞掉错误，返回一句友好的话
        return f"[警告] 无法读取此 PDF 文件，内容可能已损坏或格式不支持。错误信息：{str(e)}"
