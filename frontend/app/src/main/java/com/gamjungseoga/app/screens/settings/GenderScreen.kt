package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel

private val genderOptions = listOf("남성", "여성")

@Composable
fun GenderScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    viewModel: GenderViewModel = viewModel()
) {
    ChipSelectScreen(
        title = "성별 변경",
        options = genderOptions,
        selected = viewModel.selected,
        onSelectOption = viewModel::select,
        onBack = onBack,
        onSave = { viewModel.save(onSaved) },
        saving = viewModel.saveState is ChipSaveState.Loading,
        errorMessage = (viewModel.saveState as? ChipSaveState.Error)?.message
    )
}
