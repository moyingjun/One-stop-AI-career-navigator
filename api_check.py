import os
import httpx
import asyncio
import json
from dotenv import load_dotenv

# 1. 加载本地 .env 文件
load_dotenv()

# 2. 从环境变量读取配置
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME")

async def test_deepseek_ignition():
    print("========== 🚀 DeepSeek 引擎点火测试开始 ==========")
    print(f"📡 目标地址: {BASE_URL}")
    print(f"🤖 使用模型: {MODEL_NAME}")
    
    # 检查变量是否成功读取
    if not all([API_KEY, BASE_URL, MODEL_NAME]):
        print("❌ 错误: .env 文件读取失败，请检查变量名是否拼错！")
        return

    # 这里的 URL 处理逻辑要非常小心，中转平台有时对后缀很敏感
    # 如果你 env 里填的是 https://tokenrai.com/v1，代码里需要手动补全
    request_url = BASE_URL if BASE_URL.endswith("chat/completions") else f"{BASE_URL.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 采用“降维合并法”：把指令和测试信息合在一起，全走 user 角色
    # 这样能绕过某些中转平台对 system 角色的支持缺陷
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user", 
                "content": "这是一条点火测试消息。请回复：‘教练，DeepSeek 引擎已就绪！’"
            }
        ],
        "temperature": 0.7
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("⏳ 正在尝试建立连接...")
            response = await client.post(request_url, json=payload, headers=headers)
            
            print(f"📡 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"✅ 点火成功！大模型回复：\n{'-'*40}\n{content}\n{'-'*40}")
            else:
                print(f"❌ 点火失败！错误详情: {response.text}")
                
        except Exception as e:
            print(f"💥 发生底层网络异常: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_deepseek_ignition())