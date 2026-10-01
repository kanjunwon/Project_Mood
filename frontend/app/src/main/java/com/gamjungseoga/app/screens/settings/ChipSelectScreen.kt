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

// 성별 변경 / 직업 변경 화면과 회원가입의 성별/직업 단계가 공유하는 UI: 상단 뒤로가기+제목,
// 화면 하단에 모인 선택지 목록 + 바로 아래 버튼. 선택지가 적으면(성별 2개) 그룹이 더 아래쪽에,
// 많으면(직업 5개) 더 위쪽부터 차지하도록 위쪽 spacer에 weight를 줘서 전체를 하단 기준으로 쌓는다.
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

        Spacer(Modifier.weight(1f))

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
        Spacer(Modifier.height(24.dp))
    }
}
