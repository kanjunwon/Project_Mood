package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel

// 설정 화면의 "생년월일 변경" 진입점. GET /users/me/account로 불러온 현재 값을 BirthDateScreen에
// 넘기고, "변경하기"를 누르면 PATCH /users/me/account로 저장한다.
@Composable
fun BirthDateChangeScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    viewModel: BirthDateViewModel = viewModel()
) {
    BirthDateScreen(
        title = "생년월일 변경",
        date = viewModel.date,
        onYearChange = viewModel::setYear,
        onMonthChange = viewModel::setMonth,
        onDayChange = viewModel::setDayOfMonth,
        onBack = onBack,
        onConfirm = { viewModel.save(onSaved) },
        confirmButtonText = "변경하기",
        saving = viewModel.saveState is BirthDateSaveState.Loading,
        errorMessage = (viewModel.saveState as? BirthDateSaveState.Error)?.message
    )
}
