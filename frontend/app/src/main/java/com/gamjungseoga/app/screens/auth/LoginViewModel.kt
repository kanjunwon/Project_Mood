package com.gamjungseoga.app.screens.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.LoginRequest
import com.gamjungseoga.app.network.TokenStore
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

    fun setEmail(text: String) {
        draft = draft.copy(email = text)
    }

    fun setPassword(text: String) {
        draft = draft.copy(password = text)
    }

    fun login(onSuccess: () -> Unit) {
        if (state is LoginState.Loading) return
        state = LoginState.Loading

        viewModelScope.launch {
            try {
                val response = ApiClient.authApi.login(
                    LoginRequest(email = draft.email.trim(), password = draft.password)
                )
                TokenStore.saveSession(response.accessToken, response.userId, response.nickname)
                state = LoginState.Idle
                onSuccess()
            } catch (e: Exception) {
                state = LoginState.Error(describeAuthError(e))
            }
        }
    }
}
