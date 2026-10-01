package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.components.WheelPicker
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate

private val birthDateWheelItemHeight = 56.dp
private val currentYear = LocalDate.now().year

// 설정의 "생년월일 변경"과 회원가입의 "생년월일" 단계가 공유하는 UI: 상단 뒤로가기+제목,
// 년/월/일 휠 피커 세 개, 하단 버튼. 값 보관과 저장 시점/로직은 호출하는 쪽(ViewModel)이 맡는다.
@Composable
fun BirthDateScreen(
    title: String,
    date: LocalDate,
    onYearChange: (Int) -> Unit,
    onMonthChange: (Int) -> Unit,
    onDayChange: (Int) -> Unit,
    onBack: () -> Unit,
    onConfirm: () -> Unit,
    confirmButtonText: String = "변경하기",
    saving: Boolean = false,
    errorMessage: String? = null
) {
    val years = remember(currentYear) { (1950..currentYear).toList() }
    val months = remember { (1..12).toList() }
    val lastDayOfMonth = remember(date.year, date.monthValue) { date.lengthOfMonth() }
    val days = remember(lastDayOfMonth) { (1..lastDayOfMonth).toList() }

    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = title, onBack = onBack)

        Spacer(Modifier.height(24.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            WheelPicker(
                items = years,
                selectedIndex = years.indexOf(date.year).coerceAtLeast(0),
                onSelectedIndexChange = { onYearChange(years[it]) },
                itemHeight = birthDateWheelItemHeight,
                infinite = false,
                modifier = Modifier.width(110.dp)
            ) { item, selected ->
                BirthDateWheelLabel("${item}년", selected)
            }
            WheelPicker(
                items = months,
                selectedIndex = date.monthValue - 1,
                onSelectedIndexChange = { onMonthChange(months[it]) },
                itemHeight = birthDateWheelItemHeight,
                infinite = true,
                modifier = Modifier.width(90.dp)
            ) { item, selected ->
                BirthDateWheelLabel("${item}월", selected)
            }
            WheelPicker(
                items = days,
                selectedIndex = (date.dayOfMonth - 1).coerceIn(0, days.lastIndex),
                onSelectedIndexChange = { onDayChange(days[it]) },
                itemHeight = birthDateWheelItemHeight,
                infinite = true,
                modifier = Modifier.width(90.dp)
            ) { item, selected ->
                BirthDateWheelLabel("${item}일", selected)
            }
        }

        if (errorMessage != null) {
            Spacer(Modifier.height(16.dp))
            Text(
                errorMessage,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        SettingsPrimaryButton(
            text = confirmButtonText,
            onClick = onConfirm,
            loading = saving,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun BirthDateWheelLabel(text: String, selected: Boolean) {
    Text(
        text,
        style = if (selected) MaterialTheme.typography.titleMedium else MaterialTheme.typography.bodyMedium,
        color = if (selected) TitleBrown else MonthLabelGray
    )
}
