package com.gamjungseoga.app.screens.analysis

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.gamjungseoga.app.R
import com.gamjungseoga.app.components.EmotionBar
import com.gamjungseoga.app.components.EmotionIconCircle
import com.gamjungseoga.app.components.EmotionSummaryCard
import com.gamjungseoga.app.components.PersonPlaceInfoCard
import com.gamjungseoga.app.components.TopEmotionsBarCard
import com.gamjungseoga.app.components.WheelPicker
import com.gamjungseoga.app.emotion.EmotionGroup
import com.gamjungseoga.app.emotion.emotionColorFor
import com.gamjungseoga.app.emotion.emotionTextColorFor
import com.gamjungseoga.app.network.describeLoadError
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DailyStatsResponse
import com.gamjungseoga.app.network.EmotionFlowPoint
import com.gamjungseoga.app.network.EmotionScore
import com.gamjungseoga.app.network.MonthlyStatsResponse
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.EmptyGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.SCoreDreamFontFamily
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TabInactiveGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import com.gamjungseoga.app.util.Josa
import com.gamjungseoga.app.util.josaFor
import com.gamjungseoga.app.util.withJosa
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

private enum class ReportTab(val label: String) { DAILY("일간"), MONTHLY("월간") }

private val analysisDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM.dd")
private val analysisMonthFormatter = DateTimeFormatter.ofPattern("yyyy.MM")

// GET /stats/daily, /stats/monthly의 top3_emotions는 여러 일기의 점수를 그냥 합산한 값이라(1.0 안
// 넘게 정규화돼있지 않음) 3개 막대끼리 상대 비중으로 다시 나눠서 60/30/10 같은 퍼센트를 만듦.
// 막대 색은 순위가 아니라 감정 이름으로 정한다(emotionColorFor) - 일간/월간 공통.
private fun toTopEmotionBars(scores: List<EmotionScore>): List<EmotionBar> {
    val total = scores.sumOf { it.score }
    if (scores.isEmpty() || total <= 0) return emptyList()
    return scores.map { item ->
        val percent = (item.score / total * 100).toInt().coerceIn(0, 100)
        EmotionBar(
            label = item.emotion,
            percent = percent,
            color = emotionColorFor(item.emotion)
        )
    }
}

data class WeekPoint(val label: String, val value: Float)

// emotion_flow는 하루 단위 sentiment_score만 내려주므로, 그 달 안에서 일(day) 순서대로 7일씩
// 묶어 주차 평균을 내고, 차트가 쓰기 좋게 그 달 안에서의 최소/최대로 다시 0~1로 정규화함
// (sentiment_score의 실제 범위를 백엔드 코드를 보지 않고는 알 수 없어서, 상대적인 높낮이만 표현)
private fun toWeeklyFlow(emotionFlow: List<EmotionFlowPoint>): List<WeekPoint> {
    val parsed = emotionFlow.mapNotNull { point ->
        runCatching { LocalDate.parse(point.date) }.getOrNull()?.let { it to point.sentimentScore }
    }
    if (parsed.isEmpty()) return emptyList()

    val weeklyAverages = parsed
        .groupBy { (date, _) -> (date.dayOfMonth - 1) / 7 }
        .toSortedMap()
        .map { (weekIndex, entries) -> weekIndex to entries.map { it.second }.average() }

    val min = weeklyAverages.minOf { it.second }
    val max = weeklyAverages.maxOf { it.second }
    val range = (max - min).takeIf { it > 0.0 }

    return weeklyAverages.map { (weekIndex, avg) ->
        val normalized = range?.let { ((avg - min) / it).toFloat() } ?: 0.5f
        WeekPoint(label = "${weekIndex + 1}주차", value = normalized.coerceIn(0.05f, 1f))
    }
}

// 이번 달 캘린더를 월요일 시작 7열 그리드로 채움. 1일 앞/말일 뒤의 자리 채움 칸만 null(투명)이고,
// 그 달의 날짜는 전부 칸으로 그린다: 일기가 없는 날은 EmptyGray, 있는 날은 그날 대표 감정 색.
// 감정 색은 서버가 emotion_distribution에 주는 hex가 아니라 앱 매핑(emotionColorFor) 하나로 통일한다
// (범례/막대/요약 카드와 같은 기준이어야 서버 색과 앱 색이 달라도 한 화면 안에서 색이 어긋나지 않음).
private fun toDayColors(yearMonth: YearMonth, stats: MonthlyStatsResponse): List<Color?> {
    val flowByDate = stats.emotionFlow.associateBy { it.date }
    val leadingBlanks = yearMonth.atDay(1).dayOfWeek.value - 1
    val cells = mutableListOf<Color?>()
    repeat(leadingBlanks) { cells += null }
    for (day in 1..yearMonth.lengthOfMonth()) {
        val dateStr = yearMonth.atDay(day).format(DateTimeFormatter.ISO_LOCAL_DATE)
        val flowPoint = flowByDate[dateStr]
        cells += when {
            flowPoint == null -> EmptyGray
            else -> emotionColorFor(flowPoint.topEmotion)
        }
    }
    while (cells.size % 7 != 0) cells += null
    return cells
}

