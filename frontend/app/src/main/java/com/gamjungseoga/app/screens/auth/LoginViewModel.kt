package com.gamjungseoga.app.screens.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.LoginRequest
import com.gamjungseoga.app.network.TokenStore
import com.gamjungseoga.app.network.needsPersonalTest
import kotlinx.coroutines.launch

data class LoginDraft(
    val email: String = "",
    val password: String = ""
)

sealed interface LoginState {
    data object Idle : LoginState
    data object Loading : LoginState
    data class Error(val message: String) : LoginState
}

class LoginViewModel : ViewModel() {
    var draft by mutableStateOf(LoginDraft())
        private set
    var state by mutableStateOf<LoginState>(LoginState.Idle)
        private set

    // 회원가입 마지막 단계에서 계정은 만들어졌지만 부가 정보 저장(PATCH /users/me/account)이
    // 실패했을 때, 로그인 화면으로 돌아오면서 보여줄 안내문. sharedLoginViewModel로 같은
    // 인스턴스를 받아온 회원가입 플로우가 채워 넣는다.
    var notice by mutableStateOf<String?>(null)
        private set

    fun showNotice(message: String?) {
        notice = message
    }

    fun setEmail(text: String) {
        draft = draft.copy(email = text)
    }

    fun setPassword(text: String) {
        draft = draft.copy(password = text)
    }

    // 로그인에 성공하면 홈으로 보내기 전에 퍼스널 감정 검사를 마쳤는지 확인해서, 미완료면
    // onSuccess(needsPersonalTest = true)로 호출측(MainActivity)이 검사 화면으로 강제 진입시킬 수
    // 있게 한다.
    fun login(onSuccess: (needsPersonalTest: Boolean) -> Unit) {
        if (state is LoginState.Loading) return
        state = LoginState.Loading

        viewModelScope.launch {
            try {
                val response = ApiClient.authApi.login(
                    LoginRequest(email = draft.email.trim(), password = draft.password)
                )
                TokenStore.saveSession(response.accessToken, response.userId, response.nickname)
                state = LoginState.Idle
                onSuccess(needsPersonalTest())
            } catch (e: Exception) {
                state = LoginState.Error(describeAuthError(e))
            }
        }
    }
}
