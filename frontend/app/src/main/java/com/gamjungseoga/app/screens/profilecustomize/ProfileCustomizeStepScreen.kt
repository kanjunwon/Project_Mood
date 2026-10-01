package com.gamjungseoga.app.screens.profilecustomize

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.screens.settings.SettingsSubScreenTopBar
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown

data class ProfileCustomizeOption(val label: String, val code: String)

// 이미지 커스터마이징 4단계(안경/앞머리/머리길이/머리색)가 공유하는 레이아웃. 질문과 선택지만
// 단계별로 다르고 상단바/단계표시/이전·다음 화살표/선택지 목록 구조는 동일하다.
@Composable
fun ProfileCustomizeStepScreen(
    step: Int,
    totalSteps: Int,
    question: String,
    options: List<ProfileCustomizeOption>,
    selectedCode: String?,
    optionsEnabled: Boolean,
    onSelectOption: (String) -> Unit,
    onBack: () -> Unit,
    onPrevStep: (() -> Unit)?,
    onNextStep: (() -> Unit)?,
    errorMessage: String? = null
) {
    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = "이미지 커스터마이징", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            StepIndicator(step = step, totalSteps = totalSteps)
            Row(verticalAlignment = Alignment.CenterVertically) {
                StepArrowButton(
                    icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                    onClick = onPrevStep,
                    contentDescription = "이전 단계"
                )
                StepArrowButton(
                    icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    onClick = onNextStep,
                    contentDescription = "다음 단계"
                )
            }
        }

        Spacer(Modifier.weight(1f))

        Text(
            question,
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 32.dp)
        )

        Spacer(Modifier.weight(1f))

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            options.forEach { option ->
                ProfileOptionButton(
                    text = option.label,
                    selected = option.code == selectedCode,
                    enabled = optionsEnabled,
                    onClick = { onSelectOption(option.code) }
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

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StepIndicator(step: Int, totalSteps: Int) {
    Row(verticalAlignment = Alignment.Bottom) {
        Text("$step", style = MaterialTheme.typography.headlineSmall, color = TitleBrown)
        Text("/$totalSteps", style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
    }
}

@Composable
private fun StepArrowButton(icon: ImageVector, onClick: (() -> Unit)?, contentDescription: String) {
    IconButton(onClick = { onClick?.invoke() }, enabled = onClick != null) {
        Icon(
            icon,
            contentDescription = contentDescription,
            tint = if (onClick != null) TitleBrown else TitleBrown.copy(alpha = 0.3f)
        )
    }
}

@Composable
private fun ProfileOptionButton(
    text: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        color = if (selected) CountLabelBrown else SurfaceColor,
        border = if (selected) null else BorderStroke(1.dp, CalendarCellGray),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(
                text,
                style = MaterialTheme.typography.bodyMedium,
                color = if (selected) Color.White else MonthLabelGray
            )
        }
    }
}
