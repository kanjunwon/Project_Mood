package com.gamjungseoga.app.screens.settings

import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gamjungseoga.app.network.describeUnexpectedError
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.UserAccountUpdateRequest
import com.gamjungseoga.app.network.describeConnectionFailure
import com.gamjungseoga.app.network.describeHttpException
import com.gamjungseoga.app.network.describeTimeout
import com.gamjungseoga.app.network.limitErrorMessageLength
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeoutException
import kotlinx.coroutines.launch
import retrofit2.HttpException

private const val TAG = "BirthDateViewModel"

private val defaultBirthDate: LocalDate = LocalDate.of(2000, 1, 1)

sealed interface BirthDateSaveState {
    data object Idle : BirthDateSaveState
    data object Loading : BirthDateSaveState
    data class Error(val message: String) : BirthDateSaveState
}

sealed interface BirthDateLoadState {
    data object Loading : BirthDateLoadState
    data object Loaded : BirthDateLoadState
    data class Error(val message: String) : BirthDateLoadState
}

// 생년월일 변경 화면 로직: GET /users/me/account로 현재 값을 불러와 휠을 맞춰두고(서버에 값이
// 없으면 기본값 2000.01.01), "변경하기"를 누르면 PATCH /users/me/account로 birth_date만 보낸다.
// 불러오기에 실패한 상태에서 저장하면 화면에 떠 있는 기본값으로 실제 생년월일이 덮어써지므로,
// 불러오기가 끝나기 전/실패한 동안에는 저장을 막는다.
class BirthDateViewModel : ViewModel() {
    var date by mutableStateOf(defaultBirthDate)
        private set

    var loadState by mutableStateOf<BirthDateLoadState>(BirthDateLoadState.Loading)
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

    fun loadCurrentValue() {
        loadState = BirthDateLoadState.Loading
        viewModelScope.launch {
            try {
                val raw = ApiClient.userApi.getAccount().birthDate
                // 서버에 값이 아예 없으면 덮어쓸 것도 없으니 기본값으로 시작해도 된다. 값은 있는데
                // 형식을 못 읽은 경우는 실제 값이 있다는 뜻이라 실패로 취급한다.
                if (!raw.isNullOrBlank()) {
                    date = LocalDate.parse(raw)
                }
                loadState = BirthDateLoadState.Loaded
            } catch (e: Exception) {
                Log.w(TAG, "생년월일 불러오기 실패", e)
                loadState = BirthDateLoadState.Error("현재 생년월일을 불러오지 못했어요.\n불러온 뒤에 변경할 수 있어요.")
            }
        }
    }

    fun save(onSuccess: () -> Unit) {
        if (loadState !is BirthDateLoadState.Loaded) return
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

private fun describeBirthDateSaveError(e: Exception): String = limitErrorMessageLength(when (e) {
    is UnknownHostException, is ConnectException -> describeConnectionFailure(e)
    is SocketTimeoutException, is TimeoutException -> describeTimeout(e)
    is HttpException -> describeHttpException(e)
    else -> describeUnexpectedError(e, "저장에 실패했어요. 잠시 후 다시 시도해주세요.")
})
