package com.gamjungseoga.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = AccentTeal,
    onPrimary = Color.White,
    secondary = HeaderGreen,
    background = BackgroundColor,
    onBackground = OnBackgroundColor,
    surface = SurfaceColor
)

private val DarkColors = darkColorScheme(
    primary = AccentTeal,
    onPrimary = Color.White,
    secondary = HeaderGreen,
    background = OnBackgroundColor,
    onBackground = BackgroundColor,
    surface = TitleBrown
)

@Composable
fun GamjeongseogaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
