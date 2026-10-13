package com.gamjungseoga.app.screens.diary

import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryEntry
import com.gamjungseoga.app.network.DiaryGenerateRequest
import com.gamjungseoga.app.network.DiaryGenerateResponse
import com.gamjungseoga.app.network.SEOUL_ZONE
import com.gamjungseoga.app.network.describeHttpException
import com.gamjungseoga.app.network.extractDuplicateDiaryDetail
import com.gamjungseoga.app.network.limitErrorMessageLength
import com.gamjungseoga.app.network.parseServerDateTimeInSeoul
import java.net.ConnectException
import java.net.UnknownHostException
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.HttpException

// job 생성/폴링 소요 시간을 재는 용도 (개발 중에만 확인).
private const val DIARY_GEN_TIMING_TAG = "DiaryGenTiming"

// getDiaryJob을 3초 간격으로 폴링하고, 최대 6분까지 기다린다. 작업 자체는 1~2초짜리 요청이라
// 이 간격/상한은 서버 응답 지연이 아니라 "일기+그림 생성"이 끝날 때까지 기다리는 시간이다.
private const val POLL_INTERVAL_MILLIS = 3_000L
private const val MAX_POLL_MILLIS = 6 * 60 * 1_000L

// 폴링 중 네트워크 오류가 한두 번 나는 것은 흔하니, 연속으로 이 횟수만큼 실패할 때만 포기한다.
private const val MAX_CONSECUTIVE_POLL_FAILURES = 3

data class DiaryDraft(
    // 기기 시간대가 아니라 서버 기준(서울)으로 기본 날짜를 잡아야 한다. 기기 시간대가 서울보다
    // 앞서 있으면(예: 호주) LocalDate.now()가 서울 기준 "오늘"보다 하루 앞선 날짜를 내놓을 수
    // 있는데, 이 값이 DiaryDateScreen의 initialDate로 쓰여 그대로 제출되면 서버가 미래 날짜로
    // 거부해야 할 요청이 생긴다(캘린더 클릭 자체는 이미 SEOUL_ZONE 기준으로 막혀 있음).
    val date: LocalDate = LocalDate.now(SEOUL_ZONE),
    val what: String = "",
    val why: String = "",
    val who: Set<String> = emptySet(),
    val whoCustom: String = "",
    val time: LocalTime = LocalTime.now(),
    val where: String = ""
)

sealed interface DiaryGenerationState {
    data object Idle : DiaryGenerationState
    data object Loading : DiaryGenerationState
    data class Success(val response: DiaryGenerateResponse) : DiaryGenerationState

    // jobId가 있으면 그 job이 아직 살아있을 수 있다는 뜻이라 재시도 시 새 job을 만들지 않고
    // 그 job을 이어서 폴링한다(폴링 타임아웃/연속 네트워크 실패처럼 최종 결과를 모르는 경우).
    // jobId가 null이면 재시도해도 안전하게 새 job을 만들 수 있다는 뜻이다(job 생성 자체가
    // 실패했거나, job이 이미 확정적으로 끝났다는 걸 확인한 경우 - 서버 쪽에 저장된 게 없으므로
    // 중복이 생기지 않는다).
    data class Error(val message: String, val jobId: String?, val canRetry: Boolean) : DiaryGenerationState

    // 같은 날짜에 이미 일기가 있어서(하루 1개 제한) 생성이 거부된 경우. existingDiaryId를 모르면
    // (job 폴링 중 경쟁 상태로 감지된 경우 등) null일 수 있는데, 그때는 화면에서 "보러가기" 버튼을
    // 숨긴다.
    data class DuplicateExists(val existingDiaryId: Long?, val message: String) : DiaryGenerationState
}

// 일기 상세 화면의 "다시 작성하기"는 아직 존재하지 않는 DiaryViewModel 인스턴스(일기작성 그래프에
// 진입하기 전)에 "이 날짜로, 날짜 선택은 건너뛰고 들어가라"는 의도를 전달해야 해서, 그래프 진입
// 시점에 한 번만 소비되는 전역 요청함에 담아 넘긴다.
object DiaryRewriteRequest {
    private var pendingDate: LocalDate? = null

