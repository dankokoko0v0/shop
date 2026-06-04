from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --------------------------
# 数据库配置（SQLite，零安装）
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

# 订单表
class DBOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    customer_phone = Column(String)
    customer_address = Column(String)
    total_price = Column(Float)
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

    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: str
    items: list[Product]

# --------------------------
# FastAPI应用
# --------------------------
app = FastAPI(title="我的网店")

# 解决跨域问题（关键！）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线后改成你的Netlify域名，例如："https://my-shop.netlify.app"
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

# --------------------------
# 商品接口
# --------------------------
@app.get("/api/products", response_model=list[Product])
def get_all_products():
    db = next(get_db())
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

# --------------------------
# 订单接口
# --------------------------
@app.post("/api/orders")
def create_order(order: OrderCreate):
    db = next(get_db())
    
    # 计算总价
    total_price = sum(item.price for item in order.items)
    
    # 创建订单
    db_order = DBOrder(
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_address=order.customer_address,
        total_price=total_price
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return {"success": True, "order_id": db_order.id, "total_price": total_price}

# --------------------------
# 运行服务器
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)