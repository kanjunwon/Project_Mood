-- 감정 서가 diary_entries 테이블
-- Supabase 대시보드 -> SQL Editor에서 이 쿼리 그대로 실행하면 됨

create table diary_entries (
    id bigint generated always as identity primary key,
    user_id text,
    what text not null,
    why text,
    who text,
    when_ text,
    where_ text,
    generated_diary text,
    validation_failed boolean default false,
    created_at timestamp with time zone default now()
);

-- user_id로 자주 조회할 거라 인덱스 걸어둠
create index idx_diary_entries_user_id on diary_entries(user_id);

-- (참고) 백엔드 repository 코드가 지금 이 컬럼명 그대로 쓰고 있음
-- user_id, what, why, who, when_, where_, generated_diary
-- 컬럼명 바꾸고 싶으면 backend 쪽 diary_repository.py도 같이 맞춰서 고쳐야 함