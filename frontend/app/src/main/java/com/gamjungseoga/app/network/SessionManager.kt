package com.gamjungseoga.app.network

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

// refresh token이 없어서 401을 받으면 무조건 재로그인이 필요함. AuthInterceptor가 401을
// 감지하면 여기로 신호를 보내고, 로그인 화면이 생기면 이 flow를 collect해서 로그인 화면으로
// 이동시키면 된다.
object SessionManager {
    private val _unauthorized = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val unauthorized: SharedFlow<Unit> = _unauthorized

    fun notifyUnauthorized() {
        _unauthorized.tryEmit(Unit)
    }
}
