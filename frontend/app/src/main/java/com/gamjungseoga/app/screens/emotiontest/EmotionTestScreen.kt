package com.gamjungseoga.app.screens.emotiontest

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
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.TitleBrown

@Composable
fun EmotionTestScreen(
    index: Int,
    total: Int,
    question: String,
    selectedAnswer: Int?,
    onAnswerSelected: (Int) -> Unit,
    onBack: () -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        EmotionTestTopBar(onBack = onBack)
        Spacer(Modifier.height(24.dp))
        EmotionTestProgressRow(
            index = index,
            total = total,
            onPrev = onPrev,
            onNext = onNext,
            canGoPrev = index > 0,
            canGoNext = index < total - 1 && selectedAnswer != null
        )
        Spacer(Modifier.height(40.dp))
        Text(
            question,
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
        )
        Spacer(Modifier.weight(1f))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            emotionTestAnswerOptions.forEach { (label, value) ->
                EmotionTestOption(
                    label = label,
                    selected = selectedAnswer == value,
                    onClick = { onAnswerSelected(value) }
                )
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun EmotionTestTopBar(onBack: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(73.dp)
            .padding(horizontal = 8.dp)
    ) {
        IconButton(
            onClick = onBack,
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(top = 37.dp)
        ) {
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "뒤로", tint = TitleBrown)
        }
        Text(
            "퍼스널 감정 검사",
            style = MaterialTheme.typography.titleMedium,
            color = TitleBrown,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 49.dp)
        )
    }
}

@Composable
private fun EmotionTestProgressRow(
    index: Int,
    total: Int,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    canGoPrev: Boolean,
    canGoNext: Boolean
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onPrev, enabled = canGoPrev) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = "이전 문항",
                tint = if (canGoPrev) NavInactiveGray else NavInactiveGray.copy(alpha = 0.3f)
            )
        }
        Spacer(Modifier.width(16.dp))
        Text(
            buildAnnotatedString {
                withStyle(SpanStyle(color = TitleBrown)) { append("${index + 1}") }
                withStyle(SpanStyle(color = NavInactiveGray)) { append("/$total") }
            },
            style = MaterialTheme.typography.headlineSmall
        )
        Spacer(Modifier.width(16.dp))
        IconButton(onClick = onNext, enabled = canGoNext) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = "다음 문항",
                tint = if (canGoNext) NavInactiveGray else NavInactiveGray.copy(alpha = 0.3f)
            )
        }
    }
}

@Composable
private fun EmotionTestOption(label: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = if (selected) ButtonMint else Color.White,
        shape = RoundedCornerShape(16.dp),
        border = if (selected) null else BorderStroke(1.dp, CalendarCellGray),
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(
                label,
                style = MaterialTheme.typography.titleMedium,
                color = if (selected) Color.White else MonthLabelGray
            )
        }
    }
}
