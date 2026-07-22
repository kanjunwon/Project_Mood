package com.gamjungseoga.app.navigation

sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Archive : Screen("archive")
    data object Analysis : Screen("analysis")
    data object Settings : Screen("settings")
}
