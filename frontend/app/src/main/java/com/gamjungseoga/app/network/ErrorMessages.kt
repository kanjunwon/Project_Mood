package com.gamjungseoga.app.network

import com.google.gson.JsonParser
import retrofit2.HttpException

// HttpException 응답 본문을 화면 메시지로 쓰기 전에 공통으로 다듬는 곳.
// RunPod 프록시가 서버 기동 중일 때 502/503/504와 함께 HTML 에러 페이지를 그대로 내려주는 경우가 있어서,
// 그 본문을 그대로 노출하면 사용자에게 HTML 소스가 보이는 문제가 생긴다.

private const val MAX_RAW_TEXT_LENGTH = 200
private const val MAX_ERROR_MESSAGE_LINES = 3

private val htmlBodyPrefixes = listOf("<!doctype", "<html")

// 본문이 HTML 페이지이거나 너무 길면(둘 다 사용자에게 보여주기 부적절) null을 돌려준다.
private fun sanitizeRawBody(rawBody: String?): String? {
    val trimmed = rawBody?.trim().orEmpty()
    if (trimmed.isEmpty()) return null
    val looksLikeHtml = htmlBodyPrefixes.any { trimmed.startsWith(it, ignoreCase = true) }
    if (looksLikeHtml || trimmed.length > MAX_RAW_TEXT_LENGTH) return null
    return trimmed
}

// FastAPI가 HTTPException(detail=...)로 내려주는 형태에서 메시지만 뽑아낸다. detail은 보통
// 문자열({"detail": "..."})이지만, 하루 1개 제한 409 응답처럼 구조화된 객체
// ({"detail": {"code": ..., "message": ..., ...}})로 올 때도 있어 둘 다 처리한다.
fun extractDetailMessage(rawBody: String?): String? {
    val body = sanitizeRawBody(rawBody) ?: return null
    return runCatching {
        val detail = JsonParser.parseString(body).asJsonObject.get("detail") ?: return@runCatching null
        when {
            detail.isJsonPrimitive -> detail.asString
            detail.isJsonObject -> detail.asJsonObject.get("message")?.takeIf { it.isJsonPrimitive }?.asString
            else -> null
        }
    }.getOrNull()?.takeIf { it.isNotBlank() }
}

// 하루 1개 제한 때문에 생성 요청이 409로 거부된 경우의 상세 정보.
// {"detail": {"code": "DIARY_ALREADY_EXISTS", "message": "...", "date": "...", "existing_diary_id": 123}}
data class DuplicateDiaryDetail(
    val message: String,
    val date: String?,
    val existingDiaryId: Long?
)

// extractDetailMessage와 달리, detail이 DIARY_ALREADY_EXISTS 코드를 가진 객체일 때만 구조화된
// 필드(existing_diary_id 등)까지 뽑아낸다. 그 외 형태/코드면 null.
fun extractDuplicateDiaryDetail(rawBody: String?): DuplicateDiaryDetail? {
    val body = sanitizeRawBody(rawBody) ?: return null
    return runCatching {
        val detail = JsonParser.parseString(body).asJsonObject.get("detail") ?: return@runCatching null
        if (!detail.isJsonObject) return@runCatching null
        val detailObject = detail.asJsonObject
        val code = detailObject.get("code")?.takeIf { it.isJsonPrimitive }?.asString
        if (code != "DIARY_ALREADY_EXISTS") return@runCatching null
        DuplicateDiaryDetail(
            message = detailObject.get("message")?.takeIf { it.isJsonPrimitive }?.asString
                ?: "이 날짜에는 이미 일기가 있어요.",
            date = detailObject.get("date")?.takeIf { it.isJsonPrimitive }?.asString,
            existingDiaryId = detailObject.get("existing_diary_id")?.takeIf { it.isJsonPrimitive }?.asLong
        )
    }.getOrNull()
}

private fun statusCodeFallbackMessage(code: Int): String = when (code) {
    502, 503, 504 -> "서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요."
    else -> "서버 오류가 발생했어요 (HTTP $code). 잠시 후 다시 시도해주세요."
}

// HttpException을 화면에 보여줄 한 줄짜리 문구로 바꾼다. detail 필드가 있으면 그걸 쓰고,
// 없으면 본문을 정리해서 쓰되, 본문이 HTML이거나 너무 길면 상태 코드 기반 안내 문구로 대체한다.
fun describeHttpException(e: HttpException): String {
    val code = e.code()
    val rawBody = runCatching { e.response()?.errorBody()?.string() }.getOrNull()
    val usableBody = extractDetailMessage(rawBody) ?: sanitizeRawBody(rawBody)
    return if (usableBody != null) {
        "서버 오류 (HTTP $code): $usableBody"
    } else {
        statusCodeFallbackMessage(code)
    }
}

// 화면에 표시되는 에러 메시지는 출처(서버 본문, 예외 메시지 등)에 상관없이 항상 이 함수를 거쳐서
// 2~3줄을 넘지 않도록 길이를 제한한다.
fun limitErrorMessageLength(message: String): String {
    val limitedLines = message.lineSequence().take(MAX_ERROR_MESSAGE_LINES).joinToString("\n")
    return if (limitedLines.length > MAX_RAW_TEXT_LENGTH) {
        limitedLines.take(MAX_RAW_TEXT_LENGTH - 1).trimEnd() + "…"
    } else {
        limitedLines
    }
}
