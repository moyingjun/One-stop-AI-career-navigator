import aiohttp
import os
import dotenv
import aiofiles
import asyncio
from typing import list

dotenv.load_dotenv()

asr_api_key = os.getenv("asr_api_key")
asr_api_url = os.getenv("asr_api_url")


async def asr_api(audio_bytes: bytes) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url = asr_api_url,
            data = {"audio": audio_bytes},
            headers = {"Authorization": f"Bearer {asr_api_key}"},
        ) as resp:
            return await resp.json()
    
async def read_files(audio_path: str) -> bytes:
    async with aiofiles.open(audio_path, "rb") as f:
        return await f.read()


async def main_api(audio_path: str) -> dict:
    audio_bytes = await read_files(audio_path)
    asr_result = await asr_api(audio_bytes)
    return asr_result


if __name__ == "__main__":
    pass
