package com.gamjungseoga.app

import android.app.Application
import android.content.Context

// TokenStore 등 Activity/ViewModel 스코프 밖(네트워크 계층)에서 Context가 필요한 곳에 쓰기 위한
// 앱 전역 Context 홀더. (이름이 MainActivity.kt의 @Composable fun GamjeongseogaApp()과
// 충돌해서 클래스명은 별도로 둠)
class AppContextProvider : Application() {
    override fun onCreate() {
        super.onCreate()
        appContext = applicationContext
    }

    companion object {
        lateinit var appContext: Context
            private set
    }
}
