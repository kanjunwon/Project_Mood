package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.TokenStore
import com.gamjungseoga.app.network.UserAccountResponse
import com.gamjungseoga.app.network.UserStatsResponse
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

sealed interface AccountState {
    data object Loading : AccountState
    data class Loaded(val account: UserAccountResponse) : AccountState
    data class Error(val message: String) : AccountState
}

sealed interface StatsState {
    data object Loading : StatsState
    data class Loaded(val stats: UserStatsResponse) : StatsState
    data class Error(val message: String) : StatsState
}

sealed interface DeleteAccountState {
    data object Idle : DeleteAccountState
    data object Loading : DeleteAccountState
    data class Error(val message: String) : DeleteAccountState
}

// 설정 화면의 "계정 설정" 값(이메일/성별/직업/생년월일)과 통계 카드(Days/Emotion) 값을
// 각각 GET /users/me/account, GET /users/me/stats에서 받아온다. 아직 로그인 화면이 앱 시작
// 흐름에 안 붙어있어 토큰이 없는 상태로 호출되면 401이 뜨는데, 그 경우도 Error 상태로만
// 남기고 화면은 빈 값/0으로 정상 표시되게 한다.
class SettingsViewModel : ViewModel() {
    var accountState by mutableStateOf<AccountState>(AccountState.Loading)
        private set

    var statsState by mutableStateOf<StatsState>(StatsState.Loading)
        private set

    var deleteAccountState by mutableStateOf<DeleteAccountState>(DeleteAccountState.Idle)
        private set

    init {
        loadAccount()
        loadStats()
    }

    fun loadAccount() {
        accountState = AccountState.Loading
        viewModelScope.launch {
            accountState = try {
                AccountState.Loaded(ApiClient.userApi.getAccount())
            } catch (e: Exception) {
                AccountState.Error(e.message ?: "계정 정보를 불러오지 못했어요.")
            }
        }
    }

    fun loadStats() {
        statsState = StatsState.Loading
        viewModelScope.launch {
            statsState = try {
                StatsState.Loaded(ApiClient.userApi.getStats())
            } catch (e: Exception) {
                StatsState.Error(e.message ?: "통계를 불러오지 못했어요.")
            }
        }
    }

    // 서버에 별도 로그아웃 API가 없어서, 기기에 저장된 토큰만 지우면 끝.
    fun logout() {
        TokenStore.clearSession()
    }

    fun deleteAccount(onSuccess: () -> Unit) {
        if (deleteAccountState is DeleteAccountState.Loading) return
        deleteAccountState = DeleteAccountState.Loading

        viewModelScope.launch {
            try {
                ApiClient.userApi.deleteAccount()
                TokenStore.clearSession()
                deleteAccountState = DeleteAccountState.Idle
                onSuccess()
            } catch (e: Exception) {
                deleteAccountState = DeleteAccountState.Error(describeDeleteAccountError(e))
            }
        }
    }
}

private fun describeDeleteAccountError(e: Exception): String = when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is SocketTimeoutException, is TimeoutException ->
        "서버 응답이 너무 오래 걸려요 (타임아웃). 백엔드가 응답하는지 확인해주세요."
    is HttpException -> {
        val body = e.response()?.errorBody()?.string()?.take(300)
        "서버 오류 (HTTP ${e.code()})" + if (!body.isNullOrBlank()) ": $body" else ""
    }
    else -> e.message ?: "계정 탈퇴에 실패했어요 (${e::class.simpleName})."
}
