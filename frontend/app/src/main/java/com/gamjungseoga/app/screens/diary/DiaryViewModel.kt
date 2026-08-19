package com.gamjungseoga.app.screens.diary

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import java.time.LocalDate
import java.time.LocalTime

data class DiaryDraft(
    val date: LocalDate = LocalDate.now(),
    val what: String = "",
    val why: String = "",
    val who: Set<String> = emptySet(),
    val whoCustom: String = "",
    val time: LocalTime = LocalTime.now(),
    val where: String = ""
)

class DiaryViewModel : ViewModel() {
    var draft by mutableStateOf(DiaryDraft())
        private set

    fun setDate(date: LocalDate) {
        draft = draft.copy(date = date)
    }

    fun setWhat(text: String) {
        draft = draft.copy(what = text)
    }

    fun setWhy(text: String) {
        draft = draft.copy(why = text)
    }

    fun toggleWho(option: String) {
        draft = draft.copy(who = if (option in draft.who) draft.who - option else draft.who + option)
    }

    fun setWhoCustom(text: String) {
        draft = draft.copy(whoCustom = text)
    }

    fun setTime(time: LocalTime) {
        draft = draft.copy(time = time)
    }

    fun setWhere(text: String) {
        draft = draft.copy(where = text)
    }
}
