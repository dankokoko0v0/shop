from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import random, time, urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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

@app.post("/api/create_pay")
async def create_pay(request: Request):
    try:
        data = await request.json()
        order_id = f"TEST{random.randint(100000,999999)}"
        money = float(data.get("money",1.0))
        now_time = time.strftime("%Y-%m-%d %H:%M:%S")
        biz_dict = {
            "out_trade_no":order_id,
            "total_amount":f"{money:.2f}",
            "subject":"商城商品付款",
            "product_code":"FAST_INSTANT_TRADE_PAY"
        }
        biz_str = urllib.parse.quote(str(biz_dict).replace(" ","").replace("'","\""))
        # 改用支付宝在线调试专用固定参数链接（临时免签名跳转）
        base_params = {
            "app_id":"2021000000000000",
            "method":"alipay.trade.page.pay",
            "charset":"utf-8",
            "sign_type":"RSA2",
            "timestamp":now_time,
            "version":"1.0",
            "return_url":"https://dankokoko.netlify.app/pay_success.html",
            "notify_url":"https://dankokoko-shop2.onrender.com/pay_notify",
            "biz_content":biz_str
        }
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + urllib.parse.urlencode(base_params)
        logger.info("生成支付链接："+pay_url)
        return {"code":1,"payUrl":pay_url}
    except Exception as e:
        logger.error("支付异常："+str(e))
        return {"code":0,"msg":f"失败：{str(e)}"}

@app.post("/pay_notify")
def pay_notify():
    return "success"

@app.get("/")
def index():
    return {"msg":"后端正常运行"}
