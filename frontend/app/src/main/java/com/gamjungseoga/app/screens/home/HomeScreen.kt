package com.gamjungseoga.app.screens.home

import com.gamjungseoga.app.R
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import kotlin.math.abs
import com.gamjungseoga.app.emotion.emotionColorFor
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryEntry
import com.gamjungseoga.app.network.SEOUL_ZONE
import com.gamjungseoga.app.network.parseServerDateTimeInSeoul
import com.gamjungseoga.app.screens.diary.DiaryListState
import com.gamjungseoga.app.screens.diary.DiaryListViewModel
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale
import com.gamjungseoga.app.ui.theme.CardBackground
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.FoldBackGray
import com.gamjungseoga.app.ui.theme.GamjeongseogaTheme
import com.gamjungseoga.app.ui.theme.HeaderGreen
import com.gamjungseoga.app.ui.theme.HeaderTextOnGreen
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.PlaceholderNavy
import com.gamjungseoga.app.ui.theme.PlaceholderOcean
import com.gamjungseoga.app.ui.theme.PlaceholderTerracotta
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown

// imageUrl: 백엔드(SD3)가 생성해주는 감정 이미지 URL. 있으면 우선 사용, 없으면 imageRes(샘플 일러스트) 표시
private data class MonthlyEmotion(
    val month: String,
    val emotion: String,
    val count: String,
    // 그 달 대표 감정 색. 카드 장식(테이프/조각/점)을 이 색으로 칠함
    val accentColor: Color,
    val imageRes: Int? = null,
    val imageUrl: String? = null
)

private data class DiaryPage(
    val id: Long,
    val dateTop: String,
    val dateBottom: String,
    val color: Color,
    // 오른쪽 위 책갈피 색 = 그 일기의 감정 색
    val ribbonColor: Color,
    val imageUrl: String? = null,
    val showDateTag: Boolean = false
)

// SD3가 달마다 대표 이미지를 만들어주는 API가 아직 없어서, 카드 장식(마스킹테이프 등)과 마찬가지로
// 이미지는 이 3장을 순서대로 돌려씀. month/emotion/count만 실제 일기 목록에서 계산.
private val monthlyEmotionImageRes = listOf(R.drawable.emotion_card_1, R.drawable.emotion_card_2, R.drawable.emotion_card_3)

// 이번 달 포함 최근 3개월 각각에 대해, 그 달 일기들의 top_emotion 중 가장 많이 나온 감정을
// 대표 감정으로 삼음(최빈값). GET /diaries/{userId}가 이미 각 일기의 top_emotion/created_at을
// 내려주고 있어서 백엔드 추가 연동 없이 프론트에서 바로 집계 가능.
private fun computeMonthlyEmotions(diaries: List<DiaryEntry>): List<MonthlyEmotion> {
    val entriesByMonth = diaries
        .mapNotNull { entry ->
            val created = parseServerDateTimeInSeoul(entry.createdAt)
            created?.let { YearMonth.from(it) to entry }
        }
        .groupBy({ it.first }, { it.second })

    // 일기는 한국 시간 기준으로 묶었으니 "이번 달" 기준도 한국 시간이어야 경계가 어긋나지 않는다.
    val currentMonth = YearMonth.now(SEOUL_ZONE)
    return (0..2).map { monthsAgo ->
        val yearMonth = currentMonth.minusMonths(monthsAgo.toLong())
        val topEmotionCounts = entriesByMonth[yearMonth].orEmpty()
            .mapNotNull { it.topEmotion }
            .groupingBy { it }
            .eachCount()
        val topEmotion = topEmotionCounts.maxByOrNull { it.value }
        // 대표 감정(topEmotion)과 일치하는 그 달 일기 중 imageUrl이 있는 첫 번째 것을 대표 이미지로 삼음.
        // "가장 많이 나온 감정의 일기 중 하나"라 어떤 걸 고르든 상관없어서 순서는 신경 쓰지 않음.
        val representativeImageUrl = topEmotion?.let { (emotionLabel, _) ->
            entriesByMonth[yearMonth].orEmpty()
                .firstOrNull { it.topEmotion == emotionLabel && !it.imageUrl.isNullOrBlank() }
                ?.imageUrl
        }

        MonthlyEmotion(
            month = "${yearMonth.monthValue}월의 감정",
            emotion = topEmotion?.key ?: "기록 없음",
            count = "${topEmotion?.value ?: 0}회 기록",
            // 기록이 없는 달은 "감정 없음" 기본색
            accentColor = emotionColorFor(topEmotion?.key),
            // 그 달에 기록이 없으면 샘플 일러스트도 넣지 않는다 (이미지 영역은 MonthlyEmotionCard에서 배경색만 보이게 처리됨)
            imageRes = if (topEmotion != null) monthlyEmotionImageRes.getOrNull(monthsAgo) else null,
            imageUrl = ApiClient.resolveImageUrl(representativeImageUrl)
        )
    }
}

