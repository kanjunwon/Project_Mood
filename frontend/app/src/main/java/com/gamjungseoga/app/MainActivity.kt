package com.gamjungseoga.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.navigation
import androidx.navigation.NavType
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.gamjungseoga.app.components.BottomNavBar
import com.gamjungseoga.app.navigation.Screen
import com.gamjungseoga.app.network.SessionManager
import com.gamjungseoga.app.network.TokenStore
import com.gamjungseoga.app.network.needsPersonalTest
import com.gamjungseoga.app.screens.analysis.AnalysisScreen
import com.gamjungseoga.app.screens.archive.ArchiveScreen
import com.gamjungseoga.app.screens.auth.LoginScreen
import com.gamjungseoga.app.screens.auth.LoginViewModel
import com.gamjungseoga.app.screens.auth.SignupBirthDateScreen
import com.gamjungseoga.app.screens.auth.SignupEmailScreen
import com.gamjungseoga.app.screens.auth.SignupNicknameScreen
import com.gamjungseoga.app.screens.auth.SignupPasswordScreen
import com.gamjungseoga.app.screens.auth.SignupSubmitState
import com.gamjungseoga.app.screens.auth.SignupViewModel
import com.gamjungseoga.app.screens.diary.DiaryCompleteScreen
import com.gamjungseoga.app.screens.diary.DiaryDateScreen
import com.gamjungseoga.app.screens.diary.DiaryDetailScreen
import com.gamjungseoga.app.screens.diary.DiaryGenerationState
import com.gamjungseoga.app.screens.diary.DiaryGeneratingScreen
import com.gamjungseoga.app.screens.diary.DiaryListState
import com.gamjungseoga.app.screens.diary.DiaryListViewModel
import com.gamjungseoga.app.screens.diary.DiaryQuestionScreen
import com.gamjungseoga.app.screens.diary.DiaryViewModel
import com.gamjungseoga.app.screens.diary.DiaryWhenScreen
import com.gamjungseoga.app.screens.diary.DiaryWhoScreen
import com.gamjungseoga.app.screens.diary.buildDayImageUrls
import com.gamjungseoga.app.screens.emotiontest.EmotionTestScreen
import com.gamjungseoga.app.screens.emotiontest.EmotionTestSubmitState
import com.gamjungseoga.app.screens.emotiontest.EmotionTestViewModel
import com.gamjungseoga.app.screens.emotiontest.emotionTestQuestions
import com.gamjungseoga.app.screens.home.HomeScreen
import com.gamjungseoga.app.screens.profilecustomize.ProfileCustomizeCompleteScreen
import com.gamjungseoga.app.screens.profilecustomize.ProfileCustomizeSaveState
import com.gamjungseoga.app.screens.profilecustomize.ProfileCustomizeStepScreen
import com.gamjungseoga.app.screens.profilecustomize.ProfileCustomizeViewModel
import com.gamjungseoga.app.screens.profilecustomize.bangsOptions
import com.gamjungseoga.app.screens.profilecustomize.glassesOptions
import com.gamjungseoga.app.screens.profilecustomize.hairColorOptions
import com.gamjungseoga.app.screens.profilecustomize.hairLengthOptions
import com.gamjungseoga.app.screens.profilecustomize.profileCustomizeOptionLabel
import com.gamjungseoga.app.screens.settings.BirthDateChangeScreen
import com.gamjungseoga.app.screens.settings.ChipSelectScreen
import com.gamjungseoga.app.screens.settings.GenderScreen
import com.gamjungseoga.app.screens.settings.JobScreen
import com.gamjungseoga.app.screens.settings.PasswordChangeScreen
import com.gamjungseoga.app.screens.settings.PrivacyPolicyScreen
import com.gamjungseoga.app.screens.settings.SettingsScreen
import com.gamjungseoga.app.screens.settings.TermsOfServiceScreen
import com.gamjungseoga.app.screens.settings.SettingsViewModel
import com.gamjungseoga.app.screens.settings.genderOptions
import com.gamjungseoga.app.screens.settings.jobOptions
import com.gamjungseoga.app.ui.theme.BackgroundColor
import com.gamjungseoga.app.ui.theme.GamjeongseogaTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            GamjeongseogaTheme {
                GamjeongseogaApp()
            }
        }
    }
}