private val feltDayFormatter = DateTimeFormatter.ofPattern("M월 d일")
private fun formatFeltDate(dateStr: String?): String =
    dateStr?.let { runCatching { LocalDate.parse(it).format(feltDayFormatter) }.getOrNull() } ?: "-"

// 특정 날짜의 top3_emotions(daily 통계)를 긍정/부정 카드용 막대로 변환. 막대 색은 감정 이름으로 정함.
private fun toFeltEmotionBars(scores: List<EmotionScore>): List<FeltEmotionBar> {
    val total = scores.sumOf { it.score }
    if (scores.isEmpty() || total <= 0) return emptyList()
    return scores.map { item ->
        FeltEmotionBar(
            label = item.emotion,
            percent = (item.score / total * 100).toInt().coerceIn(0, 100),
            color = emotionColorFor(item.emotion)
        )
    }
}

// 감정 색 중 연한 것(안정형 연두, 해소형 민트 등)은 흰 배경에서 윤곽이 묻혀서, 같은 색을 조금 어둡게 한
// 테두리/점에 쓴다.
private fun darkerEmotionColor(color: Color): Color = lerp(color, Color.Black, 0.2f)

// top_companion/top_place의 top3_emotions는 점수 합산값이라 진짜 "횟수"는 아니지만, 배지에 쓸
// 정수가 필요해서 반올림해서 씀 (정확한 횟수가 필요하면 백엔드가 별도 필드로 내려줘야 함).
// 반올림해서 0회가 되는 항목은 배지로 보여줄 의미가 없어서 제외.
// 뱃지 색은 감정 이름으로 정함: 배경은 감정 색을 옅게, 점은 진하게 (글자는 가독성을 위해 검정 유지).
private fun toPills(scores: List<EmotionScore>): List<PillStat> =
    scores.filter { it.score.roundToInt() > 0 }
        .map { item ->
            val color = emotionColorFor(item.emotion)
            PillStat(
                label = item.emotion,
                count = item.score.roundToInt(),
                dotColor = darkerEmotionColor(color),
                bgColor = color.copy(alpha = 0.2f)
            )
        }

private data class EmotionCategory(val label: String, val color: Color)

// 범례 이름은 기존 표기를 유지하고, 색은 EmotionGroup 8그룹 색과 같은 순서로 대응.
private val monthlyEmotionCategories = listOf(
    EmotionCategory("긍정", EmotionGroup.RISING.color),
    EmotionCategory("활력", EmotionGroup.ACTIVE.color),
    EmotionCategory("성취", EmotionGroup.RELIEF.color),
    EmotionCategory("안정", EmotionGroup.STABLE.color),
    EmotionCategory("침체", EmotionGroup.WARY.color),
    EmotionCategory("긴장", EmotionGroup.STAGNANT.color),
    EmotionCategory("고갈", EmotionGroup.DRAINED.color),
    EmotionCategory("분노", EmotionGroup.EXPLOSIVE.color)
)

data class FeltEmotionBar(val label: String, val percent: Int, val color: Color)

data class PillStat(val label: String, val count: Int, val dotColor: Color, val bgColor: Color)

// 화면에 필요한 월간 리포트 값들을 한데 묶는 그릇. GET /stats/monthly 응답 + 가장 긍정/부정적인
// 날의 daily 통계(top3_emotions)를 조합해서 만듦 (toMonthlyReportData 참고)
data class MonthlyReportData(
    val topEmotion: String,
    val topEmotionPercent: Int,
    val topEmotionColor: Color,
    val topEmotions: List<EmotionBar>,
    val weeklyFlow: List<WeekPoint>,
    val flowColor: Color,
    val dayColors: List<Color?>,
    val positiveFeltDate: String,
    val positiveFeltBars: List<FeltEmotionBar>,
    val negativeFeltDate: String,
    val negativeFeltBars: List<FeltEmotionBar>,
    val personLabel: String?,
    val personFeelingHighlight: String,
    val personFeelingColor: Color,
    val personIconColor: Color,
    val personPills: List<PillStat>,
    val placeLabel: String?,
    val placeFeelingHighlight: String,
    val placeFeelingColor: Color,
    val placeIconColor: Color,
    val placePills: List<PillStat>
)

