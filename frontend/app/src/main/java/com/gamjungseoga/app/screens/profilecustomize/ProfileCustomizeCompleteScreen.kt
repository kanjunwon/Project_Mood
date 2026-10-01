package com.gamjungseoga.app.screens.profilecustomize

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.screens.settings.ResultValueBox
import com.gamjungseoga.app.screens.settings.SettingsPrimaryButton
import com.gamjungseoga.app.screens.settings.SettingsSubScreenTopBar
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.TitleBrown

// 이미지 커스터마이징 4단계를 모두 고른 뒤 보여주는 요약 화면. 선택값은 결과 표시용이라
// 누를 수 없고, 아래 "변경하기"(1단계로 돌아가 다시 고르기)/"확인하기"(저장) 두 버튼만 동작한다.
@Composable
fun ProfileCustomizeCompleteScreen(
    summaryLabels: List<String>,
    onBack: () -> Unit,
    onEditAgain: () -> Unit,
    onConfirm: () -> Unit,
    saving: Boolean,
    errorMessage: String?
) {
    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = "이미지 커스터마이징", onBack = onBack)

        Spacer(Modifier.weight(1f))

        Text(
            "이미지 커스터마이징이\n완료되었습니다",
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 32.dp)
        )

        Spacer(Modifier.height(32.dp))

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            summaryLabels.forEach { label ->
                ResultValueBox(text = label)
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

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SettingsPrimaryButton(
                text = "변경하기",
                onClick = onEditAgain,
                enabled = !saving,
                color = CalendarCellGray,
                contentColor = MonthLabelGray,
                modifier = Modifier.weight(1f)
            )
            SettingsPrimaryButton(
                text = "확인하기",
                onClick = onConfirm,
                enabled = !saving,
                loading = saving,
                modifier = Modifier.weight(1f)
            )
        }
        Spacer(Modifier.height(24.dp))
    }
}
