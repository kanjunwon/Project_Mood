package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material3.CircularProgressIndicator
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
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown

// 설정 화면에서 진입하는 하위 화면들(성별/직업/생년월일 변경 등)이 같이 쓰는 톱바/저장 버튼.
private val settingsSubScreenTopBarTextOffset = 49.dp // AuthTopBar/DiaryTopBar와 동일한 상단 여백 기준

@Composable
fun SettingsSubScreenTopBar(title: String, onBack: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(settingsSubScreenTopBarTextOffset + 24.dp)
            .padding(horizontal = 8.dp)
    ) {
        IconButton(
            onClick = onBack,
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(top = settingsSubScreenTopBarTextOffset - 12.dp)
        ) {
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "뒤로", tint = TitleBrown)
        }
        Text(
            title,
            style = MaterialTheme.typography.titleMedium,
            color = TitleBrown,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = settingsSubScreenTopBarTextOffset)
        )
    }
}

@Composable
fun SettingsPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false
) {
    Surface(
        onClick = onClick,
        enabled = enabled && !loading,
        color = if (enabled) SolidGreen else SolidGreen.copy(alpha = 0.5f),
        shape = RoundedCornerShape(32.dp),
        modifier = modifier
            .fillMaxWidth()
            .height(64.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            if (loading) {
                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(24.dp))
            } else {
                Text(text, style = MaterialTheme.typography.titleMedium, color = Color.White)
            }
        }
    }
}
