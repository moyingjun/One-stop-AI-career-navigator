from fastapi import FastAPI, Request, Response, File
from dotenv import load_dotenv
#添加CORS库
from fastapi.middleware.cors import CORSMiddleware 
from Router import jobResume, resumeDiagnosis

# 加载 .env 环境变量
load_dotenv()

app = FastAPI(title="一站式AI职业生涯导航员")
#分端口使前端才能成功向后端发送请求，浏览器默认会拦截它们通信，报全线飘红的 CORS 错误
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #星号代表允许所有人访问
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

#补充把路由挂给前端接口
app.include_router(jobResume.router)
app.include_router(resumeDiagnosis.router)