// GET /stats/monthly 응답과, 가장 긍정/부정적인 날 각각의 daily 통계(top3_emotions)를 합쳐서
// 화면이 쓰는 형태로 변환. topCompanion/topPlace가 없으면(그 달에 who/where 기록이 없으면)
// personLabel/placeLabel은 null, 관련 pills는 빈 목록으로 내려감 (화면에서는 안내 문구 카드로 대체)
private fun toMonthlyReportData(
    yearMonth: YearMonth,
    stats: MonthlyStatsResponse,
    positiveDayStats: DailyStatsResponse?,
    negativeDayStats: DailyStatsResponse?
): MonthlyReportData {
    val topBars = toTopEmotionBars(stats.top3Emotions)
    val personTopEmotion = stats.topCompanion?.top3Emotions?.firstOrNull()?.emotion
    val placeTopEmotion = stats.topPlace?.top3Emotions?.firstOrNull()?.emotion
    return MonthlyReportData(
        topEmotion = stats.topEmotion ?: "-",
        topEmotionPercent = topBars.firstOrNull()?.percent ?: 0,
        // 요약 카드 감정 색도 일간/일기 화면과 같은 프론트 매핑(emotionColorFor) 기준
        topEmotionColor = emotionColorFor(stats.topEmotion),
        topEmotions = topBars,
        weeklyFlow = toWeeklyFlow(stats.emotionFlow),
        // 감정 흐름 차트는 그 달 대표 감정 색으로 그림
        flowColor = emotionColorFor(stats.topEmotion),
        dayColors = toDayColors(yearMonth, stats),
        positiveFeltDate = formatFeltDate(stats.mostPositiveDay),
        positiveFeltBars = toFeltEmotionBars(positiveDayStats?.top3Emotions.orEmpty()),
        negativeFeltDate = formatFeltDate(stats.mostNegativeDay),
        negativeFeltBars = toFeltEmotionBars(negativeDayStats?.top3Emotions.orEmpty()),
        personLabel = stats.topCompanion?.name?.ifBlank { null },
        personFeelingHighlight = personTopEmotion ?: "-",
        // "-" 자리표시자로 색을 찾으면 미등록 감정 로그가 찍히므로 원래 값(null 가능)으로 찾음
        personFeelingColor = emotionTextColorFor(personTopEmotion),
        personIconColor = emotionColorFor(personTopEmotion),
        personPills = toPills(stats.topCompanion?.top3Emotions.orEmpty()),
        placeLabel = stats.topPlace?.name?.ifBlank { null },
        placeFeelingHighlight = placeTopEmotion ?: "-",
        placeFeelingColor = emotionTextColorFor(placeTopEmotion),
        placeIconColor = emotionColorFor(placeTopEmotion),
        placePills = toPills(stats.topPlace?.top3Emotions.orEmpty())
    )
}

