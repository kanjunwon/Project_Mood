package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.OmyuPrettyFontFamily
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate

// 피그마처럼 관계별 묶음(가족 / 친구·연인 / 반려동물 / 혼자)으로 나눠서, 묶음마다 새 줄에서 시작하게 함.
// 묶음 안에서는 화면 폭에 따라 자동 줄바꿈.
private val diaryWhoOptionGroups = listOf(
    listOf("가족", "엄마", "아빠", "형제", "남매", "자녀"),
    listOf("친구", "연인", "남성친구", "여성친구"),
    listOf("반려동물", "강아지", "고양이"),
    listOf("혼자")
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DiaryWhoScreen(
    date: LocalDate,
    selected: Set<String>,
    customText: String,
    onToggle: (String) -> Unit,
    onCustomTextChange: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit
) {
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                detectTapGestures(onTap = {
                    focusManager.clearFocus()
                    keyboardController?.hide()
                })
            }
            .imePadding()
    ) {
        DiaryTopBar(onBack = onBack)
        Spacer(Modifier.height(16.dp))
        DiaryDateLabel(date, modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(16.dp))
        Text(
            "누구와 함께 했던 일인가요?",
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "복수 응답이 가능해요",
            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = OmyuPrettyFontFamily),
            color = NavInactiveGray,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(20.dp - whoCheckBadgeOverhang))
        // padding을 verticalScroll 뒤(스크롤 영역 안쪽)에 둬서, 칩 모서리 밖으로 걸치는 체크 배지가
        // 스크롤 영역 경계(위/오른쪽)에서 잘리지 않게 한다. 위쪽 여백은 위 Spacer에서 그만큼 뺌.
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, top = whoCheckBadgeOverhang)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                diaryWhoOptionGroups.forEach { group ->
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        group.forEach { option ->
                            WhoChip(label = option, selected = option in selected, onClick = { onToggle(option) })
                        }
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            WhoCustomChip(text = customText, onTextChange = onCustomTextChange)
        }
        Spacer(Modifier.height(16.dp))
        DiaryNextButton(onClick = onNext, enabled = selected.isNotEmpty() || customText.isNotBlank())
        Spacer(Modifier.height(16.dp))
    }
}

private val WhoChipTextStyle
    @Composable get() = MaterialTheme.typography.bodyMedium.copy(fontFamily = OmyuPrettyFontFamily, fontSize = 14.sp)

// 체크 배지가 칩 오른쪽 위 모서리 밖으로 걸치는 양. 칩 목록 스크롤 영역이 위/오른쪽에 이만큼 여유를
// 둬야 배지가 잘리지 않는다(DiaryWhoScreen의 칩 Column padding 참고).
private val whoCheckBadgeSize = 16.dp
private val whoCheckBadgeOverhang = 5.dp

// 피그마처럼 얇은 테두리/낮은 높이의 가벼운 칩. 선택되면 오른쪽 위 모서리에 작은 원형 체크 배지가
// 겹쳐 붙는다. 배지는 칩 바깥에 그려서 칩 너비가 바뀌지 않으므로(바뀌면 FlowRow 줄바꿈이 다시
// 계산돼서 칩들이 다른 줄로 튐) 텍스트도 항상 칩 가운데에 온다.
// 좌우 padding 25dp = 예전 16dp + 텍스트 옆 체크 자리(4 + 14dp)의 절반: 칩 크기를 예전과 같게 유지.
@Composable
private fun WhoChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Box {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .clip(RoundedCornerShape(50))
                .then(
                    if (selected) {
                        Modifier.background(CountLabelBrown)
                    } else {
                        Modifier
                            .background(Color.White)
                            .border(1.dp, NavInactiveGray, RoundedCornerShape(50))
                    }
                )
                .clickable { onClick() }
                .padding(horizontal = 25.dp, vertical = 8.dp)
        ) {
            Text(
                label,
                style = WhoChipTextStyle,
                color = if (selected) Color.White else TitleBrown
            )
        }
        if (selected) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = whoCheckBadgeOverhang, y = -whoCheckBadgeOverhang)
                    .size(whoCheckBadgeSize)
                    .background(TitleBrown, CircleShape)
                    .border(1.5.dp, Color.White, CircleShape)
            ) {
                Icon(Icons.Filled.Check, contentDescription = null, tint = Color.White, modifier = Modifier.size(10.dp))
            }
        }
    }
}

@Composable
private fun WhoCustomChip(text: String, onTextChange: (String) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(50))
            .background(Color.White)
            .border(1.dp, NavInactiveGray, RoundedCornerShape(50))
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        Text("기타", style = WhoChipTextStyle, color = TitleBrown)
        Spacer(Modifier.width(16.dp))
        Box(modifier = Modifier.weight(1f)) {
            BasicTextField(
                value = text,
                onValueChange = onTextChange,
                modifier = Modifier.fillMaxWidth(),
                textStyle = WhoChipTextStyle.copy(color = Color.Black),
                cursorBrush = SolidColor(TitleBrown),
                decorationBox = { innerTextField ->
                    if (text.isEmpty()) {
                        Text("이곳에 작성해 주세요.", style = WhoChipTextStyle, color = NavInactiveGray)
                    }
                    innerTextField()
                }
            )
        }
    }
}
