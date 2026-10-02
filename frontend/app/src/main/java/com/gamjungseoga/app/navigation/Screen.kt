package com.gamjungseoga.app.navigation

sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Archive : Screen("archive")
    data object Analysis : Screen("analysis")
    data object Settings : Screen("settings")
    // forced=true: 회원가입/로그인 직후 검사 미완료라서 강제로 들어온 경우 (뒤로가기로 못 빠져나감).
    // forced=false(기본값): 설정의 "다시하기"로 들어온 경우 (지금처럼 자유롭게 나갈 수 있음).
    data object EmotionTest : Screen("emotiontest?forced={forced}") {
        const val ARG_FORCED = "forced"
        fun routeFor(forced: Boolean) = "emotiontest?forced=$forced"
    }

    // 설정 화면의 "성별 변경" / "직업 변경" / "생년월일 변경" / "비밀번호 변경" 행에서 진입하는 화면
    data object GenderChange : Screen("settings/gender")
    data object JobChange : Screen("settings/job")
    data object BirthDateChange : Screen("settings/birthdate")
    data object PasswordChange : Screen("settings/password")

    // 로그인 / 회원가입 플로우
    data object Login : Screen("login")

    // 회원가입 플로우 (로그인 화면의 "회원가입" 버튼으로 진입하는 중첩 네비게이션 그래프)
    data object SignupGraph : Screen("signup")
    data object SignupEmail : Screen("signup/email")
    data object SignupPassword : Screen("signup/password")
    data object SignupNickname : Screen("signup/nickname")
    data object SignupGender : Screen("signup/gender")
    data object SignupJob : Screen("signup/job")
    data object SignupBirthDate : Screen("signup/birthdate")

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

    // 이미지 커스터마이징 플로우 (설정 화면의 "이미지 커스터마이징 → 변경하기"로 진입하는 중첩 네비게이션 그래프)
    data object ProfileCustomizeGraph : Screen("profile-customize")
    data object ProfileCustomizeGlasses : Screen("profile-customize/glasses")
    data object ProfileCustomizeBangs : Screen("profile-customize/bangs")
    data object ProfileCustomizeHairLength : Screen("profile-customize/hair-length")
    data object ProfileCustomizeHairColor : Screen("profile-customize/hair-color")
    data object ProfileCustomizeComplete : Screen("profile-customize/complete")
}
