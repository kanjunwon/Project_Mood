package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.SurfaceColor
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
    loading: Boolean = false,
    color: Color = SolidGreen,
    contentColor: Color = Color.White,
    border: BorderStroke? = null
) {
    Surface(
        onClick = onClick,
        enabled = enabled && !loading,
        color = if (enabled) color else color.copy(alpha = 0.5f),
        border = border,
        shape = RoundedCornerShape(32.dp),
        modifier = modifier
            .fillMaxWidth()
            .height(64.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            if (loading) {
                CircularProgressIndicator(color = contentColor, strokeWidth = 2.dp, modifier = Modifier.size(24.dp))
            } else {
                Text(text, style = MaterialTheme.typography.titleMedium, color = contentColor)
            }
        }
    }
}

// 이미지 커스터마이징 완료 화면에서 선택 결과를 보여주는 용도. SelectableOptionButton의 "선택됨"
// 상태와 같은 모양이지만 누를 수 없는 결과 표시 전용이라 onClick이 없다.
@Composable
fun ResultValueBox(text: String, modifier: Modifier = Modifier) {
    Surface(
        color = CountLabelBrown,
        shape = RoundedCornerShape(16.dp),
        modifier = modifier
            .fillMaxWidth()
            .height(56.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(text, style = MaterialTheme.typography.bodyMedium, color = Color.White)
        }
    }
}

// 이미지 커스터마이징 선택지, 성별/직업 변경 칩, 퍼스널 감정 검사 답변이 공유하는 선택 버튼. 가로로 꽉 차고
// 세로로 쌓이는 흰 배경/회색 글씨 -> 선택 시 selectedColor 배경/흰 글씨로 바뀌는 디자인.
// 이 버튼들은 누르자마자 다음 단계로 넘어가는 경우가 많아서, 머티리얼 ripple(반투명 회색 덮개)을 쓰면
// 사용자가 보는 건 "회색으로 눌렸다가 넘어감"뿐이고 선택 색이 묻힌다. 그래서 ripple 없이, 누르는 동안에도
// 선택 색을 그대로 보여줘서 누름 = 선택 색이 되게 한다.
@Composable
fun SelectableOptionButton(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    selectedColor: Color = CountLabelBrown,
    height: Dp = 56.dp,
    textStyle: TextStyle = MaterialTheme.typography.bodyMedium
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val highlighted = selected || (pressed && enabled)
    val shape = RoundedCornerShape(16.dp)
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .clip(shape)
            .background(if (highlighted) selectedColor else SurfaceColor)
            .then(if (highlighted) Modifier else Modifier.border(1.dp, CalendarCellGray, shape))
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                role = Role.RadioButton,
                onClick = onClick
            )
    ) {
        Text(
            text,
            style = textStyle,
            color = if (highlighted) Color.White else BodyGray
        )
    }
}
