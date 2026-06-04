from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import hashlib
import requests
import os

# --------------------------
# 配置区（修改这里的参数）
# --------------------------
# 管理员账号密码（部署时改成你自己的）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "your_secure_password_123"

# 虎皮椒支付配置（个人可申请，https://www.xunhupay.com/）
XUNHU_PAY_MCHID = "你的商户ID"
XUNHU_PAY_KEY = "你的商户密钥"
# 支付成功后跳转的页面
PAY_RETURN_URL = "https://dankokoko.netlify.app/pay_success.html"
# 支付回调通知地址（Render后端地址+/api/pay/notify）
PAY_NOTIFY_URL = "https://dankokoko-shop2.onrender.com/api/pay/notify"

# --------------------------
# 数据库配置
# --------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 商品表
class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(String)
    image_url = Column(String)
    stock = Column(Integer, default=999)  # 新增：库存

# 订单表（升级）
class DBOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String, unique=True, index=True)  # 新增：商户订单号
    customer_name = Column(String)
    customer_phone = Column(String)
    customer_address = Column(String)
    total_price = Column(Float)
    status = Column(Integer, default=0)  # 0:待支付 1:已支付 2:已发货 3:已完成
    pay_time = Column(DateTime, nullable=True)
    ship_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# --------------------------
# 数据模型
# --------------------------
class Product(BaseModel):
    id: int | None = None
    name: str
    price: float
    description: str
    image_url: str
    stock: int = 999

    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: str
    items: list[Product]

class OrderUpdate(BaseModel):
    status: int

# --------------------------
# FastAPI应用
# --------------------------
app = FastAPI(title="我的网店")
security = HTTPBasic()

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dankokoko.netlify.app/"],  # 上线后改成你的Netlify域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 管理员验证
def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# 生成唯一订单号
def generate_order_no():
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(os.urandom(2).hex())

# --------------------------
# 商品接口（升级为完整CRUD）
# --------------------------
@app.get("/api/products", response_model=list[Product])
def get_all_products(db=Depends(get_db)):
    products = db.query(DBProduct).all()
    
    # 如果数据库为空，自动添加示例商品
    if not products:
        sample_products = [
            DBProduct(name="示例商品1", price=99.9, description="这是第一个示例商品", image_url="https://picsum.photos/400/300?random=1"),
            DBProduct(name="示例商品2", price=199.9, description="这是第二个示例商品", image_url="https://picsum.photos/400/300?random=2"),
            DBProduct(name="示例商品3", price=299.9, description="这是第三个示例商品", image_url="https://picsum.photos/400/300?random=3"),
        ]
        db.add_all(sample_products)
        db.commit()
        products = db.query(DBProduct).all()
    
    return products

# 后台：添加商品
@app.post("/api/admin/products", response_model=Product)
def create_product(product: Product, db=Depends(get_db), admin=Depends(get_current_admin)):
    db_product = DBProduct(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# 后台：更新商品
@app.put("/api/admin/products/{product_id}", response_model=Product)
def update_product(product_id: int, product: Product, db=Depends(get_db), admin=Depends(get_current_admin)):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    for key, value in product.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

# 后台：删除商品
@app.delete("/api/admin/products/{product_id}")
def delete_product(product_id: int, db=Depends(get_db), admin=Depends(get_current_admin)):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    db.delete(db_product)
    db.commit()
    return {"success": True}

# --------------------------
# 订单接口（升级）
# --------------------------
@app.post("/api/orders")
def create_order(order: OrderCreate, db=Depends(get_db)):
    # 计算总价
    total_price = sum(item.price for item in order.items)
    
    # 生成订单号
    order_no = generate_order_no()
    
    # 创建订单
    db_order = DBOrder(
        order_no=order_no,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_address=order.customer_address,
        total_price=total_price
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return {"success": True, "order_id": db_order.id, "order_no": order_no, "total_price": total_price}

# 后台：获取所有订单
@app.get("/api/admin/orders")
def get_all_orders(db=Depends(get_db), admin=Depends(get_current_admin)):
    orders = db.query(DBOrder).order_by(DBOrder.created_at.desc()).all()
    return orders

# 后台：更新订单状态
@app.put("/api/admin/orders/{order_id}")
def update_order(order_id: int, order_update: OrderUpdate, db=Depends(get_db), admin=Depends(get_current_admin)):
    db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    db_order.status = order_update.status
    if order_update.status == 1:
        db_order.pay_time = datetime.utcnow()
    elif order_update.status == 2:
        db_order.ship_time = datetime.utcnow()
    
    db.commit()
    return {"success": True}

# --------------------------
# 支付接口（虎皮椒支付）
# --------------------------
@app.post("/api/pay/create")
def create_payment(order_no: str, db=Depends(get_db)):
    db_order = db.query(DBOrder).filter(DBOrder.order_no == order_no).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if db_order.status != 0:
        raise HTTPException(status_code=400, detail="订单状态错误")
    
    # 构造支付参数
    params = {
        "mch_id": XUNHU_PAY_MCHID,
        "out_trade_no": order_no,
        "total_fee": int(db_order.total_price * 100),  # 单位：分
        "body": f"订单-{order_no}",
        "notify_url": PAY_NOTIFY_URL,
        "return_url": PAY_RETURN_URL,
        "nonce_str": os.urandom(8).hex(),
        "time": int(datetime.now().timestamp())
    }
    
    # 生成签名
    sign_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())]) + f"&key={XUNHU_PAY_KEY}"
    params["sign"] = hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    # 请求支付接口
    response = requests.post("https://api.xunhupay.com/pay/unifiedorder", json=params)
    result = response.json()
    
    if result["return_code"] == "SUCCESS" and result["result_code"] == "SUCCESS":
        return {"success": True, "pay_url": result["code_url"]}
    else:
        raise HTTPException(status_code=400, detail=result.get("return_msg", "支付创建失败"))

# 支付回调通知
@app.post("/api/pay/notify")
def pay_notify(data: dict):
    # 验证签名
    sign = data.pop("sign")
    sign_str = "&".join([f"{k}={v}" for k, v in sorted(data.items())]) + f"&key={XUNHU_PAY_KEY}"
    if hashlib.md5(sign_str.encode()).hexdigest().upper() != sign:
        raise HTTPException(status_code=400, detail="签名错误")
    
    # 更新订单状态
    db = next(get_db())
    order_no = data["out_trade_no"]
    db_order = db.query(DBOrder).filter(DBOrder.order_no == order_no).first()
    
    if db_order and data["return_code"] == "SUCCESS":
        db_order.status = 1
        db_order.pay_time = datetime.utcnow()
        db.commit()
    
    return "success"

# --------------------------
# 运行服务器
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