@Composable
fun AnalysisScreen() {
    var selectedTab by remember { mutableStateOf(ReportTab.DAILY) }
    var selectedDate by remember { mutableStateOf(LocalDate.now()) }
    var selectedMonth by remember { mutableStateOf(YearMonth.now()) }
    var showDatePicker by remember { mutableStateOf(false) }

    var dailyStats by remember { mutableStateOf<DailyStatsResponse?>(null) }
    var dailyLoading by remember { mutableStateOf(true) }
    var dailyError by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(selectedDate) {
        dailyLoading = true
        dailyError = null
        try {
            dailyStats = ApiClient.statsApi.getDailyStats(
                date = selectedDate.format(DateTimeFormatter.ISO_LOCAL_DATE)
            )
        } catch (e: Exception) {
            dailyError = describeLoadError(e)
        } finally {
            dailyLoading = false
        }
    }

    var monthlyStats by remember { mutableStateOf<MonthlyStatsResponse?>(null) }
    var monthlyLoading by remember { mutableStateOf(true) }
    var monthlyError by remember { mutableStateOf<String?>(null) }
    var positiveDayStats by remember { mutableStateOf<DailyStatsResponse?>(null) }
    var negativeDayStats by remember { mutableStateOf<DailyStatsResponse?>(null) }

    LaunchedEffect(selectedMonth) {
        monthlyLoading = true
        monthlyError = null
        positiveDayStats = null
        negativeDayStats = null
        try {
            val stats = ApiClient.statsApi.getMonthlyStats(
                year = selectedMonth.year,
                month = selectedMonth.monthValue
            )
            monthlyStats = stats
            // 가장 긍정/부정적인 날의 감정 breakdown은 월간 API에 없어서, 그 날짜로 daily API를
            // 한 번씩 더 불러옴. 실패해도(예: 그 사이 서버가 끊김) 월간 리포트 전체를 막지는 않음
            stats.mostPositiveDay?.let { date ->
                positiveDayStats = runCatching {
                    ApiClient.statsApi.getDailyStats(date)
                }.getOrNull()
            }
            stats.mostNegativeDay?.let { date ->
                negativeDayStats = runCatching {
                    ApiClient.statsApi.getDailyStats(date)
                }.getOrNull()
            }
        } catch (e: Exception) {
            monthlyError = describeLoadError(e)
        } finally {
            monthlyLoading = false
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            Text(
                text = "나의 감정 리포트",
                style = MaterialTheme.typography.headlineSmall,
                color = TitleBrown,
                modifier = Modifier.fillMaxWidth().padding(top = 49.dp),
                textAlign = TextAlign.Center
            )
        }
        item {
            Spacer(Modifier.height(20.dp))
            ReportTabRow(selectedTab) { selectedTab = it }
        }
        item {
            Spacer(Modifier.height(24.dp))
            if (selectedTab == ReportTab.DAILY) {
                DateNav(
                    dateText = selectedDate.format(analysisDateFormatter),
                    onPrev = { selectedDate = selectedDate.minusDays(1) },
                    onNext = { selectedDate = selectedDate.plusDays(1) },
                    onDateClick = { showDatePicker = true }
                )
            } else {
                DateNav(
                    dateText = selectedMonth.format(analysisMonthFormatter),
                    onPrev = { selectedMonth = selectedMonth.minusMonths(1) },
                    onNext = { selectedMonth = selectedMonth.plusMonths(1) },
                    onDateClick = { showDatePicker = true }
                )
            }
        }

        if (selectedTab == ReportTab.DAILY) {
            when {
                dailyLoading -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "불러오는 중...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                dailyError != null -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "통계를 불러오지 못했어요. (${dailyError})",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                dailyStats?.topEmotion == null -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "이 날 기록된 일기가 없어요.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                else -> {
                    val stats = dailyStats!!
                    val bars = toTopEmotionBars(stats.top3Emotions)
                    item {
                        Spacer(Modifier.height(24.dp))
                        EmotionSummaryCard(
                            titlePrefix = "오늘 가장 많이 느낀 감정은\n",
                            emotion = stats.topEmotion ?: "-",
                            percent = bars.firstOrNull()?.percent ?: 0,
                            rankColors = bars.map { it.color },
                            fontFamily = SCoreDreamFontFamily,
                            // "-" 자리표시자로 색을 찾으면 미등록 감정 로그가 찍히므로 원래 값(null 가능)으로 찾음
                            emotionColor = emotionColorFor(stats.topEmotion)
                        )
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        TopEmotionsBarCard(bars, fontFamily = SCoreDreamFontFamily)
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            // 기록이 없는 쪽 카드는 숨김 (DiaryDetailScreen과 같은 처리) - "기록 없음이에요" 같은 문장 방지
                            val companion = stats.companions.firstOrNull()?.ifBlank { null }
                            val place = stats.places.firstOrNull()?.ifBlank { null }
                            if (companion != null) {
                                PersonPlaceInfoCard(
                                    modifier = Modifier.weight(1f),
                                    iconRes = R.drawable.analysis_person_glyph,
                                    emotionColor = emotionColorFor(stats.topEmotion),
                                    prefix = "오늘 함께한 사람은",
                                    highlight = companion,
                                    fontFamily = SCoreDreamFontFamily
                                )
                            }
                            if (place != null) {
                                PersonPlaceInfoCard(
                                    modifier = Modifier.weight(1f),
                                    iconRes = R.drawable.analysis_location_glyph,
                                    emotionColor = emotionColorFor(stats.topEmotion),
                                    prefix = "오늘 방문한 장소는",
                                    highlight = place,
                                    fontFamily = SCoreDreamFontFamily
                                )
                            }
                        }
                    }
                }
            }
        } else {
            when {
                monthlyLoading -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "불러오는 중...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                monthlyError != null -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "월간 통계를 불러오지 못했어요. (${monthlyError})",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                monthlyStats?.topEmotion == null -> item {
                    Spacer(Modifier.height(24.dp))
                    Text(
                        "이 달에 기록된 일기가 없어요.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = BodyGray,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                else -> {
                    val monthlyReport = toMonthlyReportData(selectedMonth, monthlyStats!!, positiveDayStats, negativeDayStats)
                    item {
                        Spacer(Modifier.height(24.dp))
                        EmotionSummaryCard(
                            titlePrefix = "이번 달 가장 많이 느낀 감정은\n",
                            emotion = monthlyReport.topEmotion,
                            percent = monthlyReport.topEmotionPercent,
                            rankColors = monthlyReport.topEmotions.map { it.color },
                            fontFamily = SCoreDreamFontFamily,
                            emotionColor = monthlyReport.topEmotionColor
                        )
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        TopEmotionsBarCard(monthlyReport.topEmotions, fontFamily = SCoreDreamFontFamily)
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        EmotionFlowCard(monthlyReport.weeklyFlow, lineColor = monthlyReport.flowColor)
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        EmotionDistributionCard(monthlyReport.dayColors)
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        TopFeltDayCard(
                            subtitlePrefix = "가장 긍정적인 감정을 느낀 날은 ",
                            dateHighlight = monthlyReport.positiveFeltDate,
                            // 그날 대표 감정(top3 1위, 막대와 같은 기준) 색을 흰 배경에서 읽히게 대비 처리
                            dateColor = emotionTextColorFor(monthlyReport.positiveFeltBars.firstOrNull()?.label),
                            description = monthlyReport.positiveFeltBars.firstOrNull()?.label?.let { "$it 감정이 가장 많았어요" }
                                ?: "기록된 감정이 없어요",
                            bars = monthlyReport.positiveFeltBars
                        )
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        TopFeltDayCard(
                            subtitlePrefix = "가장 부정적인 감정을 느낀 날은 ",
                            dateHighlight = monthlyReport.negativeFeltDate,
                            dateColor = emotionTextColorFor(monthlyReport.negativeFeltBars.firstOrNull()?.label),
                            description = monthlyReport.negativeFeltBars.firstOrNull()?.label?.let { "$it 감정이 가장 많았어요" }
                                ?: "기록된 감정이 없어요",
                            bars = monthlyReport.negativeFeltBars
                        )
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        val person = monthlyReport.personLabel
                        if (person == null) {
                            PersonPlaceEmptyCard(
                                iconRes = R.drawable.analysis_person_glyph,
                                // 기록이 없어 연관 감정도 없으므로 "감정 없음" 기본색
                                iconColor = emotionColorFor(null),
                                message = "아직 함께한 사람 기록이 없어요"
                            )
                        } else {
                            PersonPlaceCard(
                                iconRes = R.drawable.analysis_person_glyph,
                                iconColor = monthlyReport.personIconColor,
                                highlightPrefix = "가장 많이 함께한 사람은 ",
                                highlight = person,
                                highlightColor = monthlyReport.personFeelingColor,
                                recordLine = "${withJosa(person, Josa.GWA_WA)} 함께했던 기록이에요",
                                feelingPrefix = "${withJosa(person, Josa.EUN_NEUN)} 나에게 ",
                                feelingHighlight = monthlyReport.personFeelingHighlight,
                                feelingColor = monthlyReport.personFeelingColor,
                                feelingSuffix = " 감정을 느끼게 해요",
                                pills = monthlyReport.personPills
                            )
                        }
                    }
                    item {
                        Spacer(Modifier.height(16.dp))
                        val place = monthlyReport.placeLabel
                        if (place == null) {
                            PersonPlaceEmptyCard(
                                iconRes = R.drawable.analysis_location_glyph,
                                // 기록이 없어 연관 감정도 없으므로 "감정 없음" 기본색
                                iconColor = emotionColorFor(null),
                                message = "아직 방문한 장소 기록이 없어요"
                            )
                        } else {
                            PersonPlaceCard(
                                iconRes = R.drawable.analysis_location_glyph,
                                iconColor = monthlyReport.placeIconColor,
                                highlightPrefix = "가장 많이 방문한 장소는 ",
                                highlight = place,
                                highlightColor = monthlyReport.placeFeelingColor,
                                recordLine = "${place}에서 느꼈던 기록이에요",
                                feelingPrefix = "${withJosa(place, Josa.EUN_NEUN)} 나에게 ",
                                feelingHighlight = monthlyReport.placeFeelingHighlight,
                                feelingColor = monthlyReport.placeFeelingColor,
                                feelingSuffix = " 감정을 느끼게 해요",
                                pills = monthlyReport.placePills
                            )
                        }
                    }
                }
            }
        }
    }

    if (showDatePicker) {
        AnalysisDatePickerDialog(
            initialDate = if (selectedTab == ReportTab.DAILY) selectedDate else selectedMonth.atDay(1),
            includeDay = selectedTab == ReportTab.DAILY,
            onConfirm = { picked ->
                if (selectedTab == ReportTab.DAILY) {
                    selectedDate = picked
                } else {
                    selectedMonth = YearMonth.from(picked)
                }
                showDatePicker = false
            },
            onDismiss = { showDatePicker = false }
        )
    }
}

