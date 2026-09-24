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
import androidx.lifecycle.viewmodel.compose.viewModel
import com.gamjungseoga.app.components.WheelPicker
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate

private val birthDateWheelItemHeight = 56.dp
private val currentYear = LocalDate.now().year

@Composable
fun BirthDateScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    viewModel: BirthDateViewModel = viewModel()
) {
    val date = viewModel.date
    val years = remember(currentYear) { (1950..currentYear).toList() }
    val months = remember { (1..12).toList() }
    val lastDayOfMonth = remember(date.year, date.monthValue) { date.lengthOfMonth() }
    val days = remember(lastDayOfMonth) { (1..lastDayOfMonth).toList() }

    val saving = viewModel.saveState is BirthDateSaveState.Loading
    val errorMessage = (viewModel.saveState as? BirthDateSaveState.Error)?.message

    Column(modifier = Modifier.fillMaxSize()) {
        SettingsSubScreenTopBar(title = "생년월일 변경", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            WheelPicker(
                items = years,
                selectedIndex = years.indexOf(date.year).coerceAtLeast(0),
                onSelectedIndexChange = { viewModel.setYear(years[it]) },
                itemHeight = birthDateWheelItemHeight,
                infinite = false,
                modifier = Modifier.width(110.dp)
            ) { item, selected ->
                BirthDateWheelLabel("${item}년", selected)
            }
            WheelPicker(
                items = months,
                selectedIndex = date.monthValue - 1,
                onSelectedIndexChange = { viewModel.setMonth(months[it]) },
                itemHeight = birthDateWheelItemHeight,
                infinite = true,
                modifier = Modifier.width(90.dp)
            ) { item, selected ->
                BirthDateWheelLabel("${item}월", selected)
            }
            WheelPicker(
                items = days,
                selectedIndex = (date.dayOfMonth - 1).coerceIn(0, days.lastIndex),
                onSelectedIndexChange = { viewModel.setDayOfMonth(days[it]) },
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
            text = "변경하기",
            onClick = { viewModel.save(onSaved) },
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
