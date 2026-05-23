import os
import httpx
import asyncio
import json
from dotenv import load_dotenv
import traceback

# 1. 加载 .env 文件
load_dotenv()

# 2. 读取配置
# MIMO_API_KEY = os.getenv("MIMO_API_KEY", "sk-IWh97R23GRUwLzeQEjuXoozkf7nKAsjAXDPaHKfZnP8AtQiv")
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "sk-IWh97R23GRUwLzeQEjuXoozkf7nKAsjAXDPaHKfZnP8AtQiv")
BASE_URL = os.getenv("MIMO_BASE_URL", "https://tokenrai.com/v1")
MODEL_NAME = os.getenv("MIMO_MODEL_NAME", "deepseek-v4-flash")

async def test_mimo_api():
    print("========== 🚀 Mimo 引擎点火测试开始 ==========")
    print(f"📡 目标地址: {BASE_URL}")
    print(f"🤖 使用模型: {MODEL_NAME}")

    # 检查变量是否正确
    if not all([MIMO_API_KEY, BASE_URL, MODEL_NAME]):
        print("❌ .env 配置缺失或拼写错误")
        return

    request_url = BASE_URL.rstrip("/") + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {MIMO_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "这是一条点火测试消息，请回复：‘教练，Mimo 引擎已就绪！’"}
        ],
        "temperature": 0.7,
        "stream": False,  # 改为 True 可支持流式 SSE
        "max_tokens": 500
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("⏳ 正在尝试建立连接...")
            response = await client.post(request_url, json=payload, headers=headers)
            
            print(f"📡 响应状态码: {response.status_code}")
            try:
                result = response.json()
            except json.JSONDecodeError:
                print(f"❌ 无法解析响应 JSON: {response.text}")
                return

            print(f"📄 完整返回内容:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

            if response.status_code == 200:
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"].get("content")
                    print(f"✅ 点火成功！Mimo 模型回复：\n{'-'*40}\n{content}\n{'-'*40}")
                else:
                    print(f"⚠️ 响应中未找到 choices: {result}")
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")

        except httpx.RequestError as re:
            print(f"💥 请求错误: {str(re)}")
            traceback.print_exc()
        except Exception as e:
            print(f"💥 未知异常: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mimo_api())