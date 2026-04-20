from .Utils import main_api
from fastapi import UploadFile



async def handle(userId: str, ResumeFile: UploadFile) -> dict:
    filename = ResumeFile.filename.lower() #防止大写统一小写
    
    """ if "pdf" or "docx" or "doc" not in filename:
        return {"code": "400", "data": {
            "msg": "文件格式错误"

             return asr_result
        }} """
    # os.path.splitext 会把文件名拆成“名字”和“后缀”，比如 ("resume", ".pdf")
    _, ext = os.path.splitext(filename)
    allowed_exts = {".pdf", ".docx", ".doc", ".wav", ".mp3", ".m4a"}
    if ext not in allowed_exts:
        return {"code": 400, "data": {"msg": f"不支持的文件格式！只支持: {', '.join(allowed_exts)}"}}
        
    try:
        extracted_text = ""
        
        # 2. 调度工具人：根据不同后缀，调用 Utils 里不同的机器
        if ext in {".pdf", ".docx", ".doc"}:
            # TODO: 等你后续完善 Utils/recognize_pdf.py 来解析简历
            extracted_text = "【模拟提取】从简历文档中读取到的文字内容..." 
            
        elif ext in {".wav", ".mp3", ".m4a"}:
            # TODO: 未来调用 Utils/asr.py 进行语音转文字
            extracted_text = "【模拟听写】从录音中听到的面试回答..." 
            
        # 3. 召唤 AI 大模型
        # TODO: 这里之后调用 Utils/llm_sdk.py 里的接口，真正去问 AI。前期先写死模拟一下。
        ai_reply = f"【模拟AI回复】用户 {userId} 你好，你的简历逻辑清晰，但缺乏量化数据..."
        
        # 4. 把做好的菜（数据字典）端给前台 (Router)
        return {
            "code": 200, 
            "data": {
                "msg": "AI 分析成功", 
                "userId": userId,
                "ai_advice": ai_reply,
                "text_parsed": extracted_text
            }
        }
    except Exception as e:
        return {"code": 500, "data": {"msg": f"核心处理异常: {str(e)}"}}
    
    
   











