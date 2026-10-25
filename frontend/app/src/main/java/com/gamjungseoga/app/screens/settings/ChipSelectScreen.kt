package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.MonthLabelGray

private val chipSelectTopSpacing = 120.dp // 톱바 아래부터 선택지 묶음 시작까지

// 성별 변경 / 직업 변경 화면과 회원가입의 성별/직업 단계가 공유하는 UI: 상단 뒤로가기+제목,
// 선택지 목록 + 바로 아래 버튼. 예전엔 하단 기준으로 쌓아서 선택지가 적으면(성별 2개) 위쪽이
// 크게 비었는데, 피그마처럼 선택지 개수와 상관없이 톱바 아래 고정 간격에서 시작하고 남는 공간은
// 아래로 보낸다.
@Composable
fun ChipSelectScreen(
    title: String,
    options: List<String>,
    selected: String?,
    onSelectOption: (String) -> Unit,
    onBack: () -> Unit,
    onSave: () -> Unit,
    saving: Boolean,
    errorMessage: String?,
    buttonText: String = "변경하기"
) {
    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = title, onBack = onBack)

        Spacer(Modifier.height(chipSelectTopSpacing))

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            options.forEach { option ->
                SelectableOptionButton(
                    text = option,
                    selected = option == selected,
                    onClick = { onSelectOption(option) }
                )
            }
        }

        if (errorMessage != null) {
            Spacer(Modifier.height(12.dp))
            Text(
                errorMessage,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.height(16.dp))

        SettingsPrimaryButton(
            text = buttonText,
            onClick = onSave,
            enabled = selected != null,
            loading = saving,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.weight(1f))
    }
}
