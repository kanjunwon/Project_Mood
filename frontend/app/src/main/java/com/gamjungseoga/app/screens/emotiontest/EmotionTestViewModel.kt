package com.gamjungseoga.app.screens.emotiontest

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import com.gamjungseoga.app.network.AppScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.PersonalTestSubmitRequest
import kotlinx.coroutines.launch

class EmotionTestViewModel : ViewModel() {
    var currentIndex by mutableIntStateOf(0)
        private set

    val answers = mutableStateListOf<Int?>().apply {
        addAll(List(emotionTestQuestions.size) { null })
    }

    fun selectAnswer(value: Int) {
        answers[currentIndex] = value
    }

    fun goNext() {
        if (currentIndex < emotionTestQuestions.lastIndex) currentIndex++
    }

    fun goPrev() {
        if (currentIndex > 0) currentIndex--
    }

    // 마지막 문항까지 답변이 끝나면 호출: 19문항 전부 채워졌는지 확인 후 POST /personal-test 전송.
    // 화면은 응답을 기다리지 않고 바로 닫히므로(popBackStack), 화면 생명주기와 무관한
    // AppScope로 보내서 ViewModel이 소멸돼도 요청이 끝까지 전송되게 함.
    fun submitIfComplete(userId: String? = ApiClient.TEST_USER_ID) {
        val filled = answers.mapIndexedNotNull { index, value ->
            value?.let { (index + 1).toString() to it }
        }
        if (filled.size != answers.size) return

        val request = PersonalTestSubmitRequest(userId = userId, answers = filled.toMap())
        AppScope.io.launch {
            try {
                ApiClient.personalTestApi.submitPersonalTest(request)
            } catch (_: Exception) {
                // 화면이 이미 닫힌 뒤라 사용자에게 보여줄 곳이 없음 - 다음 접속 때 재시도 UX는 TODO
            }
        }
    }
}