    fun request(date: LocalDate) {
        pendingDate = date
    }

    fun consume(): LocalDate? {
        val date = pendingDate
        pendingDate = null
        return date
    }
}

class DiaryViewModel : ViewModel() {
    var draft by mutableStateOf(DiaryDraft())
        private set

    // true면 "다시 작성하기" 플로우: 생성 요청에 overwrite=true를 담아 보낸다.
    var overwrite by mutableStateOf(false)
        private set

    var generationState by mutableStateOf<DiaryGenerationState>(DiaryGenerationState.Idle)
        private set

    fun setDate(date: LocalDate) {
        draft = draft.copy(date = date)
    }

    // 일기 상세 화면의 "다시 작성하기 확인"으로 진입한 경우 호출. 날짜를 그 일기의 날짜로
    // 고정하고(날짜 선택 단계는 건너뜀) 나머지 답변은 새로 입력받는다.
    fun startOverwrite(date: LocalDate) {
        draft = DiaryDraft(date = date)
        overwrite = true
    }

    fun setWhat(text: String) {
        draft = draft.copy(what = text)
    }

    fun setWhy(text: String) {
        draft = draft.copy(why = text)
    }

    fun toggleWho(option: String) {
        draft = draft.copy(who = if (option in draft.who) draft.who - option else draft.who + option)
    }

    fun setWhoCustom(text: String) {
        draft = draft.copy(whoCustom = text)
    }

    fun setTime(time: LocalTime) {
        draft = draft.copy(time = time)
    }

    fun setWhere(text: String) {
        draft = draft.copy(where = text)
    }

    // DiaryWhereScreen에서 "다음으로"를 눌렀을 때 호출: job을 새로 만들고 폴링을 시작한다.
    fun submitDiary() {
        if (generationState is DiaryGenerationState.Loading) return
        generationState = DiaryGenerationState.Loading
        val request = buildRequest(draft, overwrite)

        viewModelScope.launch {
            val startMillis = System.currentTimeMillis()
            generationState = createJobAndPoll(request)
            logElapsed(startMillis)
        }
    }

    // DiaryGeneratingScreen의 "다시 시도하기"에서 호출. 중복 생성을 막기 위해, 직전 Error 상태의
    // jobId가 남아있으면(=job이 이미 만들어졌고 결과를 아직 모름) 새 job을 만들지 않고 그 job을
    // 이어서 폴링한다. jobId가 없으면(=job 생성 자체가 실패했거나 확정적으로 끝남을 확인함) 새
    // job을 만든다.
    fun retryGeneration() {
        if (generationState is DiaryGenerationState.Loading) return
        val errorState = generationState as? DiaryGenerationState.Error ?: return
        if (!errorState.canRetry) return

        generationState = DiaryGenerationState.Loading
        val request = buildRequest(draft, overwrite)
        val existingJobId = errorState.jobId

        viewModelScope.launch {
            val startMillis = System.currentTimeMillis()
            generationState = if (existingJobId != null) {
                pollJob(existingJobId, request)
            } else {
                createJobAndPoll(request)
            }
            logElapsed(startMillis)
        }
    }

    private suspend fun createJobAndPoll(request: DiaryGenerateRequest): DiaryGenerationState {
        val jobId = try {
            ApiClient.diaryApi.createDiaryJob(request).jobId
        } catch (e: HttpException) {
            // 하루 1개 제한: overwrite 없이 이미 일기가 있는 날짜로 요청하면 409 + 구조화된
            // detail({"code": "DIARY_ALREADY_EXISTS", ...})을 준다.
            if (e.code() == 409) {
                val rawBody = runCatching { e.response()?.errorBody()?.string() }.getOrNull()
                val duplicate = extractDuplicateDiaryDetail(rawBody)
                if (duplicate != null) {
                    return DiaryGenerationState.DuplicateExists(duplicate.existingDiaryId, duplicate.message)
                }
            }
            return DiaryGenerationState.Error(describeError(e), jobId = null, canRetry = true)
        } catch (e: Exception) {
            return DiaryGenerationState.Error(describeError(e), jobId = null, canRetry = true)
        }
        return pollJob(jobId, request)
    }