private val recentPageColors = listOf(PlaceholderOcean, PlaceholderNavy, PlaceholderTerracotta)
private val recentPageDateFormatter = DateTimeFormatter.ofPattern("MMM", Locale.ENGLISH)

// imageUrl이 있으면 DiaryPageCard가 그 위에 실제 이미지를 그리고, 없으면 색상만 순환시켜 카드로 표시.
private fun DiaryEntry.toDiaryPage(index: Int): DiaryPage {
    val created = parseServerDateTimeInSeoul(createdAt)
    return DiaryPage(
        id = id,
        dateTop = created?.format(recentPageDateFormatter)?.uppercase(Locale.ENGLISH) ?: "-",
        dateBottom = created?.dayOfMonth?.toString() ?: "-",
        color = recentPageColors[index % recentPageColors.size],
        ribbonColor = emotionColorFor(topEmotion),
        imageUrl = ApiClient.resolveImageUrl(imageUrl),
        showDateTag = true
    )
}

// 가운데(현재 페이지) 기준 크기, 옆 페이지는 이 크기에서 축소됨
private const val PAGE_CARD_MIN_SCALE = 0.73f
private const val PAGE_CARD_MAX_SCALE = 1f
// 가운데 카드는 화면 폭의 60%, 나머지를 양옆 카드가 나눠 보여줌(피그마 캐러셀 비율).
// 세로는 피그마 카드 비율(258x354)을 유지하되, 남은 세로 공간보다 크면 비율 그대로 같이 줄인다.
private const val PAGE_CARD_WIDTH_FRACTION = 0.6f
private const val PAGE_CARD_ASPECT_RATIO = 258f / 354f
private val PAGE_CARD_SPACING = 8.dp
private val PAGE_CARD_RIBBON_OVERHANG = 6.dp

// 책갈피(리본) 모양: 위/양옆은 각지고, 아래쪽 가운데가 V자로 파인 형태
private class BookmarkRibbonShape(private val notchHeight: Dp) : Shape {
    override fun createOutline(
        size: Size,
        layoutDirection: LayoutDirection,
        density: Density
    ): Outline {
        val notchPx = with(density) { notchHeight.toPx() }
        val path = Path().apply {
            moveTo(0f, 0f)
            lineTo(size.width, 0f)
            lineTo(size.width, size.height)
            lineTo(size.width / 2f, size.height - notchPx)
            lineTo(0f, size.height)
            close()
        }
        return Outline.Generic(path)
    }
}

// LazyRow 스크롤 위치를 기준으로 화면 중앙에 가까울수록 1(확대), 멀수록 0(축소)에 가까운 값 계산
private fun centerScale(listState: LazyListState, index: Int): Float {
    val layoutInfo = listState.layoutInfo
    val itemInfo = layoutInfo.visibleItemsInfo.firstOrNull { it.index == index }
        ?: return PAGE_CARD_MIN_SCALE
    val viewportCenter = (layoutInfo.viewportStartOffset + layoutInfo.viewportEndOffset) / 2f
    val itemCenter = itemInfo.offset + itemInfo.size / 2f
    val distance = abs(itemCenter - viewportCenter)
    val maxDistance = layoutInfo.viewportSize.width / 2f
    val fraction = (1f - (distance / maxDistance)).coerceIn(0f, 1f)
    return PAGE_CARD_MIN_SCALE + (PAGE_CARD_MAX_SCALE - PAGE_CARD_MIN_SCALE) * fraction
}

