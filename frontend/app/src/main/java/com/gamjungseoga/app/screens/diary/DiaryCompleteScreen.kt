package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.R
import com.gamjungseoga.app.components.EmotionBadge
import com.gamjungseoga.app.components.EmotionHeroImage
import com.gamjungseoga.app.components.EmotionSummaryCard
import com.gamjungseoga.app.components.PersonPlaceInfoCard
import com.gamjungseoga.app.components.TopEmotionsBarCard
import com.gamjungseoga.app.components.topEmotionBarsFromScores
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryGenerateResponse
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.TitleBrown

@Composable
fun DiaryCompleteScreen(
    draft: DiaryDraft,
    result: DiaryGenerateResponse?,
    onBack: () -> Unit
) {
    val diaryText = result?.generatedDiary.orEmpty()
    val topEmotion = result?.topEmotion.orEmpty()
    val emotionBars = remember(result) { topEmotionBarsFromScores(result?.emotionScores) }
    val topEmotionPercent = emotionBars.firstOrNull()?.percent ?: 0
    val whoDisplay = draft.who.firstOrNull() ?: draft.whoCustom.ifBlank { "혼자" }
    val whereDisplay = draft.where.ifBlank { "기록된 장소 없음" }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item { DiaryTopBar(onBack = onBack) }
        item {
            Spacer(Modifier.height(8.dp))
            DiaryDateLabel(draft.date, modifier = Modifier.padding(horizontal = 16.dp))
        }
        item {
            Spacer(Modifier.height(16.dp))
            Box(modifier = Modifier.padding(horizontal = 16.dp)) {
                EmotionHeroImage(
                    topEmotion = topEmotion,
                    imageUrl = ApiClient.resolveImageUrl(result?.imageUrl),
                    modifier = Modifier.fillMaxWidth()
                )
                EmotionBadge(
                    topEmotion = topEmotion,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(12.dp)
                )
            }
        }
        item {
            Spacer(Modifier.height(20.dp))
            Text(
                diaryText,
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                color = Color.Black,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }
        item {
            Spacer(Modifier.height(24.dp))
            Text(
                "오늘의 감정 리포트",
                style = MaterialTheme.typography.titleMedium,
                color = TitleBrown,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }
        item {
            Spacer(Modifier.height(12.dp))
            EmotionSummaryCard(
                titlePrefix = "오늘 가장 많이 느낀 감정은\n",
                emotion = topEmotion,
                percent = topEmotionPercent,
                fontFamily = PretendardFontFamily
            )
        }
        item {
            Spacer(Modifier.height(16.dp))
            TopEmotionsBarCard(emotionBars, fontFamily = PretendardFontFamily)
        }
        item {
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PersonPlaceInfoCard(
                    modifier = Modifier.weight(1f),
                    iconRes = R.drawable.analysis_person_icon,
                    prefix = "오늘 함께한 사람은",
                    highlight = whoDisplay,
                    fontFamily = PretendardFontFamily
                )
                PersonPlaceInfoCard(
                    modifier = Modifier.weight(1f),
                    iconRes = R.drawable.analysis_location_icon,
                    prefix = "오늘 방문한 장소는",
                    highlight = whereDisplay,
                    fontFamily = PretendardFontFamily
                )
            }
        }
    }
}
