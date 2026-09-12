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
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

enum class AccountField { GENDER, JOB }

sealed interface ChipSaveState {
    data object Idle : ChipSaveState
    data object Loading : ChipSaveState
    data class Error(val message: String) : ChipSaveState
}

// 성별 변경 / 직업 변경 화면이 공유하는 로직: GET /users/me/account로 현재 값을 불러와 칩을
// 미리 선택해두고, "변경하기"를 누르면 PATCH /users/me/account로 자기 필드만 보낸다.
// 아직 로그인 전이라 401이 뜨는 경우도 있는데, 그때는 그냥 선택 없는 빈 상태로 둔다.
abstract class ChipSelectViewModel(private val field: AccountField) : ViewModel() {
    var selected by mutableStateOf<String?>(null)
        private set

    var saveState by mutableStateOf<ChipSaveState>(ChipSaveState.Idle)
        private set

    init {
        loadCurrentValue()
    }

    fun select(option: String) {
        selected = option
    }

    private fun loadCurrentValue() {
        viewModelScope.launch {
            try {
                val account = ApiClient.userApi.getAccount()
                selected = when (field) {
                    AccountField.GENDER -> account.gender
                    AccountField.JOB -> account.job
                }
            } catch (_: Exception) {
                // 실패해도 화면은 선택 없는 빈 상태로 그대로 둔다.
            }
        }
    }

    fun save(onSuccess: () -> Unit) {
        val current = selected ?: return
        if (saveState is ChipSaveState.Loading) return
        saveState = ChipSaveState.Loading

        viewModelScope.launch {
            try {
                val request = when (field) {
                    AccountField.GENDER -> UserAccountUpdateRequest(gender = current)
                    AccountField.JOB -> UserAccountUpdateRequest(job = current)
                }
                ApiClient.userApi.updateAccount(request)
                saveState = ChipSaveState.Idle
                onSuccess()
            } catch (e: Exception) {
                saveState = ChipSaveState.Error(describeAccountSaveError(e))
            }
        }
    }
}

class GenderViewModel : ChipSelectViewModel(AccountField.GENDER)

class JobViewModel : ChipSelectViewModel(AccountField.JOB)

private fun describeAccountSaveError(e: Exception): String = when (e) {
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
