package com.gamjungseoga.app.components

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.navigation.Screen
import com.gamjungseoga.app.ui.theme.AccentTeal
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TextMuted

@Composable
fun BottomNavBar(
    currentRoute: String,
    onNavigate: (String) -> Unit,
    onAddClick: () -> Unit
) {
    // 바깥 박스: 실제 바(72dp)보다 높이를 크게(88dp) 잡아서 위쪽에 FAB(+)가
    // 튀어나올 여유 공간을 확보하는 컨테이너
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(88.dp)
    ) {
        // 흰색 바탕의 실제 네비게이션 바 (홈/아카이브/분석/설정 4개 탭)
        Surface(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(72.dp),
            color = SurfaceColor,
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
            shadowElevation = 8.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                NavItem(Icons.Filled.Home, "홈", currentRoute == Screen.Home.route) {
                    onNavigate(Screen.Home.route)
                }
                NavItem(Icons.Filled.Book, "아카이브", currentRoute == Screen.Archive.route) {
                    onNavigate(Screen.Archive.route)
                }
                Spacer(modifier = Modifier.width(56.dp))
                NavItem(Icons.Filled.BarChart, "분석", currentRoute == Screen.Analysis.route) {
                    onNavigate(Screen.Analysis.route)
                }
                NavItem(Icons.Filled.Settings, "설정", currentRoute == Screen.Settings.route) {
                    onNavigate(Screen.Settings.route)
                }
            }
        }
        // 바 위에 겹쳐서 튀어나오는 중앙 + 버튼 (바깥 박스의 여유 공간 88-72=16dp 안에 위치)
        FloatingActionButton(
            onClick = onAddClick,
            modifier = Modifier.align(Alignment.TopCenter),
            shape = CircleShape,
            containerColor = AccentTeal,
            contentColor = Color.White
        ) {
            Icon(Icons.Filled.Add, contentDescription = "새 페이지 작성")
        }
    }
}

@Composable
private fun NavItem(icon: ImageVector, label: String, selected: Boolean, onClick: () -> Unit) {
    Column(
        modifier = Modifier.clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, contentDescription = label, tint = if (selected) AccentTeal else TextMuted)
        Text(label, style = MaterialTheme.typography.labelSmall, color = if (selected) AccentTeal else TextMuted)
    }
}
