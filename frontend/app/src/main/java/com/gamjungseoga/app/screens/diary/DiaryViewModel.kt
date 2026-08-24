package com.gamjungseoga.app.screens.diary

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryGenerateRequest
import com.gamjungseoga.app.network.DiaryGenerateResponse
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale
import kotlinx.coroutines.launch

data class DiaryDraft(
    val date: LocalDate = LocalDate.now(),
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
    data class Error(val message: String) : DiaryGenerationState
}

class DiaryViewModel : ViewModel() {
    var draft by mutableStateOf(DiaryDraft())
        private set

    var generationState by mutableStateOf<DiaryGenerationState>(DiaryGenerationState.Idle)
        private set

    fun setDate(date: LocalDate) {
        draft = draft.copy(date = date)
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

    // DiaryWhereScreen에서 "다음으로"를 눌렀을 때 호출: 지금까지 작성한 답변들을
    // 백엔드 POST /generate-diary 로 보내서 일기 생성 + 감정분석 결과를 받아온다.
    fun submitDiary(userId: String? = ApiClient.TEST_USER_ID) {
        if (generationState is DiaryGenerationState.Loading) return
        generationState = DiaryGenerationState.Loading

        viewModelScope.launch {
            try {
                val current = draft
                val who = (current.who.toList() + listOfNotNull(current.whoCustom.trim().takeIf { it.isNotEmpty() }))
                    .ifEmpty { listOf("혼자") }

                val request = DiaryGenerateRequest(
                    what = current.what.trim(),
                    why = current.why.trim(),
                    who = who,
                    whenText = formatWhen(current.date, current.time),
                    where = current.where.trim(),
                    userId = userId
                )

                val response = ApiClient.diaryApi.generateDiary(request)
                generationState = DiaryGenerationState.Success(response)
            } catch (e: Exception) {
                generationState = DiaryGenerationState.Error(e.message ?: "일기 생성에 실패했어요.")
            }
        }
    }
}

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
