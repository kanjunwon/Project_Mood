package com.gamjungseoga.app.screens.diary

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryEntry
import kotlinx.coroutines.launch

sealed interface DiaryListState {
    data object Loading : DiaryListState
    data class Loaded(val diaries: List<DiaryEntry>) : DiaryListState
    data class Error(val message: String) : DiaryListState
}

// 홈("최근 작성한 페이지")과 아카이브("나의 감정 서재") 둘 다 같은 GET /diaries/{user_id}
// 목록을 쓰므로, 화면마다 이 ViewModel을 하나씩 인스턴스화해서 재사용.
class DiaryListViewModel : ViewModel() {
    var state by mutableStateOf<DiaryListState>(DiaryListState.Loading)
        private set

    init {
        load()
    }

    fun load(userId: String = ApiClient.TEST_USER_ID) {
        state = DiaryListState.Loading
        viewModelScope.launch {
            state = try {
                val response = ApiClient.diaryApi.getDiaries(userId)
                // created_at 최신순 정렬 (문자열이 ISO 8601이라 문자열 비교로도 시간순 정렬됨)
                DiaryListState.Loaded(response.diaries.sortedByDescending { it.createdAt ?: "" })
            } catch (e: Exception) {
                DiaryListState.Error(e.message ?: "일기 목록을 불러오지 못했어요.")
            }
        }
    }
}