@Composable
fun HomeScreen(
    diaryListViewModel: DiaryListViewModel = viewModel(),
    onDiaryClick: (Long) -> Unit = {}
) {
    val listState = diaryListViewModel.state
    val recentPages = remember(listState) {
        (listState as? DiaryListState.Loaded)?.diaries
            ?.take(6)
            ?.mapIndexed { index, entry -> entry.toDiaryPage(index) }
            .orEmpty()
    }

    // 배경(바탕색+텍스처)은 MainActivity의 전체 배경 레이어가 담당하므로 여기서는 따로 안 채움.
    // 홈은 세로 스크롤 없이 한 화면에 들어가는 구조: 헤더/나의 감정은 내용만큼, "최근 작성한 페이지"가
    // 남은 높이를 전부 받고 그 안에서 카드 크기를 정한다(카드가 탭바 아래로 밀려 잘리지 않게).
    Column(
        modifier = Modifier.fillMaxSize()
    ) {
        HomeHeader()

        Column(modifier = Modifier.padding(top = 24.dp)) {
            SectionTitle("나의 감정")
            Spacer(Modifier.height(16.dp))
            when {
                listState is DiaryListState.Loading -> Text(
                    "불러오는 중...",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                listState is DiaryListState.Error -> Text(
                    "감정 기록을 불러오지 못했어요. (${listState.message})",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                else -> {
                    val monthlyEmotions = remember(listState) {
                        computeMonthlyEmotions((listState as DiaryListState.Loaded).diaries)
                    }
                    // 카드 3장 고정이라 Lazy 대신 Row로 두고, IntrinsicSize.Min으로 가장 긴 카드에
                    // 높이를 맞춘다(감정 이름이 길어 한 장만 줄바꿈돼도 세 장 높이가 같게).
                    // 세로 padding은 카드 위/아래로 걸치는 장식(테이프/점/파란 조각) 자리.
                    Row(
                        modifier = Modifier
                            .horizontalScroll(rememberScrollState())
                            .height(IntrinsicSize.Min)
                            .padding(horizontal = 16.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(18.dp)
                    ) {
                        monthlyEmotions.forEachIndexed { index, item ->
                            MonthlyEmotionCard(item, index)
                        }
                    }
                }
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(top = 20.dp, bottom = 16.dp)
        ) {
            SectionTitle("최근 작성한 페이지")
            Spacer(Modifier.height(12.dp))
            when {
                listState is DiaryListState.Loading -> Text(
                    "불러오는 중...",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                listState is DiaryListState.Error -> Text(
                    "일기 목록을 불러오지 못했어요. (${listState.message})",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                recentPages.isEmpty() -> Text(
                    "아직 작성한 일기가 없어요.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                else -> {
                    val pagesListState = rememberLazyListState()
                    BoxWithConstraints(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                    ) {
                        val maxCardHeight = (maxHeight - PAGE_CARD_RIBBON_OVERHANG).coerceAtLeast(0.dp)
                        val cardWidth = minOf(maxWidth * PAGE_CARD_WIDTH_FRACTION, maxCardHeight * PAGE_CARD_ASPECT_RATIO)
                        val cardHeight = cardWidth / PAGE_CARD_ASPECT_RATIO
                        // 좌우 여백을 (화면 폭 - 카드 폭)/2로 두면, 어떤 카드든 스크롤 오프셋 0일 때 정중앙에 온다
                        // (첫/마지막 카드도 가운데까지 끌어올 수 있음).
                        val sidePadding = ((maxWidth - cardWidth) / 2).coerceAtLeast(0.dp)
                        // 화면 로드 시 가운데(현재 페이지, index 1)가 뷰포트 정중앙에 오도록 초기 스크롤
                        LaunchedEffect(recentPages) {
                            val centerIndex = (recentPages.size - 1).coerceAtMost(1)
                            pagesListState.scrollToItem(index = centerIndex)
                        }
                        LazyRow(
                            state = pagesListState,
                            contentPadding = PaddingValues(horizontal = sidePadding),
                            horizontalArrangement = Arrangement.spacedBy(PAGE_CARD_SPACING),
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxSize()
                        ) {
                            itemsIndexed(recentPages) { index, page ->
                                DiaryPageCard(
                                    page = page,
                                    index = index,
                                    listState = pagesListState,
                                    baseWidth = cardWidth,
                                    baseHeight = cardHeight,
                                    onClick = { onDiaryClick(page.id) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HomeHeader() {
    // 헤더 배경: 반투명 초록 사각형(rectangle_1) 위에, 날짜/문구/일러스트/접힌 모서리를 겹쳐서 배치
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 178.dp)
            .background(HeaderGreen)
    ) {
        // 우측 하단 접힌 종이 모서리 (header_fold_accent.png 에셋이 투명 배경 없이 흰색으로
        // 내보내져 있어서 흰 삼각형이 비쳐보이는 문제가 있었음 -> 피그마 벡터 좌표 그대로 직접 그림)
        HeaderFoldAccent(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .size(width = 33.dp, height = 26.dp)
        )

        Column(modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 49.dp, bottom = 20.dp)) {
            val today = remember { LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy.MM.dd")) }
            Text(today, color = HeaderTextOnGreen, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(8.dp))
            Text("오늘의 감정을", color = HeaderTextOnGreen, style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(4.dp))
            Text("한 페이지로 남겨보세요", color = HeaderTextOnGreen, style = MaterialTheme.typography.headlineSmall)
        }

        // 우측상단 일러스트 (res/drawable/header_illustration.png)
        Image(
            painter = painterResource(R.drawable.header_illustration),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 57.dp, end = 16.dp)
                .size(width = 92.dp, height = 104.dp)
        )
    }
}

// 피그마 벡터(node 1:118) 좌표 그대로: 뒷면(연한 회색) 삼각형 위에 앞면(진한 초록) 삼각형을 겹쳐
// 종이 모서리가 접힌 듯한 효과를 냄. 87x69 기준 좌표를 0~1 비율로 변환해서 그림.
@Composable
private fun HeaderFoldAccent(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height

        val backPath = Path().apply {
            moveTo(w, h)
            lineTo(0f, h)
            lineTo(w, h * (9f / 69f))
            close()
        }
        drawPath(backPath, color = FoldBackGray)

        val frontPath = Path().apply {
            moveTo(w * (13.1818f / 87f), 0f)
            lineTo(w, h * (9.11322f / 69f))
            lineTo(0f, h)
            close()
        }
        drawPath(frontPath, color = SolidGreen)
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        color = TitleBrown,
        modifier = Modifier.padding(horizontal = 16.dp)
    )
}

// 높이는 114dp 고정이 아니라 최소값: 그림(58dp) 아래 "N월의 감정"/"감정 N회 기록" 두 줄이 글꼴 크기
// 설정과 상관없이 잘리지 않도록 내용만큼 늘어난다. 세 장 높이는 부모 Row(IntrinsicSize.Min)가 맞춰줌.
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MonthlyEmotionCard(item: MonthlyEmotion, index: Int) {
    Box(
        modifier = Modifier
            .width(114.dp)
            .heightIn(min = 114.dp)
            .fillMaxHeight()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(CardBackground)
                .padding(start = 7.dp, top = 8.dp, end = 7.dp, bottom = 8.dp)
        ) {
            // 사진 영역: imageUrl(SD3 생성 결과) 있으면 그걸, 없으면 샘플 일러스트, 둘 다 없으면 배경만
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(58.dp)
            ) {
                if (item.imageUrl != null) {
                    // 로딩 중/실패 시 샘플 일러스트(imageRes)가 있으면 그걸 보여주고, 없으면
                    // 그냥 비워둬서(=카드 배경색만 보임) 깨진 이미지처럼 보이지 않게 함.
                    val fallback = item.imageRes?.let { painterResource(it) }
                    AsyncImage(
                        model = item.imageUrl,
                        contentDescription = item.emotion,
                        contentScale = ContentScale.Crop,
                        placeholder = fallback,
                        error = fallback,
                        modifier = Modifier.fillMaxSize()
                    )
                } else if (item.imageRes != null) {
                    Image(
                        painter = painterResource(item.imageRes),
                        contentDescription = item.emotion,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(item.month, style = MaterialTheme.typography.labelSmall, color = MonthLabelGray)
            Spacer(Modifier.height(2.dp))
            // 감정 이름이 길면 "N회 기록"이 글자 단위로 쪼개져 잘리지 않고 통째로 다음 줄로 내려가게 FlowRow 사용
            FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    item.emotion,
                    style = MaterialTheme.typography.titleSmall,
                    color = TitleBrown,
                    modifier = Modifier.alignByBaseline()
                )
                Text(
                    item.count,
                    style = MaterialTheme.typography.labelSmall,
                    color = CountLabelBrown,
                    maxLines = 1,
                    softWrap = false,
                    modifier = Modifier.alignByBaseline()
                )
            }
        }

        // 카드마다 다른 장식 (마스킹테이프/스티커) 모양은 피그마 그대로, 색은 그 달 대표 감정 색
        when (index) {
            0 -> TapeAccent(item.accentColor)
            1 -> CornerAccents(item.accentColor)
            2 -> DotAccent(item.accentColor)
        }
    }
}

// 장식은 카드 Box 위에 그려서 그림/텍스트보다 앞에 오고, 카드 경계 밖으로 걸치는 부분은 부모 Row의
// 세로 padding(10dp) 안에 들어가게 크기/오프셋을 잡는다.
@Composable
private fun BoxScope.TapeAccent(color: Color) {
    // 카드 상단 가운데에 가로로 붙인 마스킹테이프: 절반은 카드 위, 절반은 카드 밖으로 걸침.
    // 테이프 느낌을 위해 살짝 반투명하게 해서 아래 그림이 비치게 함.
    Box(
        modifier = Modifier
            .align(Alignment.TopCenter)
            .offset(y = (-10).dp)
            .size(width = 90.dp, height = 20.dp)
            .background(color.copy(alpha = 0.9f), RoundedCornerShape(1.dp))
    )
}

@Composable
private fun BoxScope.CornerAccents(color: Color) {
    // 피그마 실측(9.9x57.6px, rotate 39.94deg): 폭 넓은 막대가 아니라 가늘고 긴 조각이
    // 40도 정도 기울어 모서리에 비스듬히 걸쳐있는 모양(사진 모서리 테이프 느낌).
    // 조각 중심이 카드 모서리 꼭짓점에 오도록 오프셋 = -(조각 크기 / 2).
    Box(
        modifier = Modifier
            .align(Alignment.TopStart)
            .offset(x = (-2).dp, y = (-11).dp)
            .size(width = 4.dp, height = 22.dp)
            .graphicsLayer { rotationZ = 40f }
            .background(color, RoundedCornerShape(1.dp))
    )
    Box(
        modifier = Modifier
            .align(Alignment.BottomEnd)
            .offset(x = 2.dp, y = 11.dp)
            .size(width = 4.dp, height = 22.dp)
            .graphicsLayer { rotationZ = 40f }
            .background(color, RoundedCornerShape(1.dp))
    )
}

@Composable
private fun BoxScope.DotAccent(color: Color) {
    // 카드 위쪽 가운데, 상단 경계에 절반 걸치는 스티커 점
    Box(
        modifier = Modifier
            .align(Alignment.TopCenter)
            .offset(y = (-8).dp)
            .size(16.dp)
            .background(color, CircleShape)
    )
}

// baseWidth/baseHeight: 가운데(scale 1)일 때 크기. 홈 화면 남은 공간에서 계산해서 넘겨줌.
@Composable
private fun DiaryPageCard(
    page: DiaryPage,
    index: Int,
    listState: LazyListState,
    baseWidth: Dp,
    baseHeight: Dp,
    onClick: () -> Unit
) {
    // 실제 레이아웃 크기 자체를 바꿔서 이웃 카드가 가려지지 않고 옆으로 밀려나게 함
    val scale = centerScale(listState, index)
    val cardWidth = baseWidth * scale
    val cardHeight = baseHeight * scale

    // 바깥 Box에 책갈피가 튀어나올 여유 공간(overhang)을 위쪽에 미리 확보해둠 (LazyRow가 넘치는 부분을 잘라내는 것 방지)
    Box(
        modifier = Modifier
            .width(cardWidth)
            .height(cardHeight + PAGE_CARD_RIBBON_OVERHANG)
            .clickable(onClick = onClick)
    ) {
        // 실제로 보이는 다이어리 페이지 박스(사진/색상). 바깥 Box 하단에 붙여서
        // 위쪽 overhang 공간은 비워두고 책갈피가 그 공간에 걸치도록 함
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(cardHeight)
                .background(page.color)
        ) {
            // 백엔드가 이미지 URL을 주면 SD3 생성 이미지로, 없으면 위 color가 그대로 보임.
            // 로딩 중이거나 실패해도 AsyncImage는 별도 error/placeholder 없이 아무것도 안 그리므로
            // 뒤에 깔린 color 배경이 그대로 보여 화면이 깨지지 않음 (의도된 동작).
            if (page.imageUrl != null) {
                AsyncImage(
                    model = page.imageUrl,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }
        }

        if (page.showDateTag) {
            // 오른쪽 위 모서리에서 살짝 왼쪽으로, 박스 위쪽 경계보다 위로 튀어나오게 배치
            Surface(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = (-18).dp)
                    .graphicsLayer {
                        // 카드와 같은 비율로 리본도 커지고 작아짐 (오른쪽 위 모서리 기준으로 확대/축소)
                        scaleX = scale
                        scaleY = scale
                        transformOrigin = TransformOrigin(1f, 0f)
                    },
                color = page.ribbonColor,
                shape = BookmarkRibbonShape(notchHeight = 10.dp)
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 14.dp).padding(bottom = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(page.dateTop, color = Color.White, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    Text(page.dateBottom, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Preview(showBackground = true, heightDp = 900)
@Composable
private fun HomeScreenPreview() {
    GamjeongseogaTheme {
        HomeScreen()
    }
}
