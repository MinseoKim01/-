from fastapi import FastAPI, Depends, Request, HTTPException, status
from sqlalchemy.orm import declarative_base, Session, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = "mysql+pymysql://root:rlaalstj011026@localhost:3306/mydb"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 실제 데이터베이스 테이블 구조를 정의
# User Model : user 테이블을 "정의"
class User(Base):
    __tablename__= "users3"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    password = Column(Integer)

# Post Model : post 테이블을 "정의"
class Post(Base):
    __tablename__ = "posts2"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    content = Column(String(500))
    author_id = Column(Integer, ForeignKey("users3.id")) # 작성자 아이디 추가 (외래키 설정)
    author = relationship("User")

# 정의한 테이블 "생성"
Base.metadata.create_all(bind=engine)

# Pydantic - 요청과 응답에서 사용하는 데이터 구조를 정의
class UserLogin(BaseModel):
    username: str
    password: int

# 클라이언트 -> 서버로 작성 데이터를 보낼 때 사용
# post id, username은 제외 (사용자가 직접 지정하면 안되는 값이므로)
class PostCreate(BaseModel):
    title: str
    content: str
    author_id: int

# 서버 ->  클라이언트로 돌려줄 때 사용 (서버가 만들어서 전달하는 데이터)
class PostOut(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author_username: str

    class Config:
        from_attributes = True

def get_db():
    db = Session(bind= engine)
    try:
        yield db
    finally:
        db.close()

# ==========get==========
# 기본 라우터 구현 (로그인용 HTML 페이지)
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 회원가입용 HTML 페이지
@app.get("/signup-page")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# 게시판용 HTML 페이지
@app.get("/posts-page")
async def posts_page(request: Request):
    return templates.TemplateResponse("posts.html", {"request": request})

# ==========post - 경로는 페이지 이동 용도가 아니라, 회원가입 처리 api로만 만들어져 있음
# 회원가입
@app.post("/signup/")
async def signup(user: UserLogin, db: Session = Depends(get_db)):
    # 중복 사용자 확인
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다.")
    
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "회원가입 완료", "user_id": db_user.username}

# 로그인
@app.post("/login/")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        User.username == user.username,
        User.password == user.password
    ).first()
    if db_user:
        return {"message": "Login successful", "user": db_user.username, "user_id": db_user.id}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

# 게시글 작성
@app.post("/posts/", response_model=PostOut)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(title=post.title, content=post.content, author_id=post.author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    # 작성자 이름을 DB에서 가져오기
    author_name = db.query(User.username).filter(User.id == db_post.author_id).scalar()
    return PostOut(
        id=db_post.id,
        title=db_post.title,
        content=db_post.content,
        author_id=db_post.author_id,
        author_username=author_name
    )

# 게시글 전체 조회
@app.get("/posts/", response_model=List[PostOut])
def read_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    result = []
    for post in posts:
        author_name = db.query(User.username).filter(User.id == post.author_id).scalar()
        result.append(PostOut(
            id=post.id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_username=author_name
        ))
    return result

# 게시글 단건 조회
@app.get("/posts/{post_id}", response_model=PostOut)
def read_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    author_name = db.query(User.username).filter(User.id == post.author_id).scalar()
    return PostOut(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_username=author_name
    )

# 내 게시물 조회
@app.get("/myPosts/{user_id}", response_model=List[PostOut])
def read_myposts(user_id: int, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.author_id == user_id).all()
    result = [ ]
    for post in posts :
        author_name = db.query(User.username).filter(User.id == post.author_id).scalar()
        result.append(PostOut(
            id=post.id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_username=author_name
        ))
    return result