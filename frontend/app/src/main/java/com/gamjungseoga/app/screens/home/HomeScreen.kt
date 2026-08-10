package com.gamjungseoga.app.screens.home

import com.gamjungseoga.app.R
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import coil.compose.AsyncImage
import kotlin.math.abs
import com.gamjungseoga.app.ui.theme.AccentBlue
import com.gamjungseoga.app.ui.theme.AccentGreen
import com.gamjungseoga.app.ui.theme.AccentOrange
import com.gamjungseoga.app.ui.theme.GamjeongseogaTheme
import com.gamjungseoga.app.ui.theme.HeaderTextDark
import com.gamjungseoga.app.ui.theme.OnBackgroundColor
import com.gamjungseoga.app.ui.theme.PlaceholderNavy
import com.gamjungseoga.app.ui.theme.PlaceholderOcean
import com.gamjungseoga.app.ui.theme.PlaceholderRose
import com.gamjungseoga.app.ui.theme.PlaceholderSage
import com.gamjungseoga.app.ui.theme.PlaceholderSlate
import com.gamjungseoga.app.ui.theme.PlaceholderTerracotta
import com.gamjungseoga.app.ui.theme.RibbonPink
import com.gamjungseoga.app.ui.theme.TextMuted

// imageUrl: 백엔드(SD3)가 생성해주는 감정 이미지 URL. 아직 없으면 null -> color로 대체 표시
private data class MonthlyEmotion(
    val month: String,
    val emotion: String,
    val count: String,
    val color: Color,
    val imageUrl: String? = null
)

private data class DiaryPage(
    val dateTop: String,
    val dateBottom: String,
    val color: Color,
    val imageUrl: String? = null,
    val showDateTag: Boolean = false
)

// TODO: 실제 데이터로 교체 (감정 분석 결과/SD3 이미지 URL은 백엔드 API 연동 후 채우기)
private val sampleMonthlyEmotions = listOf(
    MonthlyEmotion("6월의 감정", "즐거운", "14회 기록", PlaceholderRose),
    MonthlyEmotion("5월의 감정", "우울한", "14회 기록", PlaceholderSlate),
    MonthlyEmotion("4월의 감정", "편안한", "14회 기록", PlaceholderSage)
)

// "나의 감정" 카드 행 레이아웃 상수 (장식 위치 계산에 사용)
private val MONTHLY_ROW_PADDING = 20.dp
private val MONTHLY_CARD_SIZE = 114.dp
private val MONTHLY_CARD_SPACING = 12.dp

private val sampleDiaryPages = listOf(
    DiaryPage("JUN", "10", PlaceholderOcean, showDateTag = true),
    DiaryPage("JUN", "15", PlaceholderNavy, showDateTag = true),
    DiaryPage("JUN", "20", PlaceholderTerracotta, showDateTag = true)
)

private const val PAGE_CARD_MIN_SCALE = 0.82f
private const val PAGE_CARD_MAX_SCALE = 1.15f
private val PAGE_CARD_BASE_WIDTH = 170.dp
private val PAGE_CARD_BASE_HEIGHT = 270.dp
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
fun HomeScreen() {
    // 배경(바탕색+텍스처)은 MainActivity의 전체 배경 레이어가 담당하므로 여기서는 따로 안 채움
    LazyColumn(
        modifier = Modifier.fillMaxSize()
    ) {
        item { HomeHeader() }

        item {
            Column(modifier = Modifier.padding(top = 24.dp)) {
                SectionTitle("나의 감정")
                Spacer(Modifier.height(12.dp))
                // 장식(테이프/점)들이 카드 사이/위쪽 여백에 떠 있어서, 여유 공간을 위에 확보하고
                // LazyRow 바깥(같은 Box)에 절대좌표로 따로 그림 -> 카드 자체에는 안 붙음
                Box(modifier = Modifier.padding(top = 16.dp)) {
                    LazyRow(
                        contentPadding = PaddingValues(horizontal = MONTHLY_ROW_PADDING),
                        horizontalArrangement = Arrangement.spacedBy(MONTHLY_CARD_SPACING)
                    ) {
                        items(sampleMonthlyEmotions) { MonthlyEmotionCard(it) }
                    }
                    MonthlyEmotionAccents()
                }
            }
        }

        item {
            Column(modifier = Modifier.padding(top = 28.dp, bottom = 20.dp)) {
                SectionTitle("최근 작성한 페이지")
                Spacer(Modifier.height(12.dp))
                val pagesListState = rememberLazyListState()
                LazyRow(
                    state = pagesListState,
                    contentPadding = PaddingValues(horizontal = 40.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    itemsIndexed(sampleDiaryPages) { index, page ->
                        DiaryPageCard(page, index, pagesListState)
                    }
                }
            }
        }
    }
}

@Composable
private fun HomeHeader() {
    // 헤더 배경: 반투명 초록 사각형(rectangle_1) 위에, 우측하단 모서리 장식은
    // 피그마에서 내보낸 이미지(head_angle.png)로 겹쳐서 배치
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 179.dp)
            .background(Color(0xCC577E75))
    ) {
        // 우측 하단 접힌 모서리 장식 (44x36dp, 기존 대비 2배)
        Image(
            painter = painterResource(R.drawable.head_angle),
            contentDescription = null,
            contentScale = ContentScale.FillBounds,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .size(width = 33.dp, height = 27.dp)
        )

        Column(modifier = Modifier.padding(start = 24.dp, end = 24.dp, top = 56.dp, bottom = 28.dp)) {
            // TODO: 오늘 날짜(시스템 날짜)로 교체
            Text("2026.06.04", color = HeaderTextDark, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(10.dp))
            Text("오늘의 감정을", color = HeaderTextDark, style = MaterialTheme.typography.headlineSmall)
            Text("한 페이지로 남겨보세요", color = HeaderTextDark, style = MaterialTheme.typography.headlineSmall)
        }

        // 우측상단 일러스트 (res/drawable/header_illustration.png)
        Image(
            painter = painterResource(R.drawable.header_illustration),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 24.dp, end = 24.dp)
                .size(width = 95.dp, height = 102.dp)
        )
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        color = OnBackgroundColor,
        modifier = Modifier.padding(horizontal = 20.dp)
    )
}

