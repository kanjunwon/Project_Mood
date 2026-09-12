# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"감정서가" (Gamjeongseoga) — an Android diary app where users answer a few guided questions (what/why/who/when/where), send them to a backend that generates a diary entry and runs sentiment/emotion analysis (KoBERT + SD3 for images), then shows the result plus emotion stats/reports. This repo is **frontend only** (Kotlin + Jetpack Compose); the backend (FastAPI + Supabase, referenced throughout via code comments as `backend/app/...`) lives elsewhere and is not in this repo.

There is currently **no authentication**. Every request uses a hardcoded `ApiClient.TEST_USER_ID = "test-user"` (see `network/ApiClient.kt`). Anything user-account-related in the UI (Settings screen account rows, login) is placeholder only.

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

Backend must be reachable at the base URL in `network/ApiClient.kt` (`http://10.0.2.2:8000/`, i.e. `localhost:8000` from the host machine, for the emulator) or the app's network calls will fail and screens will show their error/empty states.

## Architecture

- **Single-Activity, Compose Navigation.** `MainActivity.kt` hosts one `NavHost` under a `Scaffold` with a custom `BottomNavBar`. Routes are defined in `navigation/Screen.kt` as a sealed class.
- **Diary creation is a nested nav graph** (`Screen.DiaryGraph`, route `"diary"`) entered via the bottom bar's `+` FAB: `date → what → why → who → when → where → generating → complete`. All screens in this flow share a single `DiaryViewModel` instance by scoping `viewModel()` to the graph's start-destination back stack entry (see `sharedDiaryViewModel()` extension at the bottom of `MainActivity.kt`) — draft answers accumulate in `DiaryViewModel.draft` across screens. On the `where` step's "다음으로" the app calls `POST /generate-diary`; `DiaryGeneratingScreen` just waits on `DiaryViewModel.generationState` and advances regardless of success/failure (failures fall back to locally-built mock text in `DiaryCompleteScreen`).
- **Networking**: `network/ApiClient.kt` is a single Retrofit+OkHttp singleton exposing `diaryApi`, `personalTestApi`, `statsApi` (Gson converter, HTTP logging interceptor). Each `*Api.kt` interface + its request/response data classes are commented as being kept 1:1 with a specific backend router/schema file — when changing a DTO, keep the field names/`@SerializedName` mappings in sync with intent even though the backend isn't in this repo.
- **`network/AppScope.kt`** is a process-wide `CoroutineScope(SupervisorJob() + Dispatchers.IO)` used only for fire-and-forget requests that must outlive a `ViewModel`/screen (currently: submitting the personal emotion test on its last answer, right before `popBackStack()`). Don't reuse `viewModelScope` for requests that must survive the screen closing.
- **State loading pattern**: screens/viewmodels that hit the network model state as a sealed interface with `Loading` / `Loaded(data)` / `Error(message)` variants (see `DiaryListState`, and the local `mutableStateOf` trios in `AnalysisScreen`), and render a corresponding inline text state in the Compose tree rather than a shared loading component.
- **`DiaryListViewModel`** wraps `GET /diaries/{userId}` and is instantiated independently (via default `viewModel()` param) in both `HomeScreen` and `ArchiveScreen`, which each derive their own view of the same diary list (recent 3 months' top emotion per month on Home; grouped-by-selected-month grid on Archive).
- **Emotion → image/asset mapping**: SD3-generated per-entry images don't exist yet end-to-end. `emotion/EmotionAssets.kt` maps the ~24 fine-grained emotion labels down to 8 existing illustration drawables (`archive_*`) as a stand-in wherever a real `imageUrl` from the backend is absent; `AsyncImage` (Coil) is used wherever a real URL *is* present, with a drawable/color fallback.
- **Theming**: `ui/theme/Color.kt` (raw palette + many screen-specific named colors, e.g. `TitleBrown`, `SurfaceColor`, `PillPinkBg`), `Type.kt` (defines both `SCoreDreamFontFamily`/main body font and `PretendardFontFamily` used selectively — the two are mixed intentionally per-screen, not a bug), `Theme.kt`. Colors/fonts are meant to be swapped for actual Figma values as screens are finalized — many are still named/approximate placeholders.
- **`components/`** holds cross-screen widgets: `BottomNavBar` (4 tabs + center FAB), `WheelPicker` (generic infinite/finite scrolling picker used by every date-picker dialog in Archive/Analysis/Diary flows).

## Screen-by-screen status

| Screen | Route | Status |
|---|---|---|
| Home | `home` | **Wired to backend.** Loads `GET /diaries/{userId}` via `DiaryListViewModel`; computes "이번 달 포함 최근 3개월" top emotion client-side from the returned entries. Recent-pages carousel uses real dates but placeholder colors/no real per-entry image (SD3 image URL not populated by backend yet). Today's date in the header is hardcoded (`"2026.06.04"`, marked TODO — should be system date). |
| Archive (아카이브) | `archive` | **Wired to backend.** Same diary list, grouped by month with a year/month wheel-picker dialog. Card images use the emotion→drawable fallback map (no real generated art yet). |
| Analysis (분석/리포트) | `analysis` | **Wired to backend.** Daily tab calls `GET /stats/daily/{userId}`; monthly tab calls `GET /stats/monthly/{userId}` plus two extra daily calls for the most positive/negative day. All charts (top-emotion bars, weekly flow line, month heatmap, person/place pills) are real computed views over API data, no mock. This is the most complete/backend-integrated screen. |
| Settings (설정) | `settings` | **UI shell only, no backend.** Account rows (아이디/비밀번호/성별/직업/생년월일), the "감정 기록 Days/Emotion count" stats card, and terms-of-service rows are all hardcoded sample data (explicit TODO in file). Only the "퍼스널 감정 검사 다시하기" button is wired (navigates to the Emotion Test flow); 로그아웃/계정탈퇴 buttons have no `onClick` behavior. |
| Personal Emotion Test (퍼스널 감정 검사) | `emotiontest` | **Wired to backend**, fire-and-forget. 19-question survey (`EmotionTestQuestions.kt`) driven by `EmotionTestViewModel`; on the last answer, submits `POST /personal-test` via `AppScope` (not awaited — screen pops immediately, no retry/error UI if the submit fails). |
| Diary creation flow (date/what/why/who/when/where) | `diary/*` | **UI complete, not backend-integrated until the final step.** Pure client-side form state accumulated in `DiaryViewModel.draft`. `diary/date`'s calendar accepts a `dayImageUrls` map for per-day thumbnails but nothing ever supplies real data (explicit TODO — always renders empty cells). |
| Diary generating | `diary/generating` | **Wired to backend.** Triggers `POST /generate-diary` on entry and proceeds on completion (success or error alike). |
| Diary complete | `diary/complete` | **Wired to backend with mock fallback.** Shows the real `generated_diary`/`top_emotion`/`emotion_scores` from the API response when present; if the response is null/blank (e.g. request failed), falls back to a locally string-concatenated mock diary and hardcoded "뿌듯함 60%" stats so the screen never looks broken. |
| "Coming soon" placeholder (`screens/common/ComingSoonScreen.kt`) | *(none)* | **Dead/unused.** Not referenced from `MainActivity`'s `NavHost` — was a stand-in for screens before designs existed; every screen now has a real route. Safe to delete or repurpose. |
| Emotion analysis API (`network/EmotionApi.kt`, `POST predict`) | *(none)* | **Defined but unused.** No screen calls this interface; comment says it's waiting on `sentiment/infer.py` being exposed as an actual endpoint. Likely superseded by `generate-diary`'s built-in emotion scoring — check with backend before wiring it up. |

## Known rough edges worth knowing before touching related code

- No login/session: everything reads/writes under `ApiClient.TEST_USER_ID`. Any multi-user feature needs an auth layer first.
- No persistent local cache/DB — every screen refetches from the network on each composition/viewmodel creation; there's no offline support.
- No error retry UX anywhere (failed personal-test submits, failed diary generation, failed stat loads all just show a static message or silently fall back).
- SD3-generated per-entry images are not yet wired from the backend anywhere; every image in the app is either a bundled drawable, a fallback-mapped drawable, or (rarely) `AsyncImage` pointed at a URL field that's currently always null in practice.