@Composable
private fun ReportTabRow(selected: ReportTab, onSelect: (ReportTab) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center
    ) {
        ReportTab.entries.forEach { tab ->
            val isSelected = tab == selected
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .width(84.dp)
                    .padding(horizontal = 24.dp)
                    .clickable { onSelect(tab) }
            ) {
                Text(
                    text = tab.label,
                    style = MaterialTheme.typography.titleSmall,
                    color = if (isSelected) SolidGreen else TabInactiveGray
                )
                Spacer(Modifier.height(6.dp))
                if (isSelected) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(2.dp)
                            .background(SolidGreen)
                    )
                }
            }
        }
    }
}

@Composable
private fun DateNav(dateText: String, onPrev: () -> Unit, onNext: () -> Unit, onDateClick: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
    ) {
        Row(
            modifier = Modifier.align(Alignment.Center),
            horizontalArrangement = Arrangement.spacedBy(24.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onPrev) {
                Icon(Icons.Filled.KeyboardArrowLeft, contentDescription = "이전 날짜", tint = TitleBrown)
            }
            Text(dateText, style = MaterialTheme.typography.titleMedium, color = TitleBrown)
            IconButton(onClick = onNext) {
                Icon(Icons.Filled.KeyboardArrowRight, contentDescription = "다음 날짜", tint = TitleBrown)
            }
        }
        IconButton(onClick = onDateClick, modifier = Modifier.align(Alignment.CenterEnd)) {
            Icon(Icons.Filled.CalendarMonth, contentDescription = "날짜 선택", tint = TitleBrown)
        }
    }
}