@Composable
fun GamjeongseogaApp() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()

    // 토큰 확인(SharedPreferences 읽기)은 동기적으로 거의 즉시 끝나므로, NavHost가 첫 프레임을
    // 그리기 전에 시작 화면을 한 번만 정해둔다. 그래서 "홈으로 시작했다가 로그인으로 바뀌는"
    // 깜빡임 없이 바로 올바른 화면으로 시작한다.
    val startDestination = remember {
        if (TokenStore.getToken() != null) Screen.Home.route else Screen.Login.route
    }
    val currentRoute = backStackEntry?.destination?.route ?: startDestination

    // 로그인 화면/회원가입 플로우에서는 로그인하지 않은 사용자가 하단 탭으로 홈/설정 등에
    // 접근할 수 없도록 탭바 자체를 그리지 않는다.
    val hideBottomBar = currentRoute == Screen.Login.route ||
        currentRoute.startsWith(Screen.SignupGraph.route)

    // refresh token이 없어 401이 뜨면 재로그인이 필요함. SessionManager가 신호를 보내면
    // 백스택을 모두 비우고 로그인 화면으로 이동시킨다.
    LaunchedEffect(navController) {
        SessionManager.unauthorized.collect {
            navController.navigate(Screen.Login.route) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    // 앱을 켤 때 이미 토큰이 있으면(= 홈으로 바로 시작) 퍼스널 검사 완료 여부 확인 때문에 시작이
    // 느려지면 안 되므로, 일단 홈을 그대로 보여주고 백그라운드에서 상태만 확인한다. 미완료면
    // 그제서야 강제 검사 화면으로 이동시킨다 (Unit 키라 앱 세션당 한 번만 실행됨).
    LaunchedEffect(Unit) {
        if (TokenStore.getToken() != null && needsPersonalTest()) {
            navController.navigate(Screen.EmotionTest.routeFor(forced = true)) {
                launchSingleTop = true
            }
        }
    }

    // 앱 전체 배경: 바탕색 위에 화면(박스들)을 올리고, 맨 위에 종이 질감을 반투명 오버레이로 얹음.
    // (Multiply 블렌드는 밝은 배경 위에서 거의 안 보여서 일반 알파 블렌드로 변경)
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundColor)
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            bottomBar = {
                if (!hideBottomBar) {
                    BottomNavBar(
                        currentRoute = currentRoute,
                        onNavigate = { route ->
                            navController.navigate(route) {
                                if (currentRoute.startsWith(Screen.DiaryGraph.route)) {
                                    // 일기작성 플로우(중첩 그래프) 안에서 하단 탭을 누른 경우:
                                    // saveState/restoreState 조합이 형제 그래프로 못 빠져나오는
                                    // 경우가 있어, 스택을 통째로 비우고 새로 진입한다.
                                    popUpTo(navController.graph.id) { inclusive = true }
                                } else {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    restoreState = true
                                }
                                launchSingleTop = true
                            }
                        },
                        onAddClick = {
                            navController.navigate(Screen.DiaryGraph.route)
                        }
                    )
                }
            }
        ) { innerPadding ->
            NavHost(
                navController = navController,
                startDestination = startDestination,
                modifier = Modifier.padding(innerPadding)
            ) {
                composable(Screen.Home.route) {
                    HomeScreen(
                        onDiaryClick = { diaryId -> navController.navigate(Screen.DiaryDetail.routeFor(diaryId)) }
                    )
                }
                composable(Screen.Archive.route) {
                    ArchiveScreen(
                        onDiaryClick = { diaryId -> navController.navigate(Screen.DiaryDetail.routeFor(diaryId)) }
                    )
                }
                composable(
                    route = Screen.DiaryDetail.route,
                    arguments = listOf(
                        navArgument(Screen.DiaryDetail.ARG_DIARY_ID) { type = NavType.LongType }
                    )
                ) { entry ->
                    val diaryId = entry.arguments?.getLong(Screen.DiaryDetail.ARG_DIARY_ID) ?: -1L
                    DiaryDetailScreen(
                        diaryId = diaryId,
                        onBack = { navController.popBackStack() }
                    )
                }
                composable(Screen.Analysis.route) { AnalysisScreen() }
                composable(Screen.Settings.route) {
                    SettingsScreen(
                        onEmotionTestClick = { navController.navigate(Screen.EmotionTest.routeFor(forced = false)) },
                        onProfileCustomizeClick = { navController.navigate(Screen.ProfileCustomizeGraph.route) },
                        onGenderChangeClick = { navController.navigate(Screen.GenderChange.route) },
                        onJobChangeClick = { navController.navigate(Screen.JobChange.route) },
                        onBirthDateChangeClick = { navController.navigate(Screen.BirthDateChange.route) },
                        onPasswordChangeClick = { navController.navigate(Screen.PasswordChange.route) },
                        onPrivacyPolicyClick = { navController.navigate(Screen.PrivacyPolicy.route) },
                        onTermsOfServiceClick = { navController.navigate(Screen.TermsOfService.route) },
                        onLoggedOut = {
                            navController.navigate(Screen.Login.route) {
                                popUpTo(navController.graph.id) { inclusive = true }
                                launchSingleTop = true
                            }
                        }
                    )
                }
                composable(Screen.GenderChange.route) { entry ->
                    val settingsViewModel = entry.sharedSettingsViewModel(navController)
                    GenderScreen(
                        onBack = { navController.popBackStack() },
                        onSaved = {
                            // 값이 바뀌었으니 설정 화면으로 돌아갔을 때 최신 계정 정보가 보이도록 다시 불러옴.
                            settingsViewModel.loadAccount()
                            navController.popBackStack()
                        }
                    )
                }
                composable(Screen.JobChange.route) { entry ->
                    val settingsViewModel = entry.sharedSettingsViewModel(navController)
                    JobScreen(
                        onBack = { navController.popBackStack() },
                        onSaved = {
                            settingsViewModel.loadAccount()
                            navController.popBackStack()
                        }
                    )
                }
                composable(Screen.BirthDateChange.route) { entry ->
                    val settingsViewModel = entry.sharedSettingsViewModel(navController)
                    BirthDateChangeScreen(
                        onBack = { navController.popBackStack() },
                        onSaved = {
                            settingsViewModel.loadAccount()
                            navController.popBackStack()
                        }
                    )
                }
                composable(Screen.PasswordChange.route) {
                    PasswordChangeScreen(
                        onBack = { navController.popBackStack() },
                        onSaved = { navController.popBackStack() }
                    )
                }
                composable(Screen.PrivacyPolicy.route) {
                    PrivacyPolicyScreen(onBack = { navController.popBackStack() })
                }
                composable(Screen.TermsOfService.route) {
                    TermsOfServiceScreen(onBack = { navController.popBackStack() })
                }
                composable(Screen.Login.route) {
                    LoginScreen(
                        onSignupClick = { navController.navigate(Screen.SignupGraph.route) },
                        onLoginSuccess = { needsPersonalTest ->
                            // 로그인 성공 후 뒤로가기로 로그인 화면에 돌아올 수 없도록 백스택을 비운다.
                            // 퍼스널 검사를 아직 안 했으면 홈 대신 강제 검사 화면으로 보낸다.
                            val destination = if (needsPersonalTest) {
                                Screen.EmotionTest.routeFor(forced = true)
                            } else {
                                Screen.Home.route
                            }
                            navController.navigate(destination) {
                                popUpTo(navController.graph.id) { inclusive = true }
                                launchSingleTop = true
                            }
                        }
                    )
                }
                composable(
                    route = Screen.EmotionTest.route,
                    arguments = listOf(
                        navArgument(Screen.EmotionTest.ARG_FORCED) {
                            type = NavType.BoolType
                            defaultValue = false
                        }
                    )
                ) { entry ->
                    val forced = entry.arguments?.getBoolean(Screen.EmotionTest.ARG_FORCED) ?: false
                    val emotionTestViewModel: EmotionTestViewModel = viewModel()
                    val submitState = emotionTestViewModel.submitState

                    // 강제 진입과 설정 "다시하기"는 전송 로직이 완전히 같고, 성공했을 때 어디로
                    // 이동하느냐만 다르다: 강제 진입은 홈으로 백스택을 비우고, 설정에서 들어온
                    // 경우는 그냥 설정 화면으로 돌아간다(popBackStack).
                    val onSubmitSuccess: () -> Unit = {
                        if (forced) {
                            navController.navigate(Screen.Home.route) {
                                popUpTo(navController.graph.id) { inclusive = true }
                                launchSingleTop = true
                            }
                        } else {
                            navController.popBackStack()
                        }
                    }

                    EmotionTestScreen(
                        index = emotionTestViewModel.currentIndex,
                        total = emotionTestQuestions.size,
                        question = emotionTestQuestions[emotionTestViewModel.currentIndex],
                        selectedAnswer = emotionTestViewModel.answers[emotionTestViewModel.currentIndex],
                        onAnswerSelected = { value ->
                            emotionTestViewModel.selectAnswer(value)
                            if (emotionTestViewModel.currentIndex == emotionTestQuestions.lastIndex) {
                                // 전송 결과를 기다렸다가 성공했을 때만 이동한다 (실패하면 에러 +
                                // 재시도 버튼을 화면이 보여줌 - 강제/설정 진입 모두 동일).
                                emotionTestViewModel.submit(onSuccess = onSubmitSuccess)
                            } else {
                                emotionTestViewModel.goNext()
                            }
                        },
                        // 강제 진입이면 뒤로가기 버튼을 숨기고(onBack = null) 시스템 뒤로가기도 막는다.
                        onBack = if (forced) null else { { navController.popBackStack() } },
                        onPrev = emotionTestViewModel::goPrev,
                        onNext = emotionTestViewModel::goNext,
                        blockSystemBack = forced,
                        isSubmitting = submitState is EmotionTestSubmitState.Submitting,
                        submitError = (submitState as? EmotionTestSubmitState.Error)?.message,
                        onRetrySubmit = { emotionTestViewModel.submit(onSuccess = onSubmitSuccess) }
                    )
                }

                navigation(startDestination = Screen.SignupEmail.route, route = Screen.SignupGraph.route) {
                    composable(Screen.SignupEmail.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        SignupEmailScreen(
                            email = signupViewModel.draft.email,
                            onEmailChange = signupViewModel::setEmail,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.SignupPassword.route) }
                        )
                    }
                    composable(Screen.SignupPassword.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        SignupPasswordScreen(
                            password = signupViewModel.draft.password,
                            passwordConfirm = signupViewModel.draft.passwordConfirm,
                            onPasswordChange = signupViewModel::setPassword,
                            onPasswordConfirmChange = signupViewModel::setPasswordConfirm,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.SignupNickname.route) }
                        )
                    }
                    composable(Screen.SignupNickname.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        SignupNicknameScreen(
                            nickname = signupViewModel.draft.nickname,
                            onNicknameChange = signupViewModel::setNickname,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.SignupGender.route) }
                        )
                    }
                    composable(Screen.SignupGender.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        ChipSelectScreen(
                            title = "성별",
                            options = genderOptions,
                            selected = signupViewModel.draft.gender,
                            onSelectOption = signupViewModel::setGender,
                            onBack = { navController.popBackStack() },
                            onSave = { navController.navigate(Screen.SignupJob.route) },
                            saving = false,
                            errorMessage = null,
                            buttonText = "다음으로"
                        )
                    }
                    composable(Screen.SignupJob.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        ChipSelectScreen(
                            title = "직업",
                            options = jobOptions,
                            selected = signupViewModel.draft.job,
                            onSelectOption = signupViewModel::setJob,
                            onBack = { navController.popBackStack() },
                            onSave = { navController.navigate(Screen.SignupBirthDate.route) },
                            saving = false,
                            errorMessage = null,
                            buttonText = "다음으로"
                        )
                    }
                    composable(Screen.SignupBirthDate.route) { entry ->
                        val signupViewModel: SignupViewModel = entry.sharedSignupViewModel(navController)
                        val loginViewModel = entry.sharedLoginViewModel(navController)
                        SignupBirthDateScreen(
                            date = signupViewModel.draft.birthDate,
                            onYearChange = signupViewModel::setBirthYear,
                            onMonthChange = signupViewModel::setBirthMonth,
                            onDayChange = signupViewModel::setBirthDay,
                            onBack = { navController.popBackStack() },
                            onConfirm = {
                                signupViewModel.submitSignup(
                                    onSuccess = {
                                        navController.popBackStack(Screen.Login.route, inclusive = false)
                                    },
                                    onPartialFailure = {
                                        loginViewModel.showNotice(
                                            "계정은 생성되었지만 일부 정보 저장에 실패했어요. 설정에서 다시 입력해주세요."
                                        )
                                        navController.popBackStack(Screen.Login.route, inclusive = false)
                                    }
                                )
                            },
                            saving = signupViewModel.submitState is SignupSubmitState.Loading,
                            errorMessage = (signupViewModel.submitState as? SignupSubmitState.Error)?.message
                        )
                    }
                }

                navigation(startDestination = Screen.DiaryDate.route, route = Screen.DiaryGraph.route) {
                    composable(Screen.DiaryDate.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        // 날짜 셀 썸네일용으로 일기 목록을 따로 불러옴 (Home/Archive와 같은
                        // DiaryListViewModel 재사용 - 이 화면 전용 상태는 따로 둘 필요가 없음).
                        val diaryListViewModel: DiaryListViewModel = viewModel()
                        val diaryListState = diaryListViewModel.state
                        val dayImageUrls = remember(diaryListState) {
                            buildDayImageUrls((diaryListState as? DiaryListState.Loaded)?.diaries.orEmpty())
                        }
                        DiaryDateScreen(
                            initialDate = diaryViewModel.draft.date,
                            onDateSelected = { date ->
                                diaryViewModel.setDate(date)
                                navController.navigate(Screen.DiaryWhat.route)
                            },
                            dayImageUrls = dayImageUrls
                        )
                    }
                    composable(Screen.DiaryWhat.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryQuestionScreen(
                            date = diaryViewModel.draft.date,
                            question = "오늘 가장 기억에 남는 일은\n무엇인가요?",
                            answer = diaryViewModel.draft.what,
                            onAnswerChange = diaryViewModel::setWhat,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.DiaryWhy.route) }
                        )
                    }
                    composable(Screen.DiaryWhy.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryQuestionScreen(
                            date = diaryViewModel.draft.date,
                            question = "그 일이 왜 가장\n기억에 남았나요?",
                            answer = diaryViewModel.draft.why,
                            onAnswerChange = diaryViewModel::setWhy,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.DiaryWho.route) }
                        )
                    }
                    composable(Screen.DiaryWho.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryWhoScreen(
                            date = diaryViewModel.draft.date,
                            selected = diaryViewModel.draft.who,
                            customText = diaryViewModel.draft.whoCustom,
                            onToggle = diaryViewModel::toggleWho,
                            onCustomTextChange = diaryViewModel::setWhoCustom,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.DiaryWhen.route) }
                        )
                    }
                    composable(Screen.DiaryWhen.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryWhenScreen(
                            date = diaryViewModel.draft.date,
                            time = diaryViewModel.draft.time,
                            onTimeChange = diaryViewModel::setTime,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.DiaryWhere.route) }
                        )
                    }
                    composable(Screen.DiaryWhere.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryQuestionScreen(
                            date = diaryViewModel.draft.date,
                            question = "어디서 있었던\n일인가요?",
                            answer = diaryViewModel.draft.where,
                            onAnswerChange = diaryViewModel::setWhere,
                            onBack = { navController.popBackStack() },
                            onNext = { navController.navigate(Screen.DiaryGenerating.route) }
                        )
                    }
                    composable(Screen.DiaryGenerating.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        DiaryGeneratingScreen(
                            diaryViewModel = diaryViewModel,
                            onComplete = {
                                navController.navigate(Screen.DiaryComplete.route) {
                                    popUpTo(Screen.DiaryDate.route) { inclusive = true }
                                }
                            },
                            onExit = {
                                navController.navigate(Screen.Home.route) {
                                    popUpTo(navController.graph.id) { inclusive = true }
                                    launchSingleTop = true
                                }
                            }
                        )
                    }
                    composable(Screen.DiaryComplete.route) { entry ->
                        val diaryViewModel: DiaryViewModel = entry.sharedDiaryViewModel(navController)
                        val generationState = diaryViewModel.generationState
                        DiaryCompleteScreen(
                            draft = diaryViewModel.draft,
                            result = (generationState as? DiaryGenerationState.Success)?.response,
                            onBack = {
                                navController.navigate(Screen.Home.route) {
                                    popUpTo(navController.graph.id) { inclusive = true }
                                    launchSingleTop = true
                                }
                            }
                        )
                    }
                }

                navigation(
                    startDestination = Screen.ProfileCustomizeGlasses.route,
                    route = Screen.ProfileCustomizeGraph.route
                ) {
                    composable(Screen.ProfileCustomizeGlasses.route) { entry ->
                        val viewModel = entry.sharedProfileCustomizeViewModel(navController)
                        ProfileCustomizeStepScreen(
                            step = 1,
                            totalSteps = 4,
                            question = "어떤 안경을\n착용하고 있나요?",
                            options = glassesOptions,
                            selectedCode = viewModel.draft.glasses,
                            optionsEnabled = true,
                            onSelectOption = { code ->
                                viewModel.setGlasses(code)
                                navController.navigate(Screen.ProfileCustomizeBangs.route)
                            },
                            onBack = { navController.popBackStack() },
                            onPrevStep = null,
                            onNextStep = viewModel.draft.glasses?.let {
                                { navController.navigate(Screen.ProfileCustomizeBangs.route) }
                            }
                        )
                    }
                    composable(Screen.ProfileCustomizeBangs.route) { entry ->
                        val viewModel = entry.sharedProfileCustomizeViewModel(navController)
                        ProfileCustomizeStepScreen(
                            step = 2,
                            totalSteps = 4,
                            question = "헤어스타일은\n어떤가요?",
                            options = bangsOptions,
                            selectedCode = viewModel.draft.bangs?.toString(),
                            optionsEnabled = true,
                            onSelectOption = { code ->
                                viewModel.setBangs(code.toBoolean())
                                navController.navigate(Screen.ProfileCustomizeHairLength.route)
                            },
                            onBack = { navController.popBackStack() },
                            onPrevStep = { navController.popBackStack() },
                            onNextStep = viewModel.draft.bangs?.let {
                                { navController.navigate(Screen.ProfileCustomizeHairLength.route) }
                            }
                        )
                    }
                    composable(Screen.ProfileCustomizeHairLength.route) { entry ->
                        val viewModel = entry.sharedProfileCustomizeViewModel(navController)
                        ProfileCustomizeStepScreen(
                            step = 3,
                            totalSteps = 4,
                            question = "머리 길이는\n어떤가요?",
                            options = hairLengthOptions,
                            selectedCode = viewModel.draft.hairLength,
                            optionsEnabled = true,
                            onSelectOption = { code ->
                                viewModel.setHairLength(code)
                                navController.navigate(Screen.ProfileCustomizeHairColor.route)
                            },
                            onBack = { navController.popBackStack() },
                            onPrevStep = { navController.popBackStack() },
                            onNextStep = viewModel.draft.hairLength?.let {
                                { navController.navigate(Screen.ProfileCustomizeHairColor.route) }
                            }
                        )
                    }
                    composable(Screen.ProfileCustomizeHairColor.route) { entry ->
                        val viewModel = entry.sharedProfileCustomizeViewModel(navController)
                        ProfileCustomizeStepScreen(
                            step = 4,
                            totalSteps = 4,
                            question = "머리 색은\n어떤 색인가요?",
                            options = hairColorOptions,
                            selectedCode = viewModel.draft.hairColor,
                            optionsEnabled = true,
                            onSelectOption = { code ->
                                viewModel.setHairColor(code)
                                navController.navigate(Screen.ProfileCustomizeComplete.route)
                            },
                            onBack = { navController.popBackStack() },
                            onPrevStep = { navController.popBackStack() },
                            onNextStep = null
                        )
                    }
                    composable(Screen.ProfileCustomizeComplete.route) { entry ->
                        val viewModel = entry.sharedProfileCustomizeViewModel(navController)
                        val draft = viewModel.draft
                        val summaryLabels = listOf(
                            profileCustomizeOptionLabel(glassesOptions, draft.glasses),
                            profileCustomizeOptionLabel(bangsOptions, draft.bangs?.toString()),
                            profileCustomizeOptionLabel(hairLengthOptions, draft.hairLength),
                            profileCustomizeOptionLabel(hairColorOptions, draft.hairColor)
                        )
                        ProfileCustomizeCompleteScreen(
                            summaryLabels = summaryLabels,
                            onBack = { navController.popBackStack() },
                            onEditAgain = {
                                navController.popBackStack(Screen.ProfileCustomizeGlasses.route, inclusive = false)
                            },
                            onConfirm = {
                                viewModel.save {
                                    navController.popBackStack(Screen.Settings.route, inclusive = false)
                                }
                            },
                            saving = viewModel.saveState is ProfileCustomizeSaveState.Loading,
                            errorMessage = (viewModel.saveState as? ProfileCustomizeSaveState.Error)?.message
                        )
                    }
                }
            }
        }

        Image(
            painter = painterResource(R.drawable.bg_paper_texture),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            alpha = 0.35f,
            modifier = Modifier.fillMaxSize()
        )
    }
}

