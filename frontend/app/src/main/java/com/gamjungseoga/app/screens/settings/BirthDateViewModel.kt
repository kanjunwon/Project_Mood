package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.UserAccountUpdateRequest
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

private val defaultBirthDate: LocalDate = LocalDate.of(2000, 1, 1)

sealed interface BirthDateSaveState {
    data object Idle : BirthDateSaveState
    data object Loading : BirthDateSaveState
    data class Error(val message: String) : BirthDateSaveState
}

// 생년월일 변경 화면 로직: GET /users/me/account로 현재 값을 불러와 휠을 맞춰두고(값이 없거나
// 실패하면 기본값 2000.01.01), "변경하기"를 누르면 PATCH /users/me/account로 birth_date만 보낸다.
class BirthDateViewModel : ViewModel() {
    var date by mutableStateOf(defaultBirthDate)
        private set

    var saveState by mutableStateOf<BirthDateSaveState>(BirthDateSaveState.Idle)
        private set

    init {
        loadCurrentValue()
    }

    // LocalDate.withYear/withMonth는 대상 월에 없는 날짜(예: 1/31 -> 2월)를 자동으로
    // 그 달의 마지막 날로 보정해준다.
    fun setYear(year: Int) {
        date = date.withYear(year)
    }

    fun setMonth(month: Int) {
        date = date.withMonth(month)
    }

    fun setDayOfMonth(day: Int) {
        date = date.withDayOfMonth(day)
    }

    private fun loadCurrentValue() {
        viewModelScope.launch {
            try {
                val raw = ApiClient.userApi.getAccount().birthDate
                if (!raw.isNullOrBlank()) {
                    date = runCatching { LocalDate.parse(raw) }.getOrDefault(defaultBirthDate)
                }
            } catch (_: Exception) {
                // 실패해도 기본값(2000.01.01)으로 그대로 둔다.
            }
        }
    }

    fun save(onSuccess: () -> Unit) {
        if (saveState is BirthDateSaveState.Loading) return
        saveState = BirthDateSaveState.Loading

        viewModelScope.launch {
            try {
                val request = UserAccountUpdateRequest(birthDate = date.format(DateTimeFormatter.ISO_LOCAL_DATE))
                ApiClient.userApi.updateAccount(request)
                saveState = BirthDateSaveState.Idle
                onSuccess()
            } catch (e: Exception) {
                saveState = BirthDateSaveState.Error(describeBirthDateSaveError(e))
            }
        }
    }
}

private fun describeBirthDateSaveError(e: Exception): String = when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is SocketTimeoutException, is TimeoutException ->
        "서버 응답이 너무 오래 걸려요 (타임아웃). 백엔드가 응답하는지 확인해주세요."
    is HttpException -> {
        val body = e.response()?.errorBody()?.string()?.take(300)
        "서버 오류 (HTTP ${e.code()})" + if (!body.isNullOrBlank()) ": $body" else ""
    }
    else -> e.message ?: "저장에 실패했어요 (${e::class.simpleName})."
}