    private suspend fun pollJob(jobId: String, request: DiaryGenerateRequest): DiaryGenerationState {
        val deadlineMillis = System.currentTimeMillis() + MAX_POLL_MILLIS
        var consecutiveFailures = 0

        while (System.currentTimeMillis() < deadlineMillis) {
            delay(POLL_INTERVAL_MILLIS)
            try {
                val status = ApiClient.diaryApi.getDiaryJob(jobId)
                consecutiveFailures = 0
                when (status.status) {
                    "done" -> {
                        val result = status.result
                        return if (result != null) {
                            DiaryGenerationState.Success(result)
                        } else {
                            DiaryGenerationState.Error(
                                "일기 생성 결과를 받지 못했어요. 다시 시도해주세요.",
                                jobId = null,
                                canRetry = true
                            )
                        }
                    }
                    "error" -> {
                        // 같은 날짜로 동시에 두 job이 대기 중이었던 경쟁 상태(하루 1개 제한 위반).
                        // 이 응답에는 existing_diary_id가 없으니, 방금 보낸 날짜로 저장된 일기를
                        // 목록에서 찾아 "보러가기" 대상으로 쓴다(없으면 버튼 없이 안내만 보여줌).
                        if (status.errorCode == "DIARY_ALREADY_EXISTS") {
                            return DiaryGenerationState.DuplicateExists(
                                existingDiaryId = findDiaryIdForDate(request.date),
                                message = status.error?.let { limitErrorMessageLength(it) }
                                    ?: "이 날짜에는 이미 일기가 있어요."
                            )
                        }
                        return DiaryGenerationState.Error(
                            status.error?.let { limitErrorMessageLength(it) } ?: "일기 생성에 실패했어요.",
                            jobId = null,
                            canRetry = true
                        )
                    }
                    else -> Unit // processing - 계속 폴링
                }
            } catch (e: HttpException) {
                if (e.code() == 404) {
                    // job이 만료됐거나 서버가 재시작된 경우. 이미 생성+저장이 끝났을 수 있으니
                    // 최신 일기 목록에서 지금 작성 중인 내용과 일치하는 일기가 있는지 확인한다.
                    val matched = findMatchingDiary(request)
                    return if (matched != null) {
                        DiaryGenerationState.Success(diaryGenerateResponseFrom(matched))
                    } else {
                        DiaryGenerationState.Error(
                            "일기 생성 작업을 찾을 수 없어요. 다시 시도해주세요.",
                            jobId = null,
                            canRetry = true
                        )
                    }
                }
                consecutiveFailures++
                if (consecutiveFailures >= MAX_CONSECUTIVE_POLL_FAILURES) {
                    return DiaryGenerationState.Error(describeError(e), jobId = jobId, canRetry = true)
                }
            } catch (e: Exception) {
                consecutiveFailures++
                if (consecutiveFailures >= MAX_CONSECUTIVE_POLL_FAILURES) {
                    return DiaryGenerationState.Error(describeError(e), jobId = jobId, canRetry = true)
                }
            }
        }

        return DiaryGenerationState.Error(
            "일기 생성이 너무 오래 걸리고 있어요. 다시 시도해주세요.",
            jobId = jobId,
            canRetry = true
        )
    }

    // getDiaryJob이 404를 준 뒤, 방금 보낸 요청과 같은 내용의 일기가 이미 저장돼 있는지 확인.
    // 같은 내용으로 두 번 작성하는 극히 드문 경우를 제외하면 충분히 안전한 매칭이다.
    private suspend fun findMatchingDiary(request: DiaryGenerateRequest): DiaryEntry? {
        val diaries = runCatching { ApiClient.diaryApi.getDiaries().diaries }.getOrNull() ?: return null
        return diaries
            .sortedByDescending { it.createdAt ?: "" }
            .firstOrNull { entry ->
                entry.what == request.what &&
                    entry.why == request.why &&
                    entry.who == request.who &&
                    entry.where == request.where
            }
    }

