package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gamjungseoga.app.components.WheelPicker
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.OmyuPrettyFontFamily
import com.gamjungseoga.app.ui.theme.TitleBrown
import com.gamjungseoga.app.ui.theme.WheelDim
import java.time.LocalDate
import java.time.LocalTime

private val wheelItemHeight = 72.dp
private val amPmItems = listOf("오전", "오후")
private val hourItems = (1..12).toList()
private val minuteItems = (0..59).toList()

@Composable
fun DiaryWhenScreen(
    date: LocalDate,
    time: LocalTime,
    onTimeChange: (LocalTime) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit
) {
    val isAm = time.hour < 12
    val hour12 = when (val h = time.hour % 12) {
        0 -> 12
        else -> h
    }

    fun updateAmPmIndex(index: Int) {
        val am = index == 0
        val newHour24 = if (am) hour12 % 12 else (hour12 % 12) + 12
        onTimeChange(time.withHour(newHour24))
    }

    fun updateHourIndex(index: Int) {
        val newHour12 = hourItems[index]
        val newHour24 = if (isAm) newHour12 % 12 else (newHour12 % 12) + 12
        onTimeChange(time.withHour(newHour24))
    }

    fun updateMinuteIndex(index: Int) {
        onTimeChange(time.withMinute(minuteItems[index]))
    }

    Column(modifier = Modifier.fillMaxSize()) {
        DiaryTopBar(onBack = onBack)
        Spacer(Modifier.height(16.dp))
        DiaryDateLabel(date, modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(16.dp))
        Text(
            "몇시에 있었던 일인가요?",
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
            ) {
                HorizontalDivider(color = NavInactiveGray)
                Spacer(Modifier.height(wheelItemHeight))
                HorizontalDivider(color = NavInactiveGray)
            }
            Row(
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                WheelPicker(
                    items = amPmItems,
                    selectedIndex = if (isAm) 0 else 1,
                    onSelectedIndexChange = ::updateAmPmIndex,
                    itemHeight = wheelItemHeight,
                    modifier = Modifier.width(110.dp)
                ) { item, selected ->
                    WheelLabel(item, selected)
                }
                WheelPicker(
                    items = hourItems,
                    selectedIndex = hourItems.indexOf(hour12),
                    onSelectedIndexChange = ::updateHourIndex,
                    itemHeight = wheelItemHeight,
                    modifier = Modifier.width(80.dp)
                ) { item, selected ->
                    WheelLabel(item.toString(), selected)
                }
                Text(
                    ":",
                    fontFamily = OmyuPrettyFontFamily,
                    fontSize = 36.sp,
                    color = TitleBrown
                )
                WheelPicker(
                    items = minuteItems,
                    selectedIndex = minuteItems.indexOf(time.minute),
                    onSelectedIndexChange = ::updateMinuteIndex,
                    itemHeight = wheelItemHeight,
                    modifier = Modifier.width(80.dp)
                ) { item, selected ->
                    WheelLabel(item.toString().padStart(2, '0'), selected)
                }
            }
        }
        DiaryNextButton(onClick = onNext)
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun WheelLabel(text: String, selected: Boolean) {
    Text(
        text,
        fontFamily = OmyuPrettyFontFamily,
        fontSize = if (selected) 40.sp else 28.sp,
        fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
        color = if (selected) TitleBrown else WheelDim
    )
}
