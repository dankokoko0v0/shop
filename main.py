from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/products")
def get_products():
    return [
        {"id":1,"name":"测试商品1","price":1.00,"description":"测试","image_url":"https://picsum.photos/400/300?random=1"},
        {"id":2,"name":"测试商品2","price":2.00,"description":"测试","image_url":"https://picsum.photos/400/300?random=2"}
    ]

# 新增订单接口，解决404
@app.get("/api/orders")
def get_orders():
    return []

@app.post("/api/create_pay")
async def create_pay(request: Request):
    return {
        "code": 1,
        "payUrl": "https://dankokoko.netlify.app/pay_success.html"
    }

@app.post("/pay_notify")
def pay_notify():
    return "success"

@app.get("/")
def home():
    return {"status":"ok"}
