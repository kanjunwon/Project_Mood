package com.gamjungseoga.app.navigation

sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Archive : Screen("archive")
    data object Analysis : Screen("analysis")
    data object Settings : Screen("settings")
    data object EmotionTest : Screen("emotiontest")

    // 일기 작성 플로우 (+ 버튼으로 진입하는 중첩 네비게이션 그래프)
    data object DiaryGraph : Screen("diary")
    data object DiaryDate : Screen("diary/date")
    data object DiaryWhat : Screen("diary/what")
    data object DiaryWhy : Screen("diary/why")
    data object DiaryWho : Screen("diary/who")
    data object DiaryWhen : Screen("diary/when")
    data object DiaryWhere : Screen("diary/where")
    data object DiaryGenerating : Screen("diary/generating")
    data object DiaryComplete : Screen("diary/complete")
}