@Composable
private fun EmotionFlowCard(weeklyFlow: List<WeekPoint>, lineColor: Color) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                "감정 흐름",
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily, fontWeight = FontWeight.Bold),
                color = Color.Black
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "이번 달의 감정의 흐름을 살펴보세요",
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                color = BodyGray
            )
            Spacer(Modifier.height(20.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .height(160.dp)
                        .padding(end = 8.dp),
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("좋은 날", style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily), color = BodyGray)
                    Text("평범한 날", style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily), color = BodyGray)
                    Text("안좋은 날", style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily), color = BodyGray)
                }
                val strokeColor = lineColor
                val fillTop = lineColor.copy(alpha = 0.45f)
                val fillBottom = lineColor.copy(alpha = 0f)
                Canvas(
                    modifier = Modifier
                        .weight(1f)
                        .height(160.dp)
                ) {
                    // 그 달에 기록이 1주치 미만이면(주차가 1개뿐이면) 선을 그릴 두 점이 안 나와서 스킵
                    if (weeklyFlow.size < 2) return@Canvas
                    val stepX = size.width / (weeklyFlow.size - 1)
                    // 가장 높은 값이 차트 맨 위까지 꽉 차도록 최댓값 기준으로 정규화
                    val maxValue = weeklyFlow.maxOf { it.value }
                    val points = weeklyFlow.mapIndexed { index, point ->
                        Offset(x = index * stepX, y = size.height * (1 - point.value / maxValue))
                    }
                    val linePath = Path().apply {
                        moveTo(points.first().x, points.first().y)
                        points.drop(1).forEach { lineTo(it.x, it.y) }
                    }
                    val fillPath = Path().apply {
                        addPath(linePath)
                        lineTo(points.last().x, size.height)
                        lineTo(points.first().x, size.height)
                        close()
                    }
                    drawPath(fillPath, brush = Brush.verticalGradient(listOf(fillTop, fillBottom)))
                    drawPath(
                        linePath,
                        color = strokeColor,
                        style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
                    )
                    points.forEach { drawCircle(color = strokeColor, radius = 3.dp.toPx(), center = it) }
                }
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(start = 40.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                weeklyFlow.forEach { point ->
                    Text(
                        point.label,
                        style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                        color = BodyGray
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EmotionDistributionCard(dayColors: List<Color?>) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                "감정 분포",
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily, fontWeight = FontWeight.Bold),
                color = Color.Black
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "이번 달의 감정 흐름을 살펴보세요",
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                color = BodyGray
            )
            Spacer(Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                listOf("월", "화", "수", "목", "금", "토", "일").forEach { dayLabel ->
                    Text(
                        dayLabel,
                        modifier = Modifier.weight(1f),
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                        color = BodyGray
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            dayColors.chunked(7).forEach { week ->
                Row(modifier = Modifier.fillMaxWidth()) {
                    week.forEach { cellColor ->
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .padding(4.dp)
                                // 피그마 실측: w=94.358px, h=57.663px (가로가 더 긴 직사각형)
                                .aspectRatio(94.358f / 57.663f)
                                .background(cellColor ?: Color.Transparent, RoundedCornerShape(8.dp))
                        )
                    }
                    repeat(7 - week.size) {
                        Spacer(Modifier.weight(1f))
                    }
                }
            }
            Spacer(Modifier.height(20.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                monthlyEmotionCategories.forEach { category ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // 연한 색(성취 민트, 안정 연두)이 흰 배경에 묻히지 않게 점을 키우고 진한 테두리를 둠
                        Box(
                            modifier = Modifier
                                .size(12.dp)
                                .background(category.color, CircleShape)
                                .border(1.dp, darkerEmotionColor(category.color), CircleShape)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            category.label,
                            style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                            color = Color.Black
                        )
                    }
                }
            }
        }
    }
}

