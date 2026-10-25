package com.gamjungseoga.app.screens.archive

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Icon
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.gamjungseoga.app.components.YearMonthPickerDialog
import com.gamjungseoga.app.emotion.drawableForEmotion
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.DiaryEntry
import com.gamjungseoga.app.network.SEOUL_ZONE
import com.gamjungseoga.app.network.parseServerDateTimeInSeoul
import com.gamjungseoga.app.screens.diary.DiaryListState
import com.gamjungseoga.app.screens.diary.DiaryListViewModel
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.YearMonth
import java.time.format.DateTimeFormatter

private val archiveHeaderDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM")
private val archiveCardDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM.dd")

// created_at은 Supabase가 UTC ISO 8601(timestamptz)로 내려줌. 한국 시간 기준 날짜를 보여줘야
// 하므로 parseServerDateTimeInSeoul로 변환한 뒤 포맷한다. 파싱에 실패하면(로그는 그쪽에서 남김)
// 원본 앞 10자리로 대체한다.
private fun formatArchiveDate(createdAt: String?): String {
    if (createdAt == null) return ""
    return parseServerDateTimeInSeoul(createdAt)?.format(archiveCardDateFormatter)
        ?: createdAt.take(10).replace("-", ".")
}

private fun archiveTitle(entry: DiaryEntry): String =
    entry.topEmotion?.let { "${it} 날" } ?: "기록한 날"

// entry의 created_at을 한국 시간 기준으로 파싱해서 선택한 연/월과 같은 달인지 확인
// (파싱 실패한 항목은 어느 달에도 안 걸림)
private fun DiaryEntry.isInMonth(yearMonth: YearMonth): Boolean {
    val created = parseServerDateTimeInSeoul(createdAt) ?: return false
    return YearMonth.from(created) == yearMonth
}

@Composable
fun ArchiveScreen(
    diaryListViewModel: DiaryListViewModel = viewModel(),
    onDiaryClick: (Long) -> Unit = {}
) {
    // 일기는 한국 시간 기준으로 월별 그룹핑되므로, 처음 보여줄 "이번 달"도 한국 시간 기준이어야 한다.
    var selectedYearMonth by remember { mutableStateOf(YearMonth.now(SEOUL_ZONE)) }
    var showDatePicker by remember { mutableStateOf(false) }
    val listState = diaryListViewModel.state
    val monthEntries = remember(listState, selectedYearMonth) {
        (listState as? DiaryListState.Loaded)?.diaries?.filter { it.isInMonth(selectedYearMonth) }.orEmpty()
    }

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
        when (listState) {
            is DiaryListState.Loading -> item(span = { GridItemSpan(maxLineSpan) }) {
                Text("불러오는 중...", style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
            }
            is DiaryListState.Error -> item(span = { GridItemSpan(maxLineSpan) }) {
                Text(
                    "일기 목록을 불러오지 못했어요. (${listState.message})",
                    style = MaterialTheme.typography.bodyMedium,
                    color = BodyGray
                )
            }
            is DiaryListState.Loaded -> {
                if (monthEntries.isEmpty()) {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Text("이 달에 기록한 일기가 없어요.", style = MaterialTheme.typography.bodyMedium, color = MonthLabelGray)
                    }
                } else {
                    items(monthEntries) { entry ->
                        ArchiveCard(entry, onClick = { onDiaryClick(entry.id) })
                    }
                }
            }
        }
    }

    if (showDatePicker) {
        YearMonthPickerDialog(
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
private fun ArchiveCard(entry: DiaryEntry, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clickable(onClick = onClick)
    ) {
        // entry.imageUrl(SD3 생성 이미지)이 있으면 그걸, 없거나 로딩 실패하면 top_emotion 기준
        // 가장 가까운 기존 일러스트로 대체. 로딩 중에도 같은 일러스트를 보여줘서 빈 자리 방지.
        val fallback = painterResource(drawableForEmotion(entry.topEmotion))
        AsyncImage(
            model = ApiClient.resolveImageUrl(entry.imageUrl),
            contentDescription = archiveTitle(entry),
            contentScale = ContentScale.Crop,
            placeholder = fallback,
            error = fallback,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(314f / 429f)
                .clip(RoundedCornerShape(9.dp))
        )
        Spacer(Modifier.height(10.dp))
        Text(archiveTitle(entry), style = MaterialTheme.typography.titleSmall, color = TitleBrown)
        Text(formatArchiveDate(entry.createdAt), style = MaterialTheme.typography.labelSmall, color = MonthLabelGray)
    }
}
