package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

// backend/app/routers/personal_test.py, backend/app/schemas/personal_test.py 와 1:1로 맞춘 인터페이스
interface PersonalTestApi {
    @POST("personal-test")
    suspend fun submitPersonalTest(@Body request: PersonalTestSubmitRequest): PersonalTestSubmitResponse

    @GET("personal-test/status")
    suspend fun getPersonalTestStatus(): PersonalTestStatusResponse
}

data class PersonalTestSubmitRequest(
    // "1".."19" -> 1~5점. 백엔드가 19문항 전체 응답을 강제 검증하므로 반드시 다 채워서 보내야 함.
    val answers: Map<String, Int>
)

data class PersonalTestSubmitResponse(
    val status: String
)

data class PersonalTestStatusResponse(
    val status: String,
    val completed: Boolean,
    @SerializedName("last_completed_at") val lastCompletedAt: String? = null
)

// 로그인 직후/앱 시작 시 둘 다 같은 기준으로 "검사를 강제해야 하는가"를 판단하므로 공용 함수로 둠.
// 상태 확인 자체가 실패하면(서버 다운 등) 검사를 강제하지 않는다 - 서버 장애로 앱을 아예 못 쓰게
// 되는 상황을 막기 위함.
suspend fun needsPersonalTest(): Boolean = runCatching {
    !ApiClient.personalTestApi.getPersonalTestStatus().completed
}.getOrDefault(false)
