package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryEntry
import com.gamjungseoga.app.network.SEOUL_ZONE
import com.gamjungseoga.app.network.parseServerDateTimeInSeoul
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate
import java.time.YearMonth

// 하루 1개 제한: 날짜 칸에 이미 일기가 있으면 썸네일(있으면)과 그 일기의 id를 들고 있다가,
// 칸을 누르면 작성 플로우 대신 상세 화면으로 보낸다(diaryId로 라우팅).
data class DiaryDayInfo(val diaryId: Long, val imageUrl: String?)

// GET /diaries/me 목록에서 각 일기의 created_at/image_url/id를 뽑아 날짜별 맵으로 변환.
// created_at은 UTC로 내려오므로 한국 시간 기준으로 변환한 뒤 날짜를 뽑아야 캘린더 셀 날짜와
// 맞는다. 같은 날짜에 일기가 여러 개면(이론상 하루 1개 제한으로 생기지 않아야 하지만) 가장
// 최근 것 하나만 쓴다(먼저 만난 것을 우선하고 이후 같은 날짜는 덮어쓰지 않는 방식이라,
// created_at 내림차순으로 미리 정렬해둔다).
fun buildDiaryDayInfo(diaries: List<DiaryEntry>): Map<LocalDate, DiaryDayInfo> {
    val result = LinkedHashMap<LocalDate, DiaryDayInfo>()
    diaries.sortedByDescending { it.createdAt ?: "" }.forEach { entry ->
        val created = parseServerDateTimeInSeoul(entry.createdAt) ?: return@forEach
        val date = created.toLocalDate()
        if (date !in result) {
            result[date] = DiaryDayInfo(diaryId = entry.id, imageUrl = ApiClient.resolveImageUrl(entry.imageUrl))
        }
    }
    return result
}

@Composable
fun DiaryDateScreen(
    initialDate: LocalDate,
    onDateSelected: (LocalDate) -> Unit,
    // 이미 일기가 있는 날짜를 눌렀을 때 호출(작성 플로우 대신 그 일기의 상세 화면으로 이동).
    onExistingDiaryClick: (diaryId: Long) -> Unit,
    // 선택된 달의 날짜별 일기 정보(이미지 URL + id). buildDiaryDayInfo로 채움.
    // 값이 있는 날짜 칸은 이미지로(없으면 빈 칸), 없는 날짜 칸은 빈 칸(CalendarCellGray)으로 표시됨.
    dayDiaryInfo: Map<LocalDate, DiaryDayInfo> = emptyMap()
) {
    var displayedMonth by remember { mutableStateOf(YearMonth.from(initialDate)) }
    // 기기 시간대가 아니라 서버 기준(서울)으로 "오늘"을 판단해야 다른 시간대 기기에서도
    // 기준이 서버 데이터와 어긋나지 않는다.
    val today = remember { LocalDate.now(SEOUL_ZONE) }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            Spacer(Modifier.height(16.dp))
            MonthNavRow(
                displayedMonth = displayedMonth,
                onPrev = { displayedMonth = displayedMonth.minusMonths(1) },
                onNext = { displayedMonth = displayedMonth.plusMonths(1) }
            )
        }
        item {
            Spacer(Modifier.height(20.dp))
            WeekdayHeaderRow()
        }
        item {
            Spacer(Modifier.height(8.dp))
            CalendarGrid(
                month = displayedMonth,
                today = today,
                modifier = Modifier.padding(horizontal = 16.dp),
                onDayClick = onDateSelected,
                onExistingDiaryClick = onExistingDiaryClick,
                dayDiaryInfo = dayDiaryInfo
            )
        }
    }
}

@Composable
private fun MonthNavRow(displayedMonth: YearMonth, onPrev: () -> Unit, onNext: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
    ) {
        Row(
            modifier = Modifier.align(Alignment.Center),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onPrev) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "이전 달", tint = TitleBrown)
            }
            Text(
                "${displayedMonth.year}.${displayedMonth.monthValue.toString().padStart(2, '0')}",
                style = MaterialTheme.typography.titleMedium,
                color = TitleBrown
            )
            IconButton(onClick = onNext) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "다음 달", tint = TitleBrown)
            }
        }
        Icon(
            Icons.Filled.CalendarMonth,
            contentDescription = "달력",
            tint = TitleBrown,
            modifier = Modifier.align(Alignment.CenterEnd)
        )
    }
}

@Composable
private fun WeekdayHeaderRow() {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        listOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun").forEach { label ->
            Text(
                label,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.labelSmall,
                color = CountLabelBrown
            )
        }
    }
}

@Composable
private fun CalendarGrid(
    month: YearMonth,
    today: LocalDate,
    onDayClick: (LocalDate) -> Unit,
    onExistingDiaryClick: (diaryId: Long) -> Unit,
    dayDiaryInfo: Map<LocalDate, DiaryDayInfo>,
    modifier: Modifier = Modifier
) {
    val firstDay = month.atDay(1)
    val leadingEmpty = firstDay.dayOfWeek.value - 1
    val totalDays = month.lengthOfMonth()
    val cells: List<LocalDate?> = List(leadingEmpty) { null } + (1..totalDays).map { month.atDay(it) }

    Column(modifier = modifier) {
        cells.chunked(7).forEach { week ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                week.forEach { date ->
                    if (date != null) {
                        val dayInfo = dayDiaryInfo[date]
                        // 미래 날짜는 서버가 400으로 거부하니(일기를 미리 쓸 수 없음) 클릭을
                        // 막고 흐리게 표시한다. 기준은 기기 시간이 아니라 서울 시간(오늘). 이미
                        // 일기가 있는 날짜는 미래일 수 없으니 이 블록 대상이 아니다.
                        val isFuture = dayInfo == null && date.isAfter(today)
                        Column(
                            modifier = Modifier
                                .weight(1f)
                                .alpha(if (isFuture) 0.4f else 1f),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(132f / 182f)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(CalendarCellGray)
                                    .let {
                                        when {
                                            // 하루 1개 제한: 이미 일기가 있는 날짜는 작성 플로우
                                            // 대신 그 일기 상세 화면으로 보낸다.
                                            dayInfo != null -> it.clickable { onExistingDiaryClick(dayInfo.diaryId) }
                                            isFuture -> it
                                            else -> it.clickable { onDayClick(date) }
                                        }
                                    }
                            ) {
                                // 백엔드에서 그 날짜의 기록 썸네일 URL을 주면 이미지로, 없으면 빈 칸 그대로
                                val imageUrl = dayInfo?.imageUrl
                                if (imageUrl != null) {
                                    AsyncImage(
                                        model = imageUrl,
                                        contentDescription = "${date.dayOfMonth}일 기록 이미지",
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier.fillMaxSize()
                                    )
                                }
                            }
                            // 피그마 실측: 박스 안이 아니라 박스 아래 약 42px(비율 환산) 여백을 두고 숫자 배치
                            Spacer(Modifier.height(6.dp))
                            Text(
                                "${date.dayOfMonth}",
                                style = MaterialTheme.typography.titleSmall,
                                color = SolidGreen
                            )
                        }
                    } else {
                        Spacer(Modifier.weight(1f))
                    }
                }
                repeat(7 - week.size) {
                    Spacer(Modifier.weight(1f))
                }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}
