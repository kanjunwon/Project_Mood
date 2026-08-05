-- 감정 서가 diary_entries 테이블 (감정 분석 컬럼 추가 버전)
-- 아직 테이블 안 만들었으면 이거 그대로 실행
-- 이미 만들었으면 맨 아래 ALTER 문만 따로 실행하면 됨

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

    -- 감정 분석 결과 (KoBERT 결과 저장용)
    top_emotion text,              -- 가장 강하게 느낀 감정 하나 (예: '기쁨')
    emotion_scores jsonb,          -- 감정별 점수 전체 (예: {"기쁨":0.6,"슬픔":0.1,...})
    sentiment_score float,         -- 긍정/부정 점수 (-1.0 ~ 1.0, 통계용)

    created_at timestamp with time zone default now()
);

create index idx_diary_entries_user_id on diary_entries(user_id);
create index idx_diary_entries_created_at on diary_entries(created_at);

-- ============================================
-- 이미 테이블 만들어놨으면 이 3줄만 실행하면 됨
-- ============================================
-- alter table diary_entries add column top_emotion text;
-- alter table diary_entries add column emotion_scores jsonb;
-- alter table diary_entries add column sentiment_score float;


-- users 테이블 (로그인/회원가입용)
-- 재유가 정리하기로 한 예전 users 테이블 대신 새로 만드는 버전

create table users (
    id bigint generated always as identity primary key,
    email text unique not null,
    password_hash text not null,
    nickname text,
    created_at timestamp with time zone default now()
);

create index idx_users_email on users(email);
