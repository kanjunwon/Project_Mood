package com.gamjungseoga.app.screens.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.SignupRequest
import com.gamjungseoga.app.network.TokenStore
import com.gamjungseoga.app.network.UserAccountUpdateRequest
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import kotlinx.coroutines.launch

private val defaultSignupBirthDate: LocalDate = LocalDate.of(2000, 1, 1)

data class SignupDraft(
    val email: String = "",
    val password: String = "",
    val passwordConfirm: String = "",
    val nickname: String = "",
    val gender: String? = null,
    val job: String? = null,
    val birthDate: LocalDate = defaultSignupBirthDate
)

sealed interface SignupSubmitState {
    data object Idle : SignupSubmitState
    data object Loading : SignupSubmitState
    data class Error(val message: String) : SignupSubmitState
}

// 회원가입 6단계(이메일/비밀번호/닉네임/성별/직업/생년월일)가 공유하는 ViewModel. 입력값만
// 모아두고, 마지막 생년월일 단계에서 버튼을 눌렀을 때만 POST /signup -> PATCH /users/me/account
// 순서로 호출한다.
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

    fun setGender(value: String) {
        draft = draft.copy(gender = value)
    }

    fun setJob(value: String) {
        draft = draft.copy(job = value)
    }

    fun setBirthYear(year: Int) {
        draft = draft.copy(birthDate = draft.birthDate.withYear(year))
    }

    fun setBirthMonth(month: Int) {
        draft = draft.copy(birthDate = draft.birthDate.withMonth(month))
    }

    fun setBirthDay(day: Int) {
        draft = draft.copy(birthDate = draft.birthDate.withDayOfMonth(day))
    }

    // 1) POST /signup으로 계정을 만들고 받은 토큰을 저장한 뒤, 2) 그 토큰으로
    // PATCH /users/me/account에 성별/직업/생년월일을 보낸다. 1)이 실패하면 계정 자체가 없으니
    // 에러를 보여주고 멈추고, 2)가 실패하면 계정은 이미 만들어진 뒤라 되돌릴 수 없어
    // onPartialFailure로 안내만 하고 그대로 진행(로그인 화면 복귀)한다.
    fun submitSignup(onSuccess: () -> Unit, onPartialFailure: () -> Unit) {
        if (submitState is SignupSubmitState.Loading) return
        submitState = SignupSubmitState.Loading

        viewModelScope.launch {
            val current = draft
            val authResponse = try {
                ApiClient.authApi.signup(
                    SignupRequest(
                        email = current.email.trim(),
                        password = current.password,
                        nickname = current.nickname.trim().ifBlank { null }
                    )
                )
            } catch (e: Exception) {
                submitState = SignupSubmitState.Error(describeAuthError(e))
                return@launch
            }

            TokenStore.saveSession(authResponse.accessToken, authResponse.userId, authResponse.nickname)

            try {
                ApiClient.userApi.updateAccount(
                    UserAccountUpdateRequest(
                        gender = current.gender,
                        job = current.job,
                        birthDate = current.birthDate.format(DateTimeFormatter.ISO_LOCAL_DATE)
                    )
                )
                submitState = SignupSubmitState.Idle
                onSuccess()
            } catch (_: Exception) {
                submitState = SignupSubmitState.Idle
                onPartialFailure()
            }
        }
    }
}
