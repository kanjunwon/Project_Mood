package com.gamjungseoga.app.screens.archive

import com.gamjungseoga.app.R
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.gamjungseoga.app.components.WheelPicker
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.YearMonth
import java.time.format.DateTimeFormatter

// TODO: 실제 데이터로 교체 (백엔드에서 감정 기록 목록 불러오기)
private data class ArchiveEntry(
    val title: String,
    val date: String,
    val imageRes: Int
)

private val sampleArchiveEntries = listOf(
    ArchiveEntry("행복했던 날", "2026.06.14", R.drawable.archive_happy),
    ArchiveEntry("편안했던 날", "2026.05.10", R.drawable.archive_comfortable),
    ArchiveEntry("후련했던 날", "2026.06.14", R.drawable.archive_relieved),
    ArchiveEntry("즐거웠던 날", "2026.06.04", R.drawable.archive_joyful),
    ArchiveEntry("피곤했던 날", "2026.06.11", R.drawable.archive_tired),
    ArchiveEntry("우울했던 날", "2026.05.23", R.drawable.archive_depressed),
    ArchiveEntry("화났던 날", "2026.06.09", R.drawable.archive_angry),
    ArchiveEntry("불안했던 날", "2026.05.14", R.drawable.archive_anxious)
)

private val archiveHeaderDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM")

@Composable
fun ArchiveScreen() {
    // 날짜 선택은 헤더에 표시되는 라벨만 바꾸고, 목록 자체는 필터링하지 않음
    // (피그마 디자인도 5월/6월 기록이 한 그리드에 같이 보이는 구조 - 실제 월별
    // 페이지네이션은 백엔드 연동 후 붙이기)
    var selectedYearMonth by remember { mutableStateOf(YearMonth.of(2026, 6)) }
    var showDatePicker by remember { mutableStateOf(false) }

    LazyVerticalGrid(
        columns = GridCells.Fixed(3),
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 49.dp, bottom = 24.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalArrangement = Arrangement.spacedBy(25.dp)
    ) {
        item(span = { GridItemSpan(maxLineSpan) }) {
            ArchiveHeader(
                yearMonth = selectedYearMonth,
                onDateClick = { showDatePicker = true }
            )
        }
        items(sampleArchiveEntries) { entry ->
            ArchiveCard(entry)
        }
    }

    if (showDatePicker) {
        ArchiveDatePickerDialog(
            initialYearMonth = selectedYearMonth,
            onConfirm = {
                selectedYearMonth = it
                showDatePicker = false
            },
            onDismiss = { showDatePicker = false }
        )
    }
}

@Composable
private fun ArchiveHeader(yearMonth: YearMonth, onDateClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("나의 감정 서재", style = MaterialTheme.typography.headlineSmall, color = TitleBrown)
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clickable(onClick = onDateClick)
        ) {
            Text(yearMonth.format(archiveHeaderDateFormatter), style = MaterialTheme.typography.bodyMedium, color = TitleBrown)
            Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "날짜 선택", tint = TitleBrown)
        }
    }
}

@Composable
private fun ArchiveCard(entry: ArchiveEntry) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Image(
            painter = painterResource(entry.imageRes),
            contentDescription = entry.title,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(314f / 429f)
                .clip(RoundedCornerShape(9.dp))
        )
        Spacer(Modifier.height(10.dp))
        Text(entry.title, style = MaterialTheme.typography.titleSmall, color = TitleBrown)
        Text(entry.date, style = MaterialTheme.typography.labelSmall, color = MonthLabelGray)
    }
}

private val datePickerItemHeight = 56.dp

@Composable
private fun ArchiveDatePickerDialog(
    initialYearMonth: YearMonth,
    onConfirm: (YearMonth) -> Unit,
    onDismiss: () -> Unit
) {
    var year by remember { mutableStateOf(initialYearMonth.year) }
    var month by remember { mutableStateOf(initialYearMonth.monthValue) }
    val years = remember { ((initialYearMonth.year - 10)..(initialYearMonth.year + 10)).toList() }
    val months = remember { (1..12).toList() }

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
                            modifier = Modifier.width(140.dp)
                        ) { item, selected ->
                            DatePickerWheelLabel("${item}년", selected)
                        }
                        WheelPicker(
                            items = months,
                            selectedIndex = month - 1,
                            onSelectedIndexChange = { month = months[it] },
                            itemHeight = datePickerItemHeight,
                            infinite = true,
                            modifier = Modifier.width(100.dp)
                        ) { item, selected ->
                            DatePickerWheelLabel("${item}월", selected)
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
                        onClick = { onConfirm(YearMonth.of(year, month)) },
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
