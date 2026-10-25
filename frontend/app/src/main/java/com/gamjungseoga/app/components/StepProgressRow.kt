package com.gamjungseoga.app.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.TitleBrown

// 퍼스널 감정 검사/이미지 커스터마이징이 공유하는 "‹ 1/4 ›" 단계 표시. 숫자를 화면 가운데 두고
// 그 양옆에 이전/다음 화살표를 붙인다(피그마). onPrev/onNext가 null이면 해당 화살표를 흐리게 비활성화.
// current는 1부터 시작하는 값.
@Composable
fun StepProgressRow(
    current: Int,
    total: Int,
    onPrev: (() -> Unit)?,
    onNext: (() -> Unit)?,
    prevContentDescription: String,
    nextContentDescription: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = { onPrev?.invoke() }, enabled = onPrev != null) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = prevContentDescription,
                tint = if (onPrev != null) NavInactiveGray else NavInactiveGray.copy(alpha = 0.3f)
            )
        }
        Spacer(Modifier.width(16.dp))
        Text(
            buildAnnotatedString {
                withStyle(SpanStyle(color = TitleBrown)) { append("$current") }
                withStyle(SpanStyle(color = NavInactiveGray)) { append("/$total") }
            },
            style = MaterialTheme.typography.headlineSmall
        )
        Spacer(Modifier.width(16.dp))
        IconButton(onClick = { onNext?.invoke() }, enabled = onNext != null) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = nextContentDescription,
                tint = if (onNext != null) NavInactiveGray else NavInactiveGray.copy(alpha = 0.3f)
            )
        }
    }
}
