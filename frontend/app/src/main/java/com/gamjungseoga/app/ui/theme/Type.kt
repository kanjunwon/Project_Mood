package com.gamjungseoga.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.gamjungseoga.app.R

val OmyuPrettyFontFamily = FontFamily(
    Font(R.font.omyu_pretty)
)

val PretendardFontFamily = FontFamily(
    Font(R.font.pretendard_thin, FontWeight.Thin),
    Font(R.font.pretendard_extralight, FontWeight.ExtraLight),
    Font(R.font.pretendard_light, FontWeight.Light),
    Font(R.font.pretendard_regular, FontWeight.Normal),
    Font(R.font.pretendard_medium, FontWeight.Medium),
    Font(R.font.pretendard_semibold, FontWeight.SemiBold),
    Font(R.font.pretendard_bold, FontWeight.Bold),
    Font(R.font.pretendard_extrabold, FontWeight.ExtraBold),
    Font(R.font.pretendard_black, FontWeight.Black)
)

// 피그마 "감정리포트_월간" 본문에서 쓰인 폰트 (S-Core Dream 1~9 웨이트)
val SCoreDreamFontFamily = FontFamily(
    Font(R.font.scdream_thin, FontWeight.Thin),
    Font(R.font.scdream_extralight, FontWeight.ExtraLight),
    Font(R.font.scdream_light, FontWeight.Light),
    Font(R.font.scdream_regular, FontWeight.Normal),
    Font(R.font.scdream_medium, FontWeight.Medium),
    Font(R.font.scdream_bold, FontWeight.Bold),
    Font(R.font.scdream_extrabold, FontWeight.ExtraBold),
    Font(R.font.scdream_heavy, FontWeight(850)),
    Font(R.font.scdream_black, FontWeight.Black)
)

// 피그마 "메인" 화면 기준 확정된 폰트 크기 (Omyu Pretty, 전부 Regular 웨이트)
// 행간은 폰트 크기 + 2sp로 통일 (전체적으로 행간이 너무 빡빡하다는 피드백 반영)
val Typography = Typography(
    headlineSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 24.sp,
        lineHeight = 32.sp
    ),
    titleMedium = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 20.sp,
        lineHeight = 22.sp
    ),
    titleSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 18.sp
    ),
    bodyMedium = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 18.sp
    ),
    labelSmall = TextStyle(
        fontFamily = OmyuPrettyFontFamily,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        lineHeight = 14.sp
    )
)
