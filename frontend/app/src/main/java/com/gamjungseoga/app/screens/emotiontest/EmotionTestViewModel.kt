package com.gamjungseoga.app.screens.emotiontest

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel

class EmotionTestViewModel : ViewModel() {
    var currentIndex by mutableIntStateOf(0)
        private set

    val answers = mutableStateListOf<Int?>().apply {
        addAll(List(emotionTestQuestions.size) { null })
    }

    fun selectAnswer(value: Int) {
        answers[currentIndex] = value
    }

    fun goNext() {
        if (currentIndex < emotionTestQuestions.lastIndex) currentIndex++
    }

    fun goPrev() {
        if (currentIndex > 0) currentIndex--
    }
}
