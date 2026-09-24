package com.gamjungseoga.app.navigation

sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Archive : Screen("archive")
    data object Analysis : Screen("analysis")
    data object Settings : Screen("settings")
    data object EmotionTest : Screen("emotiontest")

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