// 일기 작성 플로우(중첩 네비게이션 그래프) 내 화면들이 같은 DiaryViewModel 인스턴스를
// 공유하도록, 그래프의 시작 지점 백스택 엔트리에 스코프를 건다.
@Composable
private fun NavBackStackEntry.sharedDiaryViewModel(navController: NavHostController): DiaryViewModel {
    val parentEntry = remember(this) {
        navController.getBackStackEntry(Screen.DiaryGraph.route)
    }
    return viewModel(parentEntry)
}

// 회원가입 플로우(중첩 네비게이션 그래프) 내 화면들이 같은 SignupViewModel 인스턴스를
// 공유하도록, 그래프의 시작 지점 백스택 엔트리에 스코프를 건다.
@Composable
private fun NavBackStackEntry.sharedSignupViewModel(navController: NavHostController): SignupViewModel {
    val parentEntry = remember(this) {
        navController.getBackStackEntry(Screen.SignupGraph.route)
    }
    return viewModel(parentEntry)
}

// 회원가입 마지막(생년월일) 단계에서 계정 부가정보 저장이 실패했을 때, 로그인 화면이 들고 있던
// 바로 그 LoginViewModel 인스턴스에 안내 문구를 심어두기 위한 스코프.
@Composable
private fun NavBackStackEntry.sharedLoginViewModel(navController: NavHostController): LoginViewModel {
    val parentEntry = remember(this) {
        navController.getBackStackEntry(Screen.Login.route)
    }
    return viewModel(parentEntry)
}

// 성별/직업 변경 화면에서 저장에 성공했을 때, 설정 화면이 들고 있던 바로 그 SettingsViewModel
// 인스턴스를 찾아 계정 정보를 다시 불러오게 하기 위한 스코프.
@Composable
private fun NavBackStackEntry.sharedSettingsViewModel(navController: NavHostController): SettingsViewModel {
    val parentEntry = remember(this) {
        navController.getBackStackEntry(Screen.Settings.route)
    }
    return viewModel(parentEntry)
}

// 이미지 커스터마이징 플로우(중첩 네비게이션 그래프) 내 4단계가 같은 ProfileCustomizeViewModel
// 인스턴스를 공유하도록, 그래프의 시작 지점 백스택 엔트리에 스코프를 건다.
@Composable
private fun NavBackStackEntry.sharedProfileCustomizeViewModel(navController: NavHostController): ProfileCustomizeViewModel {
    val parentEntry = remember(this) {
        navController.getBackStackEntry(Screen.ProfileCustomizeGraph.route)
    }
    return viewModel(parentEntry)
}
