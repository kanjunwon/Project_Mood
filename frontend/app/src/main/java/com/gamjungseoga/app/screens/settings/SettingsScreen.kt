package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material.icons.outlined.SentimentSatisfied
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.VerticalDivider
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown

// TODO: 실제 데이터로 교체 (백엔드에서 사용자 계정/기록 정보 불러오기)
private data class SettingsRow(val label: String, val value: String? = null)

private val accountRows = listOf(
    SettingsRow("아이디", "project02"),
    SettingsRow("비밀번호 변경"),
    SettingsRow("성별 변경", "여성"),
    SettingsRow("직업 변경", "학생"),
    SettingsRow("생년월일 변경", "2002.01.18")
)

private val termsRows = listOf(
    SettingsRow("개인정보처리방침"),
    SettingsRow("이용약관 확인")
)

@Composable
fun SettingsScreen(onEmotionTestClick: () -> Unit = {}) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            Text(
                text = "설정",
                style = MaterialTheme.typography.headlineSmall,
                color = TitleBrown,
                modifier = Modifier.fillMaxWidth().padding(top = 49.dp),
                textAlign = TextAlign.Center
            )
        }
        item {
            Spacer(Modifier.height(24.dp))
            StatsCard()
        }
        item {
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                FeatureCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Filled.AutoFixHigh,
                    title = "이미지\n커스터마이징",
                    buttonText = "변경하기"
                )
                FeatureCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Outlined.SentimentSatisfied,
                    title = "퍼스널\n감정 검사",
                    buttonText = "다시하기",
                    onClick = onEmotionTestClick
                )
            }
        }
        item {
            Spacer(Modifier.height(32.dp))
            SectionLabel("계정 설정")
        }
        items(accountRows) { row ->
            SettingsListRow(row)
        }
        item {
            Spacer(Modifier.height(16.dp))
            SectionLabel("이용약관")
        }
        items(termsRows) { row ->
            SettingsListRow(row)
        }
        item {
            Spacer(Modifier.height(32.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                PillButton(text = "로그아웃", modifier = Modifier.weight(1f))
                PillButton(text = "계정탈퇴", modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        color = TitleBrown,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
    )
}

@Composable
private fun StatsCard() {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(20.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            StatColumn(
                modifier = Modifier.weight(1f),
                icon = Icons.Outlined.Edit,
                label = "감정 기록을 시작한 지",
                value = "32",
                unit = "Days"
            )
            VerticalDivider(
                modifier = Modifier.height(48.dp).padding(horizontal = 12.dp),
                color = NavInactiveGray.copy(alpha = 0.4f)
            )
            StatColumn(
                modifier = Modifier.weight(1f),
                icon = Icons.Outlined.FavoriteBorder,
                label = "기록한 감정",
                value = "12",
                unit = "Emotion"
            )
        }
    }
}

@Composable
private fun StatColumn(modifier: Modifier, icon: ImageVector, label: String, value: String, unit: String) {
    Column(modifier = modifier) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = CountLabelBrown)
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.Bottom) {
            Icon(icon, contentDescription = null, tint = SolidGreen, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(6.dp))
            Text(value, style = MaterialTheme.typography.headlineSmall, color = SolidGreen)
            Spacer(Modifier.width(6.dp))
            Text(
                unit,
                style = MaterialTheme.typography.labelSmall,
                color = NavInactiveGray,
                modifier = Modifier.padding(bottom = 4.dp)
            )
        }
    }
}

@Composable
private fun FeatureCard(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    title: String,
    buttonText: String,
    onClick: () -> Unit = {}
) {
    Surface(
        modifier = modifier,
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .background(CountLabelBrown, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.height(16.dp))
            Text(title, style = MaterialTheme.typography.titleMedium, color = TitleBrown)
            Spacer(Modifier.height(16.dp))
            Surface(
                onClick = onClick,
                color = ButtonMint,
                shape = RoundedCornerShape(50),
                modifier = Modifier.fillMaxWidth().height(36.dp)
            ) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                    Text(buttonText, style = MaterialTheme.typography.bodyMedium, color = Color.White)
                }
            }
        }
    }
}

@Composable
private fun SettingsListRow(row: SettingsRow, onClick: () -> Unit = {}) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(row.label, style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (row.value != null) {
                Text(row.value, style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
                Spacer(Modifier.width(8.dp))
            }
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MonthLabelGray
            )
        }
    }
}

@Composable
private fun PillButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit = {}) {
    Surface(
        onClick = onClick,
        color = CalendarCellGray,
        shape = RoundedCornerShape(50),
        modifier = modifier.height(56.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(text, style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
        }
    }
}
