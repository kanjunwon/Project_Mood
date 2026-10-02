package com.gamjungseoga.app.screens.profilecustomize

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.UserProfileRequest
import com.gamjungseoga.app.network.describeHttpException
import com.gamjungseoga.app.network.limitErrorMessageLength
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class ProfileCustomizeDraft(
    val glasses: String? = null, // "horn_rimmed" | "round" | "none"
    val bangs: Boolean? = null,
    val hairLength: String? = null, // "long" | "short"
    val hairColor: String? = null // "black" | "brown"
)

sealed interface ProfileCustomizeSaveState {
    data object Idle : ProfileCustomizeSaveState
    data object Loading : ProfileCustomizeSaveState
    data class Error(val message: String) : ProfileCustomizeSaveState
}

// 이미지 커스터마이징 4단계(안경/앞머리/머리길이/머리색)가 공유하는 로직: GET /users/me/profile로
// 저장된 값을 불러와 각 단계에 미리 선택해두고, 마지막 단계에서 PATCH /users/me/profile로 네 값을
// 한 번에 보낸다. 아직 로그인 전이거나 서버가 없어 요청이 실패해도 선택 없는 빈 상태로 둔다.
class ProfileCustomizeViewModel : ViewModel() {
    var draft by mutableStateOf(ProfileCustomizeDraft())
        private set

    var saveState by mutableStateOf<ProfileCustomizeSaveState>(ProfileCustomizeSaveState.Idle)
        private set

    init {
        loadCurrentValue()
    }

    fun setGlasses(value: String) {
        draft = draft.copy(glasses = value)
    }

    fun setBangs(value: Boolean) {
        draft = draft.copy(bangs = value)
    }

    fun setHairLength(value: String) {
        draft = draft.copy(hairLength = value)
    }

    fun setHairColor(value: String) {
        draft = draft.copy(hairColor = value)
    }

    private fun loadCurrentValue() {
        viewModelScope.launch {
            try {
                val profile = ApiClient.userApi.getProfile()
                draft = ProfileCustomizeDraft(
                    glasses = profile.glasses,
                    bangs = profile.bangs,
                    hairLength = profile.hairLength,
                    hairColor = profile.hairColor
                )
            } catch (_: Exception) {
                // 실패해도 화면은 선택 없는 빈 상태로 그대로 둔다.
            }
        }
    }

    fun save(onSuccess: () -> Unit) {
        if (saveState is ProfileCustomizeSaveState.Loading) return
        saveState = ProfileCustomizeSaveState.Loading

        viewModelScope.launch {
            try {
                val current = draft
                val request = UserProfileRequest(
                    glasses = current.glasses,
                    bangs = current.bangs,
                    hairLength = current.hairLength,
                    hairColor = current.hairColor
                )
                ApiClient.userApi.updateProfile(request)
                saveState = ProfileCustomizeSaveState.Idle
                onSuccess()
            } catch (e: Exception) {
                saveState = ProfileCustomizeSaveState.Error(describeProfileSaveError(e))
            }
        }
    }
}

private fun describeProfileSaveError(e: Exception): String = limitErrorMessageLength(when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is SocketTimeoutException, is TimeoutException ->
        "서버 응답이 너무 오래 걸려요 (타임아웃). 백엔드가 응답하는지 확인해주세요."
    is HttpException -> describeHttpException(e)
    else -> e.message ?: "저장에 실패했어요 (${e::class.simpleName})."
})
