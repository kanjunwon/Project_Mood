package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate

@Composable
fun DiaryQuestionScreen(
    date: LocalDate,
    question: String,
    answer: String,
    onAnswerChange: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit,
    charLimit: Int = 500
) {
    Column(modifier = Modifier.fillMaxSize()) {
        DiaryTopBar(onBack = onBack)
        Spacer(Modifier.height(16.dp))
        DiaryDateLabel(date, modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(16.dp))
        Text(
            question,
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            BasicTextField(
                value = answer,
                onValueChange = { if (it.length <= charLimit) onAnswerChange(it) },
                modifier = Modifier.fillMaxWidth(),
                textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily, color = Color.Black),
                cursorBrush = SolidColor(TitleBrown),
                decorationBox = { innerTextField ->
                    if (answer.isEmpty()) {
                        Text(
                            "이곳을 눌러서 답변을 입력해주세요.",
                            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                            color = NavInactiveGray
                        )
                    }
                    innerTextField()
                }
            )
        }
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
            Text(
                "${answer.length}/$charLimit",
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.End,
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = PretendardFontFamily),
                color = NavInactiveGray
            )
        }
        Spacer(Modifier.height(16.dp))
        DiaryNextButton(onClick = onNext, enabled = answer.isNotBlank())
        Spacer(Modifier.height(16.dp))
    }
}
