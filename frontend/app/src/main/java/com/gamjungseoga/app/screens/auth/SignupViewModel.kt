package com.gamjungseoga.app.screens.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.SignupRequest
import com.gamjungseoga.app.network.TokenStore
import kotlinx.coroutines.launch

data class SignupDraft(
    val email: String = "",
    val password: String = "",
    val passwordConfirm: String = "",
    val nickname: String = ""
)

sealed interface SignupSubmitState {
    data object Idle : SignupSubmitState
    data object Loading : SignupSubmitState
    data class Error(val message: String) : SignupSubmitState
}

// 회원가입 3단계(이메일/비밀번호/닉네임)가 공유하는 ViewModel. 입력값만 모아두고,
// 마지막 닉네임 단계에서 "완료하고 로그인 화면으로 돌아가기"를 눌렀을 때만 POST /signup을 호출한다.
class SignupViewModel : ViewModel() {
    var draft by mutableStateOf(SignupDraft())
        private set

    var submitState by mutableStateOf<SignupSubmitState>(SignupSubmitState.Idle)
        private set

    fun setEmail(text: String) {
        draft = draft.copy(email = text)
    }

    fun setPassword(text: String) {
        draft = draft.copy(password = text)
    }

    fun setPasswordConfirm(text: String) {
        draft = draft.copy(passwordConfirm = text)
    }

    fun setNickname(text: String) {
        draft = draft.copy(nickname = text)
    }

    fun submitSignup(onSuccess: () -> Unit) {
        if (submitState is SignupSubmitState.Loading) return
        submitState = SignupSubmitState.Loading

        viewModelScope.launch {
            try {
                val current = draft
                val request = SignupRequest(
                    email = current.email.trim(),
                    password = current.password,
                    nickname = current.nickname.trim().ifBlank { null }
                )
                val response = ApiClient.authApi.signup(request)
                TokenStore.saveSession(response.accessToken, response.userId, response.nickname)
                submitState = SignupSubmitState.Idle
                onSuccess()
            } catch (e: Exception) {
                submitState = SignupSubmitState.Error(describeAuthError(e))
            }
        }
    }
}