private val feltBarLabelHorizontalPadding = 10.dp
// 0%여도 그 감정 줄에 막대가 있다는 건 보이도록 남겨두는 아주 짧은 막대 너비
private val feltBarMinWidth = 4.dp
private val feltBarLabelOutsideGap = 6.dp

@Composable
private fun TopFeltDayCard(
    subtitlePrefix: String,
    dateHighlight: String,
    dateColor: Color,
    description: String,
    bars: List<FeltEmotionBar>
) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = buildAnnotatedString {
                    append(subtitlePrefix)
                    withStyle(SpanStyle(color = dateColor, fontWeight = FontWeight.Bold)) {
                        append(dateHighlight)
                    }
                    append("이에요")
                },
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily),
                color = Color.Black
            )
            Spacer(Modifier.height(4.dp))
            Text(
                description,
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                color = BodyGray
            )
            Spacer(Modifier.height(20.dp))
            val maxPercent = bars.maxOfOrNull { it.percent } ?: 0
            val percentStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily, fontWeight = FontWeight.Bold)
            // 주요 감정 세로 막대와 같은 원리: 막대 길이는 비율 그대로(가장 큰 값이 꽉 찬 너비, 0%는 아주
            // 짧은 최소 너비)로 그리고, 퍼센트 글자는 막대 안에 "글자 폭(실측, 글꼴 크기 설정 반영) + 좌우
            // 여백"이 들어갈 때만 안(흰색)에, 아니면 막대 오른쪽 바깥에 회색으로 둔다.
            val textMeasurer = rememberTextMeasurer()
            val density = LocalDensity.current
            val percentTextWidth = remember(percentStyle, density) {
                with(density) { textMeasurer.measure("100%", percentStyle).size.width.toDp() }
            }
            val insideLabelWidth = feltBarLabelHorizontalPadding * 2 + percentTextWidth
            bars.forEach { bar ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        bar.label,
                        modifier = Modifier.width(72.dp),
                        textAlign = TextAlign.End,
                        style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                        color = Color.Black
                    )
                    Spacer(Modifier.width(12.dp))
                    BoxWithConstraints(
                        modifier = Modifier
                            .weight(1f)
                            .height(24.dp)
                    ) {
                        val fullWidth = maxWidth
                        val ratio = if (maxPercent > 0) bar.percent.toFloat() / maxPercent else 0f
                        val barWidth = (fullWidth * ratio).coerceIn(feltBarMinWidth, fullWidth)
                        val labelInside = barWidth >= insideLabelWidth
                        Row(
                            modifier = Modifier.fillMaxHeight(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .width(barWidth)
                                    .fillMaxHeight()
                                    .background(bar.color, RoundedCornerShape(12.dp)),
                                contentAlignment = Alignment.CenterEnd
                            ) {
                                if (labelInside) {
                                    Text(
                                        "${bar.percent}%",
                                        modifier = Modifier.padding(end = feltBarLabelHorizontalPadding),
                                        style = percentStyle,
                                        color = Color.White,
                                        maxLines = 1,
                                        softWrap = false
                                    )
                                }
                            }
                            if (!labelInside) {
                                Spacer(Modifier.width(feltBarLabelOutsideGap))
                                Text(
                                    "${bar.percent}%",
                                    style = percentStyle,
                                    color = BodyGray,
                                    maxLines = 1,
                                    softWrap = false
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// 그 달에 사람/장소 기록이 없을 때 PersonPlaceCard 자리에 쓰는 안내 카드. 월간 리포트는 섹션 순서가
// 고정이라(긍정/부정 카드도 "기록된 감정이 없어요"로 자리를 유지) 카드를 숨기지 않고 문구만 바꾼다.
@Composable
private fun PersonPlaceEmptyCard(iconRes: Int, iconColor: Color, message: String) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            EmotionIconCircle(glyphRes = iconRes, color = iconColor, size = 28.dp)
            Spacer(Modifier.width(8.dp))
            Text(
                message,
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily),
                color = BodyGray
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PersonPlaceCard(
    iconRes: Int,
    iconColor: Color,
    highlightPrefix: String,
    highlight: String,
    highlightColor: Color,
    recordLine: String,
    feelingPrefix: String,
    feelingHighlight: String,
    feelingColor: Color,
    feelingSuffix: String,
    pills: List<PillStat>
) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        color = SurfaceColor,
        shape = RoundedCornerShape(23.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                EmotionIconCircle(glyphRes = iconRes, color = iconColor, size = 28.dp)
                Spacer(Modifier.width(8.dp))
                Text(
                    text = buildAnnotatedString {
                        append(highlightPrefix)
                        withStyle(SpanStyle(color = highlightColor, fontWeight = FontWeight.Bold)) {
                            append(highlight)
                        }
                        // highlight는 사람/장소 이름(사용자 입력)이라 받침에 따라 "예요/이에요"를 고름
                        append(josaFor(highlight, Josa.COPULA))
                    },
                    style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily),
                    color = Color.Black
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                recordLine,
                modifier = Modifier.padding(start = 36.dp),
                style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                color = BodyGray
            )
            Spacer(Modifier.height(16.dp))
            Text(
                text = buildAnnotatedString {
                    append(feelingPrefix)
                    withStyle(SpanStyle(color = feelingColor, fontWeight = FontWeight.Bold)) {
                        append(feelingHighlight)
                    }
                    append(feelingSuffix)
                },
                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = SCoreDreamFontFamily),
                color = Color.Black
            )
            // 0회로 걸러지고 남은 pill이 하나도 없으면(= 모든 항목이 0회였으면) 줄 자체를 숨김.
            if (pills.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    pills.forEach { pill ->
                        Row(
                            modifier = Modifier
                                .background(pill.bgColor, RoundedCornerShape(64.dp))
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(pill.dotColor, CircleShape)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                "${pill.label} ${pill.count}회",
                                style = MaterialTheme.typography.labelSmall.copy(fontFamily = SCoreDreamFontFamily),
                                color = Color.Black
                            )
                        }
                    }
                }
            }
        }
    }
}

