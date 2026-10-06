package com.gamjungseoga.app.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.gamjungseoga.app.R
import com.gamjungseoga.app.emotion.drawableForEmotion
import com.gamjungseoga.app.ui.theme.AccentGreen
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.ChartMint
import com.gamjungseoga.app.ui.theme.HighlightMint
import com.gamjungseoga.app.ui.theme.RibbonPink
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown

// 일기 생성 완료/상세보기/분석(일간) 화면이 모두 같은 모양의 "감정 리포트" 위젯 묶음(히어로 이미지+뱃지,
// 오늘의 대표 감정 카드, 주요 감정 막대 카드, 사람/장소 카드)을 쓰므로 여기 한 곳에 모아 공유한다.
// 화면마다 본문 폰트(Pretendard/S-Core Dream)가 다르게 쓰이는 건 의도된 디자인이라 fontFamily를
// 파라미터로 받는다.

data class EmotionBar(val label: String, val percent: Int, val barHeight: Dp, val color: Color)

val defaultEmotionBarPalette = listOf(ChartMint, AccentGreen, RibbonPink)
val defaultEmotionBarMaxHeight = 138.dp

// emotion_scores(감정별 0~1 점수)에서 상위 3개를 뽑아 막대그래프용 데이터로 변환.
// DiaryGenerateResponse/DiaryEntry 둘 다 이 모양(Map<String, Double>)의 emotion_scores를 내려준다.
fun topEmotionBarsFromScores(
    scores: Map<String, Double>?,
    palette: List<Color> = defaultEmotionBarPalette,
    maxBarHeight: Dp = defaultEmotionBarMaxHeight
): List<EmotionBar> {
    if (scores.isNullOrEmpty()) return emptyList()
    val top3 = scores.entries.sortedByDescending { it.value }.take(3)
    return top3.mapIndexed { index, (label, score) ->
        val percent = (score * 100).toInt().coerceIn(0, 100)
        EmotionBar(
            label = label,
            percent = percent,
            barHeight = maxBarHeight * (percent / 100f).coerceAtLeast(0.15f),
            color = palette[index % palette.size]
        )
    }
}

// SD3가 생성한 imageUrl이 있으면 그걸 보여주고, 없거나 로딩 실패하면 감정별 일러스트로 대체.
// 로딩 중에도 같은 일러스트를 placeholder로 보여줘서 자리가 비어 보이지 않게 함.
@Composable
fun EmotionHeroImage(topEmotion: String, imageUrl: String?, modifier: Modifier = Modifier) {
    val fallback = painterResource(drawableForEmotion(topEmotion))
    AsyncImage(
        model = imageUrl,
        contentDescription = null,
        contentScale = ContentScale.Crop,
        placeholder = fallback,
        error = fallback,
        modifier = modifier
            .aspectRatio(1f)
            .clip(RoundedCornerShape(24.dp))
    )
}

// 흰 배경 + 둥근 모서리 + 왼쪽 작은 원형 점 + 감정 이름. 히어로 이미지 위에 겹쳐 쓰거나(완료/상세 화면),
// 날짜 옆에 나란히 쓸 수도 있어서(상세 화면) 위치는 호출 쪽 modifier에 맡긴다.
@Composable
fun EmotionBadge(topEmotion: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
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

// "오늘(이번 달) 가장 많이 느낀 감정은 OO이에요 / 전체 감정 중 N%를 차지했어요" 카드.
// titlePrefix는 끝에 줄바꿈까지 포함해서 넘긴다 (예: "오늘 가장 많이 느낀 감정은\n").
@Composable
fun EmotionSummaryCard(
    titlePrefix: String,
    emotion: String,
    percent: Int,
    fontFamily: FontFamily,
    modifier: Modifier = Modifier,
    emotionColor: Color = HighlightMint
) {
    Surface(
        modifier = modifier.fillMaxWidth().padding(horizontal = 16.dp),
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
                        append(titlePrefix)
                        withStyle(SpanStyle(color = emotionColor, fontWeight = FontWeight.Bold)) {
                            append(emotion)
                        }
                        append("이에요")
                    },
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = fontFamily),
                    color = Color.Black
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "전체 감정 중 ${percent}%를 차지했어요",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = fontFamily),
                    color = BodyGray
                )
            }
        }
    }
}

// "주요 감정" 카드: emotionBars 상위 3개를 비율에 따른 높이의 막대로 보여준다.
@Composable
fun TopEmotionsBarCard(emotionBars: List<EmotionBar>, fontFamily: FontFamily, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    "주요 감정",
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = fontFamily, fontWeight = FontWeight.Bold),
                    color = Color.Black
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "일기에서 추출된 핵심 감정이에요",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = fontFamily),
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
                                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = fontFamily, fontWeight = FontWeight.Bold),
                                color = Color.White,
                                modifier = Modifier.padding(top = 12.dp)
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(
                            bar.label,
                            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = fontFamily),
                            color = Color.Black
                        )
                    }
                }
            }
        }
    }
}

// "오늘 함께한 사람은/오늘 방문한 장소는 OO에요" 카드. 위에 아이콘, 아래 강조 텍스트.
@Composable
fun PersonPlaceInfoCard(
    modifier: Modifier = Modifier,
    iconRes: Int,
    prefix: String,
    highlight: String,
    fontFamily: FontFamily,
    suffix: String = "에요"
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
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = fontFamily),
                color = Color.Black
            )
            Text(
                text = buildAnnotatedString {
                    withStyle(SpanStyle(color = HighlightMint, fontWeight = FontWeight.Bold)) {
                        append(highlight)
                    }
                    append(suffix)
                },
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = fontFamily),
                color = Color.Black
            )
        }
    }
}
