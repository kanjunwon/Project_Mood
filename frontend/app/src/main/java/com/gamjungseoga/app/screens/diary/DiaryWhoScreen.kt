package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate

private val diaryWhoOptions = listOf(
    "가족", "남매", "친구", "남성친구", "여성친구", "연인",
    "반려동물", "강아지", "고양이", "자녀", "엄마", "아빠", "형제", "혼자"
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
    Column(modifier = Modifier.fillMaxSize()) {
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
            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
            color = NavInactiveGray,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(20.dp))
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                diaryWhoOptions.forEach { option ->
                    WhoChip(label = option, selected = option in selected, onClick = { onToggle(option) })
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

@Composable
private fun WhoChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .then(
                if (selected) {
                    Modifier.background(CountLabelBrown)
                } else {
                    Modifier
                        .background(Color.White)
                        .border(2.dp, NavInactiveGray, RoundedCornerShape(50))
                }
            )
            .clickable { onClick() }
            .padding(horizontal = 20.dp, vertical = 14.dp)
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
            color = if (selected) Color.White else TitleBrown
        )
        if (selected) {
            Spacer(Modifier.width(6.dp))
            Icon(Icons.Filled.Check, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
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
            .border(2.dp, NavInactiveGray, RoundedCornerShape(50))
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        Text("기타", style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily), color = TitleBrown)
        Spacer(Modifier.width(16.dp))
        Box(modifier = Modifier.weight(1f)) {
            BasicTextField(
                value = text,
                onValueChange = onTextChange,
                modifier = Modifier.fillMaxWidth(),
                textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily, color = Color.Black),
                cursorBrush = SolidColor(TitleBrown),
                decorationBox = { innerTextField ->
                    if (text.isEmpty()) {
                        Text("이곳에 작성해 주세요.", style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily), color = NavInactiveGray)
                    }
                    innerTextField()
                }
            )
        }
    }
}
