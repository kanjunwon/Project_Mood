package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.gamjungseoga.app.R
import com.gamjungseoga.app.emotion.drawableForEmotion
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.ui.theme.AccentGreen
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.ChartMint
import com.gamjungseoga.app.ui.theme.HighlightMint
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.RibbonPink
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown
import androidx.compose.ui.unit.Dp
import com.gamjungseoga.app.network.DiaryGenerateResponse

private data class DiaryEmotionBar(val label: String, val percent: Int, val barHeight: Dp, val color: Color)

private val emotionBarColors = listOf(ChartMint, AccentGreen, RibbonPink)
private val maxEmotionBarHeight = 138.dp

// emotion_scores(감정별 0~1 점수)에서 상위 3개를 뽑아 막대그래프용 데이터로 변환.
private fun buildEmotionBars(scores: Map<String, Double>?): List<DiaryEmotionBar> {
    if (scores.isNullOrEmpty()) return emptyList()
    val top3 = scores.entries.sortedByDescending { it.value }.take(3)
    return top3.mapIndexed { index, (label, score) ->
        val percent = (score * 100).toInt().coerceIn(0, 100)
        DiaryEmotionBar(
            label = label,
            percent = percent,
            barHeight = maxEmotionBarHeight * (percent / 100f).coerceAtLeast(0.15f),
            color = emotionBarColors[index % emotionBarColors.size]
        )
    }
}

@Composable
fun DiaryCompleteScreen(
    draft: DiaryDraft,
    result: DiaryGenerateResponse?,
    onBack: () -> Unit
) {
    val diaryText = result?.generatedDiary.orEmpty()
    val topEmotion = result?.topEmotion.orEmpty()
    val emotionBars = remember(result) { buildEmotionBars(result?.emotionScores) }
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
            HeroImageWithTag(topEmotion, ApiClient.resolveImageUrl(result?.imageUrl))
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
            CompleteSummaryCard(topEmotion, topEmotionPercent)
        }
        item {
            Spacer(Modifier.height(16.dp))
            CompleteTopEmotionsCard(emotionBars)
        }
        item {
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CompleteInfoCard(
                    modifier = Modifier.weight(1f),
                    iconRes = R.drawable.analysis_person_icon,
                    prefix = "오늘 함께한 사람은",
                    highlight = whoDisplay,
                    suffix = "에요"
                )
                CompleteInfoCard(
                    modifier = Modifier.weight(1f),
                    iconRes = R.drawable.analysis_location_icon,
                    prefix = "오늘 방문한 장소는",
                    highlight = whereDisplay,
                    suffix = "에요"
                )
            }
        }
    }
}

@Composable
private fun HeroImageWithTag(topEmotion: String, imageUrl: String?) {
    Box(modifier = Modifier.padding(horizontal = 16.dp)) {
        // SD3가 생성한 imageUrl이 있으면 그걸 보여주고, 없거나 로딩 실패하면 감정별 일러스트로 대체.
        // 로딩 중에도 같은 일러스트를 placeholder로 보여줘서 자리가 비어 보이지 않게 함.
        val fallback = painterResource(drawableForEmotion(topEmotion))
        AsyncImage(
            model = imageUrl,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            placeholder = fallback,
            error = fallback,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(24.dp))
        )
        Surface(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(12.dp),
            color = SurfaceColor,
            shape = RoundedCornerShape(20.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(ChartMint, CircleShape)
                )
                Spacer(Modifier.width(6.dp))
                Text(topEmotion, style = MaterialTheme.typography.labelSmall, color = TitleBrown)
            }
        }
    }
}

@Composable
private fun CompleteSummaryCard(topEmotion: String, topEmotionPercent: Int) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Image(
                painter = painterResource(R.drawable.analysis_top_emotion_circles),
                contentDescription = null,
                modifier = Modifier.size(width = 88.dp, height = 63.dp)
            )
            Spacer(Modifier.width(16.dp))
            Column {
                Text(
                    text = buildAnnotatedString {
                        append("오늘 가장 많이 느낀 감정은\n")
                        withStyle(SpanStyle(color = HighlightMint, fontWeight = FontWeight.Bold)) {
                            append(topEmotion)
                        }
                        append("이에요")
                    },
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                    color = Color.Black
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "전체 감정 중 ${topEmotionPercent}%를 차지했어요",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = PretendardFontFamily),
                    color = BodyGray
                )
            }
        }
    }
}

@Composable
private fun CompleteTopEmotionsCard(emotionBars: List<DiaryEmotionBar>) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    "주요 감정",
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily, fontWeight = FontWeight.Bold),
                    color = Color.Black
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "일기에서 추출된 핵심 감정이에요",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = PretendardFontFamily),
                    color = BodyGray
                )
            }
            Spacer(Modifier.height(24.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.Bottom
            ) {
                emotionBars.forEach { bar ->
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            modifier = Modifier
                                .width(88.dp)
                                .height(bar.barHeight)
                                .background(bar.color, RoundedCornerShape(16.dp)),
                            contentAlignment = Alignment.TopCenter
                        ) {
                            Text(
                                "${bar.percent}%",
                                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily, fontWeight = FontWeight.Bold),
                                color = Color.White,
                                modifier = Modifier.padding(top = 12.dp)
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(
                            bar.label,
                            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                            color = Color.Black
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CompleteInfoCard(
    modifier: Modifier = Modifier,
    iconRes: Int,
    prefix: String,
    highlight: String,
    suffix: String
) {
    Surface(
        modifier = modifier,
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Image(
                painter = painterResource(iconRes),
                contentDescription = null,
                modifier = Modifier.size(40.dp)
            )
            Spacer(Modifier.height(12.dp))
            Text(
                prefix,
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = PretendardFontFamily),
                color = Color.Black
            )
            Text(
                text = buildAnnotatedString {
                    withStyle(SpanStyle(color = HighlightMint, fontWeight = FontWeight.Bold)) {
                        append(highlight)
                    }
                    append(suffix)
                },
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                color = Color.Black
            )
        }
    }
}
