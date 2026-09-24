package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.SurfaceColor

// 성별 변경 / 직업 변경 화면이 공유하는 UI: 상단 뒤로가기+제목, 흐르는 칩 목록, 하단 저장 버튼.
@Composable
fun ChipSelectScreen(
    title: String,
    options: List<String>,
    selected: String?,
    onSelectOption: (String) -> Unit,
    onBack: () -> Unit,
    onSave: () -> Unit,
    saving: Boolean,
    errorMessage: String?
) {
    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = title, onBack = onBack)

        Spacer(Modifier.height(24.dp))

        ChipFlowRow(
            options = options,
            selected = selected,
            onSelectOption = onSelectOption,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        if (errorMessage != null) {
            Spacer(Modifier.height(16.dp))
            Text(
                errorMessage,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        SettingsPrimaryButton(
            text = "변경하기",
            onClick = onSave,
            enabled = selected != null,
            loading = saving,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ChipFlowRow(
    options: List<String>,
    selected: String?,
    onSelectOption: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    FlowRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        options.forEach { option ->
            SelectChip(
                text = option,
                selected = option == selected,
                onClick = { onSelectOption(option) }
            )
        }
    }
}

@Composable
private fun SelectChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = if (selected) CountLabelBrown else SurfaceColor,
        shape = RoundedCornerShape(50)
    ) {
        Text(
            text,
            style = MaterialTheme.typography.bodyMedium,
            color = if (selected) Color.White else MonthLabelGray,
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp)
        )
    }
}
