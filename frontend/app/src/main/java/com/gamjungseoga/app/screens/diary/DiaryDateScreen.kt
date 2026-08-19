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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate
import java.time.YearMonth

@Composable
fun DiaryDateScreen(
    initialDate: LocalDate,
    onDateSelected: (LocalDate) -> Unit,
    // TODO: 백엔드 연동 후 선택된 달의 날짜별 기록 썸네일 URL(SD3 생성 이미지 등)을 채워서 전달.
    // 값이 있는 날짜 칸은 이미지로, 없으면 지금처럼 빈 칸(CalendarCellGray)으로 표시됨.
    dayImageUrls: Map<LocalDate, String> = emptyMap()
) {
    var displayedMonth by remember { mutableStateOf(YearMonth.from(initialDate)) }

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
                modifier = Modifier.padding(horizontal = 16.dp),
                onDayClick = onDateSelected,
                dayImageUrls = dayImageUrls
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
    onDayClick: (LocalDate) -> Unit,
    dayImageUrls: Map<LocalDate, String>,
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
                        Column(
                            modifier = Modifier.weight(1f),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(132f / 182f)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(CalendarCellGray)
                                    .clickable { onDayClick(date) }
                            ) {
                                // 백엔드에서 그 날짜의 기록 썸네일 URL을 주면 이미지로, 없으면 빈 칸 그대로
                                val imageUrl = dayImageUrls[date]
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
