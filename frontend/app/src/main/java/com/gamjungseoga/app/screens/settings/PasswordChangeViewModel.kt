package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.describeUnexpectedError
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.UpdatePasswordRequest
import com.gamjungseoga.app.network.describeConnectionFailure
import com.gamjungseoga.app.network.describeHttpException
import com.gamjungseoga.app.network.describeTimeout
import com.gamjungseoga.app.network.extractDetailMessage
import com.gamjungseoga.app.network.limitErrorMessageLength
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class PasswordChangeDraft(
    val currentPassword: String = "",
    val newPassword: String = "",
    val newPasswordConfirm: String = ""
)

sealed interface PasswordChangeSaveState {
    data object Idle : PasswordChangeSaveState
    data object Loading : PasswordChangeSaveState
    data class Error(val message: String) : PasswordChangeSaveState
}

// 비밀번호 변경 화면 로직: PATCH /users/me/password에 current_password/new_password를 보낸다.
// 현재 비밀번호가 틀리면 서버가 401 + detail("현재 비밀번호가 일치하지 않습니다")로 응답하는데,
// ApiClient.authInterceptor가 이 엔드포인트의 401은 로그아웃 신호로 취급하지 않도록 예외
// 처리되어 있으니, 여기서는 그냥 에러 메시지로 화면에 보여주기만 하면 된다.
class PasswordChangeViewModel : ViewModel() {
    var draft by mutableStateOf(PasswordChangeDraft())
        private set

    var saveState by mutableStateOf<PasswordChangeSaveState>(PasswordChangeSaveState.Idle)
        private set

    fun setCurrentPassword(text: String) {
        draft = draft.copy(currentPassword = text)
    }

    fun setNewPassword(text: String) {
        draft = draft.copy(newPassword = text)
    }

    fun setNewPasswordConfirm(text: String) {
        draft = draft.copy(newPasswordConfirm = text)
    }

    fun save(onSuccess: () -> Unit) {
        if (saveState is PasswordChangeSaveState.Loading) return
        saveState = PasswordChangeSaveState.Loading

        viewModelScope.launch {
            try {
                val request = UpdatePasswordRequest(
                    currentPassword = draft.currentPassword,
                    newPassword = draft.newPassword
                )
                ApiClient.userApi.updatePassword(request)
                saveState = PasswordChangeSaveState.Idle
                onSuccess()
            } catch (e: Exception) {
                saveState = PasswordChangeSaveState.Error(describePasswordChangeError(e))
            }
        }
    }
}

private fun describePasswordChangeError(e: Exception): String = limitErrorMessageLength(when (e) {
    is UnknownHostException, is ConnectException -> describeConnectionFailure(e)
    is SocketTimeoutException, is TimeoutException -> describeTimeout(e)
    is HttpException -> {
        if (e.code() == 401) {
            val rawBody = runCatching { e.response()?.errorBody()?.string() }.getOrNull()
            extractDetailMessage(rawBody) ?: "현재 비밀번호가 일치하지 않아요."
        } else {
            describeHttpException(e)
        }
    }
    else -> describeUnexpectedError(e, "저장에 실패했어요. 잠시 후 다시 시도해주세요.")
})
