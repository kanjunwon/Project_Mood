package com.gamjungseoga.app.network

import android.util.Log
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset

private const val TAG = "ServerDateTime"

// DiaryEntry.createdAt(Supabase timestamptz)을 파싱하는 곳이 HomeScreen/ArchiveScreen/
// DiaryDateScreen 등 여러 화면에 흩어져 있었고, 각자 OffsetDateTime.parse 실패를 조용히
// null로 삼켜서(mapNotNull/getOrNull) 일기가 누락되거나 엉뚱한 달로 묶여도 알아챌 방법이
// 없었다. 여기로 모으고, 표준 ISO 8601("2026-09-28T19:10:00+09:00")이 아닌 변형(날짜/시간
// 구분자가 공백인 Postgres 기본 표현, 오프셋이 빠진 경우)도 방어적으로 한 번씩 더 시도한
// 뒤, 그래도 실패하면 Log.w로 원본 문자열을 남긴다.
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
