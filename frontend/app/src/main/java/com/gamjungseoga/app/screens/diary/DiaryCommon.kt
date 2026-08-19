package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val diaryDateFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy.MM.dd")

// 홈/아카이브/분석/설정 화면의 타이틀 텍스트 시작 높이(위 여백)와 통일시킨 값
// (60 + 40 + 40 + 40 + 13의 평균 ≈ 39.dp, 이후 요청으로 +10dp)
private val diaryTopBarTextOffset = 49.dp

@Composable
fun DiaryTopBar(onBack: (() -> Unit)? = null) {
    // 높이를 명시적으로 고정해서, IconButton의 기본 48dp 터치 영역이 박스 전체 높이를
    // 밀어 늘리지 않도록 함 (그 결과로 아래 콘텐츠가 불필요하게 더 내려가던 문제 수정)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(diaryTopBarTextOffset + 24.dp)
            .padding(horizontal = 8.dp)
    ) {
        if (onBack != null) {
            IconButton(
                onClick = onBack,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(top = diaryTopBarTextOffset - 12.dp)
            ) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "뒤로", tint = TitleBrown)
            }
        }
        Text(
            "나의 감정 일기",
            style = MaterialTheme.typography.titleMedium,
            color = TitleBrown,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = diaryTopBarTextOffset)
        )
    }
}

@Composable
fun DiaryDateLabel(date: LocalDate, modifier: Modifier = Modifier) {
    Text(
        date.format(diaryDateFormatter),
        style = MaterialTheme.typography.titleMedium,
        color = TitleBrown,
        modifier = modifier
    )
}

@Composable
fun DiaryNextButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    text: String = "다음으로",
    enabled: Boolean = true
) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        color = if (enabled) ButtonMint else ButtonMint.copy(alpha = 0.5f),
        shape = RoundedCornerShape(32.dp),
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .height(64.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(text, style = MaterialTheme.typography.titleMedium, color = Color.White)
        }
    }
}
