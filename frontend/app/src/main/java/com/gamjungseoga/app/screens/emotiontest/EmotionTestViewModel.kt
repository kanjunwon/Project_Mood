package com.gamjungseoga.app.screens.emotiontest

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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

    // 강제 진입(회원가입/로그인 직후)과 설정 "다시하기" 둘 다 이 상태를 보고 전송 결과를 기다린다.
    // 두 흐름의 차이는 성공 후 어디로 이동하느냐뿐이라, 그 부분만 호출하는 쪽(MainActivity)이
    // onSuccess 콜백으로 다르게 넘긴다.
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

    // 마지막 문항에 답했을 때 호출: 전송 결과를 기다렸다가 성공했을 때만 onSuccess를 호출한다.
    // 실패하면 에러 상태로 남겨서 화면이 재시도 버튼을 보여줄 수 있게 하고, 전송 중에는
    // submitState가 Submitting이라 다시 호출해도 중복 전송되지 않는다.
    fun submit(onSuccess: () -> Unit) {
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
