"""
Supabase(Postgres)에 테이블을 생성하는 1회성 스크립트.

사용법:
    python create_tables.py

주의: 이미 존재하는 테이블은 건드리지 않음 (create_all은 없는 테이블만 생성).
테이블 구조를 바꾸고 싶으면 마이그레이션 도구(Alembic) 도입을 고려할 것.
"""
from database import engine, Base
import models  # noqa: F401  (모델들을 Base.metadata에 등록하기 위해 import 필요)

if __name__ == "__main__":
    print("테이블 생성을 시작합니다...")
    Base.metadata.create_all(bind=engine)
    print("완료! Supabase Table Editor에서 확인해보세요.")
