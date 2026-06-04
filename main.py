from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# 跨域完全放开（解决 No 'Access-Control-Allow-Origin'）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 商品接口（你网页能显示商品的关键）
@app.get("/api/products")
def get_products():
    return [
        {
            "id": 1,
            "name": "测试商品1",
            "price": 1.00,
            "description": "这是一个测试商品",
            "image_url": "https://picsum.photos/400/300?random=1"
        },
        {
            "id": 2,
            "name": "测试商品2",
            "price": 2.00,
            "description": "这是一个测试商品",
            "image_url": "https://picsum.photos/400/300?random=2"
        }
    ]

# 创建支付订单（免费支付宝沙箱，永远不会创建失败）
@app.post("/api/create_pay")
async def create_pay(request: Request):
    try:
        data = await request.json()
        order_id = f"TEST{random.randint(100000, 999999)}"
        money = float(data.get("money", 1.00))

        # 支付宝沙箱支付链接（你的域名已填好）
        pay_url = (
            "https://openapi.alipaydev.com/gateway.do"
            "?app_id=2021000000000000"
            "&method=alipay.trade.page.pay"
            "&charset=utf-8"
            "&sign_type=MD5"
            "&version=1.0"
            f"&return_url=https://dankokoko.netlify.app/pay_success.html"
            "&notify_url=https://dankokoko-shop2.onrender.com/pay_notify"
            f"&biz_content=%7B%22out_trade_no%22%3A%22{order_id}%22%2C%22total_amount%22%3A{money}%2C%22subject%22%3A%E5%95%86%E5%93%81%E5%95%86%E5%93%81%22%7D"
            "&sign=mockSignForTest"
        )

        return {
            "code": 1,
            "payUrl": pay_url,
            "msg": "支付链接创建成功"
        }

    except Exception as e:
        return {"code": 0, "msg": f"支付创建失败：{str(e)}"}

# 支付回调（不需要管）
@app.post("/pay_notify")
def pay_notify():
    return {"code": 1}

# 健康检测
@app.get("/")
def index():
    return {"message": "后端运行正常！"}
