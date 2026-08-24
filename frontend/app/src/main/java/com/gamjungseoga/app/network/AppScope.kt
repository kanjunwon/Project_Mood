package com.gamjungseoga.app.network

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

// 화면 전환/ViewModel 소멸(예: 퍼스널 검사 마지막 문항 답변 즉시 popBackStack)과
// 무관하게 끝까지 전송되어야 하는 fire-and-forget 요청용 앱 전역 스코프.
// viewModelScope로 보내면 화면이 닫히는 순간 요청이 취소될 수 있어 별도로 둠.
object AppScope {
    val io: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
}
