package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.POST

// backend/app/routers/personal_test.py, backend/app/schemas/personal_test.py 와 1:1로 맞춘 인터페이스
interface PersonalTestApi {
    @POST("personal-test")
    suspend fun submitPersonalTest(@Body request: PersonalTestSubmitRequest): PersonalTestSubmitResponse
}

data class PersonalTestSubmitRequest(
    @SerializedName("user_id") val userId: String? = null,
    // "1".."19" -> 1~5점. 백엔드가 19문항 전체 응답을 강제 검증하므로 반드시 다 채워서 보내야 함.
    val answers: Map<String, Int>
)

data class PersonalTestSubmitResponse(
    val status: String
)
