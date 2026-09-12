package com.gamjungseoga.app.screens.settings

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel

private val jobOptions = listOf("학생", "직장인", "군인", "주부", "무직")

@Composable
fun JobScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    viewModel: JobViewModel = viewModel()
) {
    ChipSelectScreen(
        title = "직업 변경",
        options = jobOptions,
        selected = viewModel.selected,
        onSelectOption = viewModel::select,
        onBack = onBack,
        onSave = { viewModel.save(onSaved) },
        saving = viewModel.saveState is ChipSaveState.Loading,
        errorMessage = (viewModel.saveState as? ChipSaveState.Error)?.message
    )
}
