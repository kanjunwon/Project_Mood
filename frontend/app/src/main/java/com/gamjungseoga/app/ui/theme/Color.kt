package com.gamjungseoga.app.ui.theme

import androidx.compose.ui.graphics.Color

// 피그마 "메인" 화면(완성 디자인, node 554:938) 기준 확정된 색상
val HeaderGreen = Color(0xCC577E75)
val SolidGreen = Color(0xFF577E75)
val HeaderTextOnGreen = Color(0xFFFFFFFF)
val TitleBrown = Color(0xFF6F4B32)
val MonthLabelGray = Color(0xFFACACAC)
val CountLabelBrown = Color(0xFFAE886C)
val CardBackground = Color(0xFFF1F3F0)
val AccentTeal = Color(0xFF3E6B5A)
val NavActiveTeal = Color(0xFF35665A)
val NavInactiveGray = Color(0xFFACACAC)
val RibbonPink = Color(0xFFE4A4C2)
val TextMuted = Color(0xFF8B8B8B)
val TabInactiveGray = Color(0xFF949494)
val BodyGray = Color(0xFF646464)
val BackgroundColor = Color(0xFFF7F7F7)
val SurfaceColor = Color(0xFFFFFFFF)
val OnBackgroundColor = Color(0xFF1C1B1F)

// 감정 카드 위에 올라가는 작은 장식(테이프/스티커) 색상
val AccentOrange = Color(0xFFFABE7D)
val AccentBlue = Color(0xFF79BCE2)
val AccentGreen = Color(0xFFC5E8A8)
val ChartMint = Color(0xFF8CDECE)

// TODO: 아직 실제 사진 에셋으로 확인 못한 "최근 작성한 페이지" 임시 색상
val PlaceholderOcean = Color(0xFF6E8CA0)
val PlaceholderNavy = Color(0xFF16324A)
val PlaceholderTerracotta = Color(0xFFB05A4A)

// 피그마 "감정리포트_월간"(node 50:38) 기준 색상
val AccentPurple = Color(0xFF957AA1)
val AccentNavy = Color(0xFF5071A9)
val AccentTerracotta = Color(0xFFB26D6D)
val EmptyGray = Color(0xFFEDEDED)
val PillPinkBg = Color(0xFFFBF2F6)
val PillGreenBg = Color(0xFFF1FBE9)
val PillOrangeBg = Color(0xFFFFF3E5)
val PillBlueBg = Color(0xFFDFEFF9)
val PillPurpleBg = Color(0xFFD9E3F4)

// 디자이너가 색채심리학 기준으로 확정한 감정 8그룹 색상 (emotion/EmotionAssets.kt의 EmotionGroup이 사용).
// 값은 위 RibbonPink/AccentOrange/ChartMint/AccentGreen/AccentBlue/AccentNavy/AccentPurple/
// AccentTerracotta와 같지만, 그쪽은 장식/버튼에도 쓰이므로 감정용은 따로 둬서 한쪽만 바뀌어도 서로 안 엮이게 함.
val EmotionRising = Color(0xFFE4A4C2)    // 상승형
val EmotionActive = Color(0xFFFABE7D)    // 활동형
val EmotionRelief = Color(0xFF8CDECE)    // 해소형
val EmotionStable = Color(0xFFC5E8A8)    // 안정형
val EmotionWary = Color(0xFF79BCE2)      // 경계형
val EmotionStagnant = Color(0xFF5071A9)  // 침체형
val EmotionDrained = Color(0xFF957AA1)   // 소모형
val EmotionExplosive = Color(0xFFB26D6D) // 폭발형
// 매핑에 없는 감정용. 막대 위에 흰 글씨(퍼센트)가 올라가서 EmptyGray(#EDEDED)는 글씨가 안 보여 한 톤 진하게 둠.
val EmotionUnknown = Color(0xFFACACAC)

// 피그마 "메인" 화면 헤더 접힌 모서리(node 1:118) 뒷면 색상
val FoldBackGray = Color(0xFFF8F8F8)

// 피그마 "일기작성" 플로우 (node 10:444 등) 기준 색상
val ButtonMint = Color(0xFF7A9D92)
val WheelDim = Color(0xFFDFDFDF)
val CalendarCellGray = Color(0xFFD9D9D9)

// 일기 본문(DiaryBodyTextStyle) 글자색
val DiaryBodyGray = Color(0xFF5B5B5B)
