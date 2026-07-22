# 감정서가 - 프론트엔드 (Android)

## 스택
- Kotlin + Jetpack Compose
- minSdk 33 (Android 13) / targetSdk 35
- Navigation Compose (화면 전환)
- Retrofit + OkHttp (백엔드 연동 준비, `sentiment/` 모델 서버 연결용)

## 여는 법
1. Android Studio 설치 (없으면 https://developer.android.com/studio 에서 최신 버전)
2. Android Studio 실행 → `Open` → 이 `frontend` 폴더 선택
3. 처음 열면 Gradle Wrapper가 없다는 안내가 뜰 수 있는데, `Sync Project with Gradle Files` 누르면 Android Studio가 자동으로 생성/동기화함
4. 에뮬레이터(Android 13 이상, API 33+) 하나 만들고 Run

## 구조
```
app/src/main/java/com/gamjungseoga/app/
  MainActivity.kt        # 앱 진입점 + NavHost
  navigation/Screen.kt    # 화면 route 정의 (피그마 화면 나오면 여기 추가)
  screens/home/           # 화면별 폴더 (피그마 화면마다 폴더 하나씩 추가)
  ui/theme/               # Color/Type/Theme (피그마 스타일 가이드로 교체 예정)
  network/                # 백엔드(KoBERT 감정분석 서버) 연동용 Retrofit 설정
```

## 피그마 작업 옮길 때
- 화면 하나당 `screens/<화면이름>/<화면이름>Screen.kt` 로 추가
- 새 화면은 `navigation/Screen.kt`에 route 추가 후 `MainActivity.kt`의 `NavHost`에 `composable(...)` 등록
- 색상/폰트는 `ui/theme/Color.kt`, `Type.kt`에 피그마 값 그대로 반영
