# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"감정서가" (Gamjeongseoga) — an Android diary app where users answer a few guided questions (what/why/who/when/where), send them to a backend that generates a diary entry and runs sentiment/emotion analysis (KoBERT + SD3 for images), then shows the result plus emotion stats/reports. This repo is **frontend only** (Kotlin + Jetpack Compose); the backend (FastAPI + Supabase, referenced throughout via code comments as `backend/app/...`) lives elsewhere and is not in this repo.

The app has real JWT-based authentication (see **Authentication** below) — there is no more hardcoded test user. Every authenticated request carries whatever token `TokenStore` currently holds; endpoints are all scoped to "me" (`/diaries/me`, `/users/me/...`, `/stats/.../me`) so the backend resolves the user from the token, not from a path parameter.

## Commands

Build and install via Android Studio (`Open` on this `frontend` folder, then Run), or from the command line:

```
./gradlew assembleDebug         # build debug APK
./gradlew installDebug          # build + install on connected device/emulator
./gradlew lint                  # Android lint
./gradlew test                  # unit tests (module has no test sources yet — this is a no-op)
./gradlew connectedAndroidTest  # instrumented tests (no test sources yet either)
```

On Windows use `gradlew.bat` instead of `./gradlew`. There are no unit or instrumented test files in the project yet (`app/src/test`, `app/src/androidTest` don't exist) — `test`/`connectedAndroidTest` will pass trivially with nothing to run.

Backend must be reachable at the base URL in `network/ApiClient.kt` (`BASE_URL`, currently a RunPod proxy address — `ApiClient.kt` has a comment warning that this changes whenever the RunPod pod restarts) or the app's network calls will fail and screens will show their error/empty states.

## Authentication

The app has a full login/signup flow backed by JWT, not a hardcoded test user:

- **`network/AuthApi.kt`**: `POST /signup`, `POST /login`, both return `AuthResponse(accessToken, userId, nickname)`.
- **`network/TokenStore.kt`**: `SharedPreferences`-backed storage for the access token/userId/nickname. `ApiClient`'s `authInterceptor` reads the token on every request (except `signup`/`login` themselves, listed in `noAuthEndpoints`) and attaches `Authorization: Bearer <token>`.
- **No refresh token**: if any authenticated request gets a 401 (except on `signup`/`login`, and except `PATCH /users/me/password` — a wrong "current password" also returns 401 but means "bad input", not "session expired", so it's listed in `skipLogoutOn401Endpoints`), `ApiClient` clears the stored session and calls `SessionManager.notifyUnauthorized()`.
- **`network/SessionManager.kt`**: a `SharedFlow<Unit>` that `GamjeongseogaApp` (in `MainActivity.kt`) collects via `LaunchedEffect` — on a signal it navigates to `Screen.Login` and clears the entire back stack (`popUpTo(graph.id) { inclusive = true }`).
- **Start destination**: `GamjeongseogaApp` picks `Screen.Home` or `Screen.Login` synchronously based on `TokenStore.getToken() != null`, decided once with `remember` before the first frame (no login→home flash).
- **Personal-test gate on app start**: if a token already exists, a separate `LaunchedEffect(Unit)` calls `needsPersonalTest()` (`network/PersonalTestApi.kt`, `GET /personal-test/status`) in the background; if the test isn't completed, it navigates to the forced emotion-test route. If the status check itself fails (server down, etc.) it does **not** force the test — see `needsPersonalTest()`'s doc comment.

### Login / signup flow

- **`screens/auth/LoginScreen.kt` + `LoginViewModel.kt`**: email/password → `POST /login` → `TokenStore.saveSession(...)` → `onLoginSuccess(needsPersonalTest)`. `MainActivity` uses that callback to route either to `Screen.Home` or to the forced emotion test, clearing the back stack either way.
- **Signup is a 6-step nested nav graph** (`Screen.SignupGraph`, route `"signup"`): `email → password → nickname → gender → job → birthdate`, all screens sharing one `SignupViewModel` instance scoped to the graph's start-destination back stack entry (same `sharedXViewModel` pattern as the diary graph — see `MainActivity.kt`'s `sharedSignupViewModel`). The gender/job steps reuse the generic `ChipSelectScreen` (`screens/settings/ChipSelectScreen.kt`) — the same composable the Settings "성별 변경"/"직업 변경" screens use.
- On the last step (birthdate), `SignupViewModel.submitSignup` calls `POST /signup` (creates the account + saves the returned token), then `PATCH /users/me/account` with gender/job/birthdate. If `/signup` fails, nothing is saved and the screen shows an error. If `/signup` succeeds but the follow-up `PATCH` fails, the account already exists (can't be undone from here), so it calls `onPartialFailure` instead: a notice is stashed on the shared `LoginViewModel` instance and the user is sent back to `Screen.Login` to log in normally.

## Architecture

- **Single-Activity, Compose Navigation.** `MainActivity.kt` hosts one `NavHost` under a `Scaffold` with a custom `BottomNavBar`. Routes are defined in `navigation/Screen.kt` as a sealed class. The bottom bar is hidden only on `Screen.Login` and anywhere under `Screen.SignupGraph`; every other route (including the diary-creation graph and the standalone settings sub-screens) still renders it.
- **Diary creation is a nested nav graph** (`Screen.DiaryGraph`, route `"diary"`) entered via the bottom bar's `+` FAB: `date → what → why → who → when → where → generating → complete`. All screens in this flow share a single `DiaryViewModel` instance by scoping `viewModel()` to the graph's start-destination back stack entry (see `sharedDiaryViewModel()` extension at the bottom of `MainActivity.kt`) — draft answers accumulate in `DiaryViewModel.draft` across screens. On the `where` step's "다음으로" the app moves to `DiaryGeneratingScreen`, which itself triggers `POST /generate-diary` and **only advances on success**; on failure it stays on the screen showing an error with up to 2 retries plus a "돌아가기" exit button (see `DiaryGeneratingScreen.kt` — this replaced the old "advance regardless of outcome" behavior).
- **Diary detail / re-reading a saved entry**: tapping an Archive card or a Home "최근 작성한 페이지" card navigates to `Screen.DiaryDetail` (route `"diary-detail/{diaryId}"`, outside the diary-creation graph). `DiaryDetailScreen` (`screens/diary/DiaryDetailScreen.kt`) takes its own `DiaryListViewModel` instance, finds the matching `DiaryEntry` by id in the already-fetched `GET /diaries/me` list, and renders it with the same shared report-card components `DiaryCompleteScreen` uses (see next bullet). No extra network call is made — everything needed (`generatedDiary`, `topEmotion`, `emotionScores`, `imageUrl`, `createdAt`, `who`, `where`) is already in `DiaryEntry`.
- **Shared "emotion report" widgets** (`components/EmotionReportCards.kt`): `DiaryCompleteScreen`, `DiaryDetailScreen`, and `AnalysisScreen`'s daily/monthly tabs all render the same visual pieces — a hero image + emotion badge, an "오늘 가장 많이 느낀 감정은 OO예요" summary card, a "주요 감정" top-3 percentage bar card, and person/place info cards. These were factored out into one file (`EmotionBar`, `topEmotionBarsFromScores`, `EmotionHeroImage`, `EmotionBadge`, `EmotionSummaryCard`, `TopEmotionsBarCard`, `PersonPlaceInfoCard`) so the three screens don't duplicate the layout. Each screen still passes its own `fontFamily` (Pretendard for diary screens, S-Core Dream for Analysis) since the font split between screens is an intentional design choice, not a bug.
- **Networking**: `network/ApiClient.kt` is a single Retrofit+OkHttp singleton exposing `diaryApi`, `personalTestApi`, `statsApi`, `authApi`, `userApi` (Gson converter, HTTP logging interceptor, the auth interceptor described above). Each `*Api.kt` interface + its request/response data classes are commented as being kept 1:1 with a specific backend router/schema file — when changing a DTO, keep the field names/`@SerializedName` mappings in sync with intent even though the backend isn't in this repo.
- **`network/AppScope.kt`** is a process-wide `CoroutineScope(SupervisorJob() + Dispatchers.IO)` used only for fire-and-forget requests that must outlive a `ViewModel`/screen (currently: submitting the personal emotion test from the non-forced "다시하기" flow, right before `popBackStack()`). Don't reuse `viewModelScope` for requests that must survive the screen closing.
- **State loading pattern**: screens/viewmodels that hit the network model state as a sealed interface with `Loading` / `Loaded(data)` / `Error(message)` variants (see `DiaryListState`, `AccountState`/`StatsState`/`DeleteAccountState` in `SettingsViewModel`, and the local `mutableStateOf` trios in `AnalysisScreen`), and render a corresponding inline text state in the Compose tree rather than a shared loading component.
- **`DiaryListViewModel`** wraps `GET /diaries/me` and is instantiated independently (via default `viewModel()` param) in `HomeScreen`, `ArchiveScreen`, `DiaryDetailScreen`, and the date-picker thumbnail lookup inside the diary-creation graph's `DiaryDateScreen` step — each derives its own view of the same diary list. There's no shared cache/refresh signal between instances; a screen only re-fetches when its own `ViewModel` is (re)created.
- **Emotion → image/asset mapping**: SD3-generated per-entry images don't always exist end-to-end yet. `emotion/EmotionAssets.kt` maps the ~24 fine-grained emotion labels down to 8 existing illustration drawables (`archive_*`) as a stand-in wherever a real `imageUrl` from the backend is absent; `AsyncImage` (Coil) is used wherever a real URL *is* present, with a drawable/color fallback. `ApiClient.resolveImageUrl` normalizes whatever the backend sends (absolute URL vs. relative path) before it's handed to Coil.
- **Theming**: `ui/theme/Color.kt` (raw palette + many screen-specific named colors, e.g. `TitleBrown`, `SurfaceColor`, `PillPinkBg`), `Type.kt` (defines both `SCoreDreamFontFamily`/main body font and `PretendardFontFamily` used selectively — the two are mixed intentionally per-screen, not a bug), `Theme.kt`. A few colors (see **Known rough edges**) are still named/approximate placeholders pending real Figma/asset values.
- **`components/`** holds cross-screen widgets: `BottomNavBar` (4 tabs + center FAB), `WheelPicker` (generic infinite/finite scrolling picker used by every date-picker dialog in Archive/Analysis/Diary flows), `EmotionReportCards` (see above).

## Screen-by-screen status

| Screen | Route | Status |
|---|---|---|
| Login | `login` | **Wired to backend.** `POST /login`, saves session token, routes to Home or forced emotion test. |
| Signup (6 steps) | `signup/*` | **Wired to backend.** `POST /signup` + `PATCH /users/me/account` on the last step; see **Authentication** above for partial-failure handling. |
| Home | `home` | **Wired to backend.** Loads `GET /diaries/me` via `DiaryListViewModel`; computes "이번 달 포함 최근 3개월" top emotion client-side. Header date is `LocalDate.now()` (no longer hardcoded). Recent-pages carousel and monthly-emotion cards are tappable where backed by a real diary id; fallback decorative colors/sample illustrations are still placeholders — see **Known rough edges**. |
| Archive (아카이브) | `archive` | **Wired to backend.** Same diary list, grouped by month with a year/month wheel-picker dialog. Each card navigates to the diary detail screen. Card images use the emotion→drawable fallback map when no real generated art exists yet. |
| Analysis (분석/리포트) | `analysis` | **Wired to backend.** Daily tab calls `GET /stats/daily/me`; monthly tab calls `GET /stats/monthly/me` plus two extra daily calls for the most positive/negative day. All charts are real computed views over API data; the summary/top-emotion/person-place cards now come from the shared `components/EmotionReportCards.kt` widgets. |
| Settings (설정) | `settings` | **Fully wired to backend.** `SettingsViewModel` loads `GET /users/me/account` and `GET /users/me/stats` for the account rows and the Days/Emotion stats card. 로그아웃 clears the stored session; 계정탈퇴 calls `DELETE /users/me` behind a confirm dialog with loading/error states. "퍼스널 감정 검사 다시하기" navigates to the (non-forced) Emotion Test flow. |
| Settings sub-screens: 성별/직업/생년월일/비밀번호 변경, 개인정보처리방침, 이용약관 | `settings/*` | **Wired to backend** (`GenderScreen`/`JobScreen` via `ChipSelectViewModel` + `PATCH /users/me/account`, `BirthDateChangeScreen` similarly, `PasswordChangeScreen` via `PATCH /users/me/password`). Privacy policy / terms-of-service are static text screens — see **Known rough edges** for their placeholder content. |
| Personal Emotion Test (퍼스널 감정 검사) | `emotiontest` | **Wired to backend, two different submit paths.** 19-question survey (`EmotionTestQuestions.kt`) driven by `EmotionTestViewModel`. Forced entry (fresh signup/login without a completed test, `forced=true`): back navigation is blocked, the last answer submits via `viewModelScope` and waits for the result, showing a retry button on failure. Non-forced entry ("다시하기" from Settings, `forced=false`): submits fire-and-forget via `AppScope` and the screen pops immediately — a failure here is silent (see **Known rough edges**). |
| Diary creation flow (date/what/why/who/when/where) | `diary/*` | **UI complete, not backend-integrated until the final step.** Pure client-side form state accumulated in `DiaryViewModel.draft`. `diary/date`'s calendar is wired to real per-day thumbnails via `buildDayImageUrls` (built from the same `GET /diaries/me` list). |
| Diary generating | `diary/generating` | **Wired to backend, with retry.** Triggers `POST /generate-diary` on entry; advances only on success. On failure, shows the error message with up to 2 retries and an exit button back to Home. |
| Diary complete | `diary/complete` | **Wired to backend.** Shows the real `generated_diary`/`top_emotion`/`emotion_scores`/`image_url` from the just-generated response using the shared `EmotionReportCards` widgets. |
| Diary detail (다시 보기) | `diary-detail/{diaryId}` | **Wired to backend (no extra call).** New screen; see **Architecture** above. Shows loading/error/"일기를 찾을 수 없어요" states while the shared `DiaryListViewModel` list is loading or the id isn't found. |
| 이미지 커스터마이징 (profile customize) | `profile-customize/*` | **Wired to backend, no visual preview.** 4-step chip-select flow (`ProfileCustomizeViewModel`) loads `GET /users/me/profile` and saves via `PATCH /users/me/profile` on confirm. Every step is text-only (안경/앞머리/머리길이/머리색 chips) — there is no character image anywhere in the flow that actually updates to reflect the selection; it reads as a questionnaire rather than a visual customizer. |

## Known rough edges worth knowing before touching related code

- **No pull-to-refresh / shared cache.** Every `DiaryListViewModel`/`SettingsViewModel` instance re-fetches once on creation and never again; screens only see fresh data because `NavHost` tends to recreate the relevant composable (e.g. finishing the diary-creation graph pops the whole back stack, so Home gets a brand-new `DiaryListViewModel`). There's no manual refresh affordance anywhere.
- **퍼스널 검사 "다시하기" 제출 실패는 조용히 사라짐.** The non-forced resubmit path (`EmotionTestViewModel.submitIfComplete`) is fire-and-forget via `AppScope`; the screen is already closed by the time a failure would be known, so there's no retry UX for that path (there is for the forced path). See the TODO comment at the call site.
- **이미지 커스터마이징 has no visual feedback.** See the table above — worth fixing before treating that flow as "done" in any visual sense.
- **Analysis person/place "N회" badges are approximate.** `AnalysisScreen.toPills` rounds a summed emotion score, not an actual occurrence count, because the backend doesn't return a dedicated count field for `top_companion`/`top_place`.
- **Legal screens are placeholder copy.** `screens/settings/LegalScreens.kt`'s 개인정보처리방침/이용약관 text is explicitly marked as an un-reviewed draft for the demo, not real legal copy — replace before any real launch.
- **A few colors/illustrations are still named placeholders**, not final Figma values: `PlaceholderOcean`/`PlaceholderNavy`/`PlaceholderTerracotta` (Home's recent-pages fallback colors) and the `emotion_card_1/2/3` sample illustrations cycled on Home's monthly-emotion cards (real per-month generated art isn't wired up yet).
- **Some response fields are parsed but never displayed**: `DiaryGenerateResponse`/`DiaryEntry`'s `validationFailed` and `sentimentScore` are deserialized but no screen currently reads them.
- **SD3-generated per-entry images aren't always present.** Wherever `imageUrl`/`image_url` is null (common — not every backend path populates it yet), the UI falls back to a bundled drawable via `emotion/EmotionAssets.kt`; this is expected/by design, not a bug to "fix" by itself.
- **No offline support.** Everything requires a live connection to the backend at `ApiClient.BASE_URL`; there's no local DB/cache layer.