private val datePickerItemHeight = 56.dp

// 피그마 "감정리포트_날짜선택"(node 11:961) 팝업 그대로: 연도/월/일 무한 스크롤 휠 피커
// (월간 탭은 일(day) 휠 없이 연도/월만 표시)
@Composable
private fun AnalysisDatePickerDialog(
    initialDate: LocalDate,
    includeDay: Boolean,
    onConfirm: (LocalDate) -> Unit,
    onDismiss: () -> Unit
) {
    var year by remember { mutableStateOf(initialDate.year) }
    var month by remember { mutableStateOf(initialDate.monthValue) }
    var day by remember { mutableStateOf(initialDate.dayOfMonth) }
    val years = remember { ((initialDate.year - 10)..(initialDate.year + 10)).toList() }
    val months = remember { (1..12).toList() }
    val days = remember { (1..31).toList() }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            color = SurfaceColor,
            shape = RoundedCornerShape(32.dp)
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("날짜 선택", style = MaterialTheme.typography.titleMedium, color = TitleBrown)
                Spacer(Modifier.height(16.dp))
                Box(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .fillMaxWidth()
                    ) {
                        HorizontalDivider(color = NavInactiveGray)
                        Spacer(Modifier.height(datePickerItemHeight))
                        HorizontalDivider(color = NavInactiveGray)
                    }
                    Row(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        WheelPicker(
                            items = years,
                            selectedIndex = years.indexOf(year).coerceAtLeast(0),
                            onSelectedIndexChange = { year = years[it] },
                            itemHeight = datePickerItemHeight,
                            infinite = false,
                            modifier = Modifier.width(120.dp)
                        ) { item, selected ->
                            DatePickerWheelLabel("${item}년", selected)
                        }
                        WheelPicker(
                            items = months,
                            selectedIndex = month - 1,
                            onSelectedIndexChange = { month = months[it] },
                            itemHeight = datePickerItemHeight,
                            infinite = true,
                            modifier = Modifier.width(if (includeDay) 84.dp else 100.dp)
                        ) { item, selected ->
                            DatePickerWheelLabel("${item}월", selected)
                        }
                        if (includeDay) {
                            WheelPicker(
                                items = days,
                                selectedIndex = day - 1,
                                onSelectedIndexChange = { day = days[it] },
                                itemHeight = datePickerItemHeight,
                                infinite = true,
                                modifier = Modifier.width(84.dp)
                            ) { item, selected ->
                                DatePickerWheelLabel("${item}일", selected)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(24.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        onClick = onDismiss,
                        color = MonthLabelGray.copy(alpha = 0.15f),
                        shape = RoundedCornerShape(24.dp),
                        modifier = Modifier.weight(1f).height(56.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                            Text("취소", style = MaterialTheme.typography.bodyMedium, color = TitleBrown)
                        }
                    }
                    Surface(
                        onClick = {
                            val lastDayOfMonth = YearMonth.of(year, month).lengthOfMonth()
                            val safeDay = if (includeDay) day.coerceAtMost(lastDayOfMonth) else 1
                            onConfirm(LocalDate.of(year, month, safeDay))
                        },
                        color = ButtonMint,
                        shape = RoundedCornerShape(24.dp),
                        modifier = Modifier.weight(1f).height(56.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                            Text("확인", style = MaterialTheme.typography.bodyMedium, color = Color.White)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DatePickerWheelLabel(text: String, selected: Boolean) {
    Text(
        text,
        style = if (selected) MaterialTheme.typography.titleMedium else MaterialTheme.typography.bodyMedium,
        color = if (selected) TitleBrown else MonthLabelGray
    )
}
