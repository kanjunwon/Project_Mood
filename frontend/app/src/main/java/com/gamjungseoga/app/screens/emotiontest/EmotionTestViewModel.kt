package com.gamjungseoga.app.screens.emotiontest

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.AppScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.PersonalTestSubmitRequest
import com.gamjungseoga.app.network.describeHttpException
import com.gamjungseoga.app.network.limitErrorMessageLength
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

sealed interface EmotionTestSubmitState {
    data object Idle : EmotionTestSubmitState
    data object Submitting : EmotionTestSubmitState
    data class Error(val message: String) : EmotionTestSubmitState
}

class EmotionTestViewModel : ViewModel() {
    var currentIndex by mutableIntStateOf(0)
        private set

    val answers = mutableStateListOf<Int?>().apply {
        addAll(List(emotionTestQuestions.size) { null })
    }

    // 강제 진입(회원가입/로그인 직후) 흐름에서만 쓰는 제출 상태. 설정의 "다시하기"는 지금처럼
    // fire-and-forget이라 이 상태를 보지 않는다.
    var submitState by mutableStateOf<EmotionTestSubmitState>(EmotionTestSubmitState.Idle)
        private set

    fun selectAnswer(value: Int) {
        answers[currentIndex] = value
    }

    fun goNext() {
        if (currentIndex < emotionTestQuestions.lastIndex) currentIndex++
    }

    fun goPrev() {
        if (currentIndex > 0) currentIndex--
    }

    private fun buildRequest(): PersonalTestSubmitRequest? {
        val filled = answers.mapIndexedNotNull { index, value ->
            value?.let { (index + 1).toString() to it }
        }
        if (filled.size != answers.size) return null
        return PersonalTestSubmitRequest(answers = filled.toMap())
    }

    // 설정 화면 "다시하기"로 들어온 경우: 화면은 응답을 기다리지 않고 바로 닫히므로(popBackStack),
    // 화면 생명주기와 무관한 AppScope로 보내서 ViewModel이 소멸돼도 요청이 끝까지 전송되게 함.
    fun submitIfComplete() {
        val request = buildRequest() ?: return
        AppScope.io.launch {
            try {
                ApiClient.personalTestApi.submitPersonalTest(request)
            } catch (_: Exception) {
                // 화면이 이미 닫힌 뒤라 사용자에게 보여줄 곳이 없음 - 다음 접속 때 재시도 UX는 TODO
            }
        }
    }

    // 강제 진입 흐름: 전송에 실패하면 사용자가 검사를 또 해야 하는 상황이 생기므로, 결과를
    // 기다렸다가 성공했을 때만 onSuccess를 호출한다. 실패하면 에러 상태로 남겨서 화면이
    // 재시도 버튼을 보여줄 수 있게 한다.
    fun submitForced(onSuccess: () -> Unit) {
        val request = buildRequest() ?: return
        if (submitState is EmotionTestSubmitState.Submitting) return
        submitState = EmotionTestSubmitState.Submitting

        viewModelScope.launch {
            try {
                ApiClient.personalTestApi.submitPersonalTest(request)
                submitState = EmotionTestSubmitState.Idle
                onSuccess()
            } catch (e: Exception) {
                submitState = EmotionTestSubmitState.Error(describeSubmitError(e))
            }
        }
    }
}

private fun describeSubmitError(e: Exception): String = limitErrorMessageLength(when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is SocketTimeoutException, is TimeoutException ->
        "서버 응답이 너무 오래 걸려요 (타임아웃). 백엔드가 응답하는지 확인해주세요."
    is HttpException -> describeHttpException(e)
    else -> e.message ?: "검사 결과 전송에 실패했어요 (${e::class.simpleName})."
})
