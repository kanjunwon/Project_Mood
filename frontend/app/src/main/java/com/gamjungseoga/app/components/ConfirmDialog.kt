package com.gamjungseoga.app.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown

// 설정 화면(로그아웃/계정탈퇴)에서 쓰던 확인 다이얼로그를 일기 상세 화면("다시 작성하기")에서도
// 그대로 재사용하기 위해 공용 컴포넌트로 분리.
@Composable
fun ConfirmDialog(
    title: String,
    message: String,
    confirmText: String,
    confirmColor: Color,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
    cancelText: String = "취소",
    loading: Boolean = false
) {
    Dialog(onDismissRequest = { if (!loading) onDismiss() }) {
        Surface(
            color = SurfaceColor,
            shape = RoundedCornerShape(32.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(24.dp)
                    .fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleMedium,
                    color = TitleBrown,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(24.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        onClick = onDismiss,
                        enabled = !loading,
                        color = CalendarCellGray,
                        shape = RoundedCornerShape(50),
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                            Text(cancelText, style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
                        }
                    }
                    Surface(
                        onClick = onConfirm,
                        enabled = !loading,
                        color = if (loading) confirmColor.copy(alpha = 0.5f) else confirmColor,
                        shape = RoundedCornerShape(50),
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                            if (loading) {
                                CircularProgressIndicator(
                                    color = Color.White,
                                    strokeWidth = 2.dp,
                                    modifier = Modifier.size(20.dp)
                                )
                            } else {
                                Text(confirmText, style = MaterialTheme.typography.bodyMedium, color = Color.White)
                            }
                        }
                    }
                }
            }
        }
    }
}