@Composable
private fun MonthlyEmotionCard(item: MonthlyEmotion) {
    Column(modifier = Modifier.width(114.dp)) {
        // 감정 카드의 정사각형 사진 영역(114x114). imageUrl 없으면 item.color 배경이 그대로 보임
        Box(
            modifier = Modifier
                .size(114.dp)
                .background(item.color)
        ) {
            // 백엔드가 이미지 URL을 주면 SD3 생성 이미지로, 없으면 위 color가 그대로 보임
            if (item.imageUrl != null) {
                AsyncImage(
                    model = item.imageUrl,
                    contentDescription = item.emotion,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
        Spacer(Modifier.height(6.dp))
        Text(item.month, style = MaterialTheme.typography.labelSmall, color = TextMuted)
        Spacer(Modifier.height(2.dp))
        Row {
            Text(item.emotion, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(4.dp))
            Text(
                item.count,
                style = MaterialTheme.typography.labelSmall,
                color = TextMuted,
                modifier = Modifier.padding(top = 2.dp)
            )
        }
    }
}

// "나의 감정" 카드 행 위/사이의 빈 공간에 떠 있는 장식들 (피그마 기준 절대 위치, 카드 자체에는 안 붙어있음)
@Composable
private fun BoxScope.MonthlyEmotionAccents() {
    val card1Center = MONTHLY_ROW_PADDING + MONTHLY_CARD_SIZE / 2
    val gap1Center = MONTHLY_ROW_PADDING + MONTHLY_CARD_SIZE + MONTHLY_CARD_SPACING / 2
    val gap2Center = MONTHLY_ROW_PADDING + MONTHLY_CARD_SIZE * 2 + MONTHLY_CARD_SPACING * 3 / 2
    val card3Center = MONTHLY_ROW_PADDING + MONTHLY_CARD_SIZE * 2 + MONTHLY_CARD_SPACING * 2 + MONTHLY_CARD_SIZE / 2

    // 6월 카드 정가운데 위, 기울기 없는 직사각형 (박스 위로 2dp만 살짝 올라옴)
    AccentBar(
        centerX = card1Center,
        y = (-4).dp,
        width = 52.dp,
        height = 8.dp,
        color = AccentOrange,
        rotationDegrees = 0f
    )
    // 6월-5월 카드 사이 위쪽, 파랑 바 (오른쪽으로 6dp 이동, 반대 방향 기울기 45도)
    AccentBar(
        centerX = gap1Center + 13.dp,
        y = 5.dp,
        width = 30.dp,
        height = 4.dp,
        color = AccentBlue,
        rotationDegrees = -45f
    )
    // 5월-4월 카드 사이 아래쪽, 파랑 바
    AccentBar(
        centerX = gap2Center - 12.dp,
        y = MONTHLY_CARD_SIZE - 8.dp,
        width = 30.dp,
        height = 4.dp,
        color = AccentBlue,
        rotationDegrees = -45f
    )
    // 4월 카드 위, 초록 점
    Box(
        modifier = Modifier
            .align(Alignment.TopStart)
            .offset(x = card3Center - 8.dp, y = -8.dp)
            .size(16.dp)
            .background(AccentGreen, CircleShape)
    )
}

@Composable
private fun BoxScope.AccentBar(
    centerX: Dp,
    y: Dp,
    width: Dp,
    height: Dp,
    color: Color,
    rotationDegrees: Float = -18f
) {
    // 장식 바 하나를 실제로 그리는 박스. centerX/y로 위치를, rotationDegrees로 기울기를 받아서
    // 색만 채운 작은 사각형을 그림 (테이프/스티커처럼 보이는 용도)
    Box(
        modifier = Modifier
            .align(Alignment.TopStart)
            .offset(x = centerX - width / 2, y = y)
            .size(width = width, height = height)
            .graphicsLayer { rotationZ = rotationDegrees }
            .background(color, RoundedCornerShape(2.dp))
    )
}

@Composable
private fun DiaryPageCard(page: DiaryPage, index: Int, listState: LazyListState) {
    // 실제 레이아웃 크기 자체를 바꿔서 이웃 카드가 가려지지 않고 옆으로 밀려나게 함
    val scale = centerScale(listState, index)
    val cardWidth = PAGE_CARD_BASE_WIDTH * scale
    val cardHeight = PAGE_CARD_BASE_HEIGHT * scale

    // 바깥 Box에 책갈피가 튀어나올 여유 공간(overhang)을 위쪽에 미리 확보해둠 (LazyRow가 넘치는 부분을 잘라내는 것 방지)
    Box(
        modifier = Modifier
            .width(cardWidth)
            .height(cardHeight + PAGE_CARD_RIBBON_OVERHANG)
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
            // 백엔드가 이미지 URL을 주면 SD3 생성 이미지로, 없으면 위 color가 그대로 보임
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
                color = RibbonPink,
                shape = BookmarkRibbonShape(notchHeight = 10.dp)
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp).padding(bottom = 6.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(page.dateTop, color = Color.White, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
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
