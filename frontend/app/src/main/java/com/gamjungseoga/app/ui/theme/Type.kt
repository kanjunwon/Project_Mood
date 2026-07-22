package com.gamjungseoga.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.gamjungseoga.app.R

// TODO: res/font/omyu_pretty.ttf 파일이 있어야 빌드됨.
// Android Studio에서 res 폴더 우클릭 -> New -> Font Resource File -> 검색창에 "Omyu Pretty" 입력해서
// Google Fonts에서 받으면 res/font/omyu_pretty.ttf로 자동 추가됨 (파일명 다르면 아래 R.font.omyu_pretty도 맞춰서 변경)
val OmyuPrettyFontFamily = FontFamily(
    Font(R.font.omyu_pretty)
)

val Typography = Typography(
    headlineSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp,
        lineHeight = 28.sp
    ),
    titleMedium = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Bold,
        fontSize = 16.sp
    ),
    titleSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Bold,
        fontSize = 14.sp
    ),
    bodyMedium = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp
    ),
    labelSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 11.sp
    )
)
