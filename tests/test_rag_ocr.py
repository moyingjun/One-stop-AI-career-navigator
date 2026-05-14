"""
rag_service OCR 直接调用单元测试

验证 _extract_text_from_image() 直接调用 recognize_image_text() SDK，
不发起任何 HTTP 请求，且正确处理成功/失败场景。

**Property 5: 后端 OCR 无 HTTP 自调用**
**Property 6: OCR 失败正确抛出异常**
**Validates: Requirements 6.1, 6.2, 6.3**
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# 确保项目根目录在 sys.path 中，以便正确导入 Service 模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import HTTPException
from Service.rag_service import _extract_text_from_image

# Mock 路径：因为 _extract_text_from_image 内部使用 local import，
# 需要 patch 源模块 Service.Utils.ocr_sdk.recognize_image_text
MOCK_OCR_PATH = "Service.Utils.ocr_sdk.recognize_image_text"


# ============================================================
# Unit Tests: 具体场景验证
# ============================================================


class TestExtractTextFromImageSuccess:
    """验证正常图片返回 OCR 文本。"""

    @patch(MOCK_OCR_PATH)
    def test_valid_image_returns_text(self, mock_ocr):
        """正常图片 bytes → 返回 OCR 识别文本。"""
        mock_ocr.return_value = "这是一段识别出的文本"
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # 模拟图片 bytes

        result = _extract_text_from_image(content)

        assert result == "这是一段识别出的文本"
        mock_ocr.assert_called_once()
        # 验证传入的参数是 base64 格式带前缀
        call_arg = mock_ocr.call_args[0][0]
        assert call_arg.startswith("data:image/png;base64,")

    @patch(MOCK_OCR_PATH)
    def test_returns_multiline_text(self, mock_ocr):
        """OCR 返回多行文本时正常传递。"""
        mock_ocr.return_value = "第一行\n第二行\n第三行"
        content = b"\xff\xd8\xff\xe0" + b"\x00" * 50  # 模拟 JPEG bytes

        result = _extract_text_from_image(content)

        assert result == "第一行\n第二行\n第三行"


class TestExtractTextFromImageFailure:
    """验证 OCR 失败时正确抛出 HTTPException(400)。"""

    @patch(MOCK_OCR_PATH)
    def test_empty_result_raises_400(self, mock_ocr):
        """OCR 返回空字符串 → 抛出 HTTPException(400)。"""
        mock_ocr.return_value = ""
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with pytest.raises(HTTPException) as exc_info:
            _extract_text_from_image(content)

        assert exc_info.value.status_code == 400
        assert "OCR 识别失败" in exc_info.value.detail

    @patch(MOCK_OCR_PATH)
    def test_none_result_raises_400(self, mock_ocr):
        """OCR 返回 None → 抛出 HTTPException(400)。"""
        mock_ocr.return_value = None
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with pytest.raises(HTTPException) as exc_info:
            _extract_text_from_image(content)

        assert exc_info.value.status_code == 400

    @patch(MOCK_OCR_PATH)
    def test_parse_failure_message_raises_400(self, mock_ocr):
        """OCR 返回包含"图片解析失败"的字符串 → 抛出 HTTPException(400)。"""
        mock_ocr.return_value = "图片解析失败，请确保图片清晰或重试。"
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with pytest.raises(HTTPException) as exc_info:
            _extract_text_from_image(content)

        assert exc_info.value.status_code == 400
        assert "OCR 识别失败" in exc_info.value.detail


class TestNoHTTPRequests:
    """验证 _extract_text_from_image 不发起任何 HTTP 请求。

    **Property 5: 后端 OCR 无 HTTP 自调用**
    **Validates: Requirements 6.1, 6.2**
    """

    @patch(MOCK_OCR_PATH)
    def test_no_httpx_calls(self, mock_ocr):
        """验证不使用 httpx 发起 HTTP 请求。"""
        mock_ocr.return_value = "识别文本"
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with patch("httpx.post") as mock_httpx_post, \
             patch("httpx.get") as mock_httpx_get, \
             patch("httpx.AsyncClient") as mock_async_client:
            _extract_text_from_image(content)

            mock_httpx_post.assert_not_called()
            mock_httpx_get.assert_not_called()
            mock_async_client.assert_not_called()

    @patch(MOCK_OCR_PATH)
    def test_no_requests_calls(self, mock_ocr):
        """验证不使用 requests 库发起 HTTP 请求。"""
        mock_ocr.return_value = "识别文本"
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        with patch("requests.post", create=True) as mock_req_post, \
             patch("requests.get", create=True) as mock_req_get:
            _extract_text_from_image(content)

            mock_req_post.assert_not_called()
            mock_req_get.assert_not_called()


# ============================================================
# Property-Based Tests: 通用属性验证
# ============================================================


class TestPropertyNoHTTPSelfCall:
    """Property 5: 后端 OCR 无 HTTP 自调用

    对任意图片 bytes，_extract_text_from_image() 不发起 HTTP 请求。

    **Validates: Requirements 6.1, 6.2**
    """

    @given(content=st.binary(min_size=1, max_size=1024))
    @settings(max_examples=50)
    def test_no_http_for_any_input(self, content):
        """对任意 bytes 输入，函数不发起 HTTP 请求到本机。"""
        with patch(MOCK_OCR_PATH, return_value="模拟OCR结果") as mock_ocr, \
             patch("httpx.post") as mock_httpx_post, \
             patch("httpx.get") as mock_httpx_get:
            _extract_text_from_image(content)

            mock_httpx_post.assert_not_called()
            mock_httpx_get.assert_not_called()


class TestPropertyOCRFailureRaisesException:
    """Property 6: OCR 失败正确抛出异常

    对任意 OCR 返回空字符串或包含"图片解析失败"的结果，
    _extract_text_from_image() 抛出 HTTPException(400)。

    **Validates: Requirements 6.3**
    """

    @given(content=st.binary(min_size=1, max_size=1024))
    @settings(max_examples=50)
    def test_empty_result_always_raises_400(self, content):
        """对任意 bytes 输入，当 OCR 返回空字符串时抛出 400。"""
        with patch(MOCK_OCR_PATH, return_value=""):
            with pytest.raises(HTTPException) as exc_info:
                _extract_text_from_image(content)

            assert exc_info.value.status_code == 400

    @given(
        content=st.binary(min_size=1, max_size=1024),
        prefix=st.text(min_size=0, max_size=20),
        suffix=st.text(min_size=0, max_size=20),
    )
    @settings(max_examples=50)
    def test_failure_message_always_raises_400(self, content, prefix, suffix):
        """对任意包含"图片解析失败"子串的 OCR 结果，抛出 400。"""
        with patch(MOCK_OCR_PATH, return_value=f"{prefix}图片解析失败{suffix}"):
            with pytest.raises(HTTPException) as exc_info:
                _extract_text_from_image(content)

            assert exc_info.value.status_code == 400

    @given(content=st.binary(min_size=1, max_size=1024))
    @settings(max_examples=50)
    def test_none_result_always_raises_400(self, content):
        """对任意 bytes 输入，当 OCR 返回 None 时抛出 400。"""
        with patch(MOCK_OCR_PATH, return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                _extract_text_from_image(content)

            assert exc_info.value.status_code == 400
