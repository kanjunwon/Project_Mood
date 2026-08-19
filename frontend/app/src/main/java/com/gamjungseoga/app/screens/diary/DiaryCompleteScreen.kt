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
import com.gamjungseoga.app.R
import com.gamjungseoga.app.ui.theme.AccentGreen
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.ChartMint
import com.gamjungseoga.app.ui.theme.HighlightMint
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.RibbonPink
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown
import androidx.compose.ui.unit.Dp

// TODO: 실제 KoBERT 감정분석 결과로 교체 (sentiment/infer.py 서버 연동 전까지 목업)
private data class DiaryEmotionBar(val label: String, val percent: Int, val barHeight: Dp, val color: Color)

private val mockTopEmotion = "뿌듯함"
private val mockTopEmotionPercent = 60
private val mockEmotionBars = listOf(
    DiaryEmotionBar("뿌듯한", 60, 138.dp, ChartMint),
    DiaryEmotionBar("편안한", 30, 95.dp, AccentGreen),
    DiaryEmotionBar("행복한", 10, 56.dp, RibbonPink)
)

@Composable
fun DiaryCompleteScreen(draft: DiaryDraft, onBack: () -> Unit) {
    val diaryText = remember(draft) { buildMockDiaryText(draft) }
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
            HeroImageWithTag()
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
            CompleteSummaryCard()
        }
        item {
            Spacer(Modifier.height(16.dp))
            CompleteTopEmotionsCard()
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

private fun buildMockDiaryText(draft: DiaryDraft): String {
    val whoText = (draft.who.toList() + listOfNotNull(draft.whoCustom.takeIf { it.isNotBlank() }))
        .joinToString(", ")
        .ifBlank { "혼자" }
    return buildString {
        if (draft.what.isNotBlank()) {
            append(draft.what.trim())
            append(". ")
        }
        if (draft.where.isNotBlank()) {
            append(draft.where.trim())
            append("에서 ")
            append(whoText)
            append("와(과) 함께한 시간이었다. ")
        }
        if (draft.why.isNotBlank()) {
            append(draft.why.trim())
        }
    }.ifBlank { "오늘의 이야기를 기록했어요." }
}

@Composable
private fun HeroImageWithTag() {
    Box(modifier = Modifier.padding(horizontal = 16.dp)) {
        Image(
            painter = painterResource(R.drawable.header_illustration),
            contentDescription = null,
            contentScale = ContentScale.Crop,
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
                Text(mockTopEmotion, style = MaterialTheme.typography.labelSmall, color = TitleBrown)
            }
        }
    }
}

@Composable
private fun CompleteSummaryCard() {
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
                            append(mockTopEmotion)
                        }
                        append("이에요")
                    },
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                    color = Color.Black
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "전체 감정 중 ${mockTopEmotionPercent}%를 차지했어요",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = PretendardFontFamily),
                    color = BodyGray
                )
            }
        }
    }
}

@Composable
private fun CompleteTopEmotionsCard() {
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
                mockEmotionBars.forEach { bar ->
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