    // 같은 날짜 일기 중복 감지 시(job 폴링 경쟁 상태) existing_diary_id가 안 내려오므로, 그 날짜에
    // 해당하는 일기를 목록에서 직접 찾는다. dateStr은 "YYYY-MM-DD"(ISO_LOCAL_DATE).
    private suspend fun findDiaryIdForDate(dateStr: String): Long? {
        val diaries = runCatching { ApiClient.diaryApi.getDiaries().diaries }.getOrNull() ?: return null
        return diaries.firstOrNull { entry ->
            parseServerDateTimeInSeoul(entry.createdAt)?.toLocalDate()?.toString() == dateStr
        }?.id
    }

    private fun logElapsed(startMillis: Long) {
        val elapsedMillis = System.currentTimeMillis() - startMillis
        Log.d(DIARY_GEN_TIMING_TAG, "일기 생성 완료까지: ${elapsedMillis}ms (${elapsedMillis / 1000.0}s)")
    }
}

private fun diaryGenerateResponseFrom(entry: DiaryEntry): DiaryGenerateResponse = DiaryGenerateResponse(
    status = "success",
    generatedDiary = entry.generatedDiary.orEmpty(),
    validationFailed = entry.validationFailed,
    topEmotion = entry.topEmotion,
    emotionScores = entry.emotionScores,
    sentimentScore = entry.sentimentScore,
    imageUrl = entry.imageUrl,
    id = entry.id
)

private val isoDateFormatter = DateTimeFormatter.ISO_LOCAL_DATE

private fun buildRequest(draft: DiaryDraft, overwrite: Boolean): DiaryGenerateRequest {
    val who = (draft.who.toList() + listOfNotNull(draft.whoCustom.trim().takeIf { it.isNotEmpty() }))
        .ifEmpty { listOf("혼자") }
        .joinToString(",")

    return DiaryGenerateRequest(
        what = draft.what.trim(),
        why = draft.why.trim(),
        who = who,
        whenText = formatWhen(draft.date, draft.time),
        where = draft.where.trim(),
        date = draft.date.format(isoDateFormatter),
        overwrite = overwrite
    )
}

// 개발 중 백엔드 연결 문제를 바로 알아볼 수 있게, 흔한 네트워크 예외를 원인이 드러나는 문구로 바꿔준다.
private fun describeError(e: Exception): String = limitErrorMessageLength(when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is java.net.SocketTimeoutException, is TimeoutException ->
        "그림을 그리는 데 시간이 오래 걸리고 있어요. 다시 시도해주세요."
    is HttpException -> {
        if (e.code() == 504 || e.code() == 524) {
            // 504/524: 이미지 생성이 오래 걸려 중간에 연결이 끊긴 경우
            "그림을 그리는 데 시간이 오래 걸리고 있어요. 다시 시도해주세요."
        } else {
            describeHttpException(e)
        }
    }
    else -> e.message ?: "일기 생성에 실패했어요 (${e::class.simpleName})."
})

private val whenDateFormatter = DateTimeFormatter.ofPattern("M월 d일")

// 백엔드 "when" 필드는 자유 형식 텍스트라, 날짜+시간을 사람이 읽는 문장으로 합쳐서 보낸다.
// 예: "8월 24일 월요일 오후 2시 30분"
private fun formatWhen(date: LocalDate, time: LocalTime): String {
    val dayOfWeek = date.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.KOREAN)
    val isAm = time.hour < 12
    val hour12 = when (val h = time.hour % 12) { 0 -> 12; else -> h }
    val ampm = if (isAm) "오전" else "오후"
    val minutePart = if (time.minute == 0) "" else " ${time.minute}분"
    return "${date.format(whenDateFormatter)} ${dayOfWeek} ${ampm} ${hour12}시${minutePart}"
}
