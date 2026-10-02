package com.gamjungseoga.app.network

import android.util.Log
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.ZonedDateTime

private const val TAG = "ServerDateTime"

// 서버(Supabase)는 created_at을 UTC로 저장/반환하지만, 이 앱은 한국 사용자만 대상이라 화면에
// 보여주는 날짜는 항상 한국 시간(KST) 기준이어야 한다. 기기의 시스템 시간대를 쓰면 사용자가
// 해외에서 폰 시간대를 다르게 맞춰놨을 때 일기 날짜가 또 달라지는 문제가 생길 수 있어, 시스템
// 기본 시간대 대신 Asia/Seoul로 명시적으로 고정한다. "이번 달/오늘"처럼 현재 시각 기준으로
// 계산하는 쪽도 이 시간대를 같이 써야 서버 데이터와 기준이 어긋나지 않아서 공개해둔다.
val SEOUL_ZONE: ZoneId = ZoneId.of("Asia/Seoul")

// DiaryEntry.createdAt(Supabase timestamptz)을 파싱하는 곳이 HomeScreen/ArchiveScreen/
// DiaryDateScreen 등 여러 화면에 흩어져 있었고, 각자 OffsetDateTime.parse 실패를 조용히
// null로 삼켜서(mapNotNull/getOrNull) 일기가 누락되거나 엉뚱한 달로 묶여도 알아챌 방법이
// 없었다. 여기로 모으고, 표준 ISO 8601("2026-09-28T19:10:00+09:00")이 아닌 변형(날짜/시간
// 구분자가 공백인 Postgres 기본 표현, 오프셋이 빠진 경우)도 방어적으로 한 번씩 더 시도한
// 뒤, 그래도 실패하면 Log.w로 원본 문자열을 남긴다.
//
// 반환값은 원본에 담긴 오프셋(대개 UTC) 그대로다 - 화면에 날짜/시간을 표시하거나 월별로
// 묶으려면 이 결과를 그대로 쓰지 말고 parseServerDateTimeInSeoul을 사용해야 한다.
fun parseServerDateTime(raw: String?): OffsetDateTime? {
    if (raw.isNullOrBlank()) return null

    runCatching { OffsetDateTime.parse(raw) }.getOrNull()?.let { return it }

    // "2026-09-28 19:10:00+09:00"처럼 'T' 대신 공백으로 구분된 경우
    val withT = raw.replaceFirst(' ', 'T')
    if (withT != raw) {
        runCatching { OffsetDateTime.parse(withT) }.getOrNull()?.let { return it }
    }

    // 오프셋이 아예 없는 경우("2026-09-28T19:10:00") UTC로 가정
    runCatching { LocalDateTime.parse(withT).atOffset(ZoneOffset.UTC) }.getOrNull()?.let { return it }

    Log.w(TAG, "서버 날짜 파싱 실패: \"$raw\"")
    return null
}

// parseServerDateTime의 결과를 한국 시간대로 변환한다. 화면에 날짜/시간을 보여주거나(아카이브
// 카드, 홈 최근 페이지), 날짜 단위로 묶을 때(홈 월별 집계, 아카이브 월별 그룹핑, 날짜 선택
// 캘린더 썸네일) 전부 이 함수를 써야 "한국 시간 기준 자정 전후" 일기가 엉뚱한 날짜/달로
// 보이지 않는다.
fun parseServerDateTimeInSeoul(raw: String?): ZonedDateTime? =
    parseServerDateTime(raw)?.atZoneSameInstant(SEOUL_ZONE)
