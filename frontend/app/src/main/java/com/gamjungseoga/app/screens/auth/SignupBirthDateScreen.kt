package com.gamjungseoga.app.screens.auth

import androidx.compose.runtime.Composable
import com.gamjungseoga.app.screens.settings.BirthDateScreen
import java.time.LocalDate

// 회원가입 마지막 단계. 기존 값을 불러오지 않고(로그인 전이라 불러올 수 없음) SignupViewModel의
// draft를 그대로 쓰며, 버튼을 누르면 호출부(MainActivity)가 POST /signup -> PATCH /users/me/account
// 두 요청을 순서대로 실행한다.
@Composable
fun SignupBirthDateScreen(
    date: LocalDate,
    onYearChange: (Int) -> Unit,
    onMonthChange: (Int) -> Unit,
    onDayChange: (Int) -> Unit,
    onBack: () -> Unit,
    onConfirm: () -> Unit,
    saving: Boolean,
    errorMessage: String?
) {
    BirthDateScreen(
        title = "생년월일",
        date = date,
        onYearChange = onYearChange,
        onMonthChange = onMonthChange,
        onDayChange = onDayChange,
        onBack = onBack,
        onConfirm = onConfirm,
        confirmButtonText = "완료하고 로그인 화면으로 돌아가기",
        saving = saving,
        errorMessage = errorMessage
    )
}
