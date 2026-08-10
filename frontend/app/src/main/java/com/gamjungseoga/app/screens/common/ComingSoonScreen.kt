package com.gamjungseoga.app.screens.common

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.gamjungseoga.app.ui.theme.TextMuted

// TODO: 피그마 화면 나오면 이 화면들도 각자 파일로 분리해서 실제 내용으로 교체
@Composable
fun ComingSoonScreen(title: String) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(
            text = "$title 화면 준비 중이에요",
            style = MaterialTheme.typography.bodyMedium,
            color = TextMuted
        )
    }
}
