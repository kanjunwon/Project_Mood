package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH

// backend/app/routers/users.py, backend/app/schemas/users.py 와 1:1로 맞춘 인터페이스.
// 전부 로그인한 본인("me") 기준이라 user_id를 경로/바디에 실을 필요 없음 (토큰에서 서버가 추출).
interface UserApi {
    @GET("users/me/profile")
    suspend fun getProfile(): UserProfileResponse

    @PATCH("users/me/profile")
    suspend fun updateProfile(@Body request: UserProfileRequest): UserProfileResponse

    @GET("users/me/account")
    suspend fun getAccount(): UserAccountResponse

    @PATCH("users/me/account")
    suspend fun updateAccount(@Body request: UserAccountUpdateRequest): UserAccountResponse

    @PATCH("users/me/password")
    suspend fun updatePassword(@Body request: UpdatePasswordRequest): UpdatePasswordResponse

    @DELETE("users/me")
    suspend fun deleteAccount(): DeleteAccountResponse

    @GET("users/me/stats")
    suspend fun getStats(): UserStatsResponse
}

data class UserProfileRequest(
    val glasses: Boolean? = null,
    val bangs: Boolean? = null,
    @SerializedName("hair_length") val hairLength: String? = null,
    @SerializedName("hair_color") val hairColor: String? = null
)

data class UserProfileResponse(
    val status: String,
    val glasses: Boolean? = null,
    val bangs: Boolean? = null,
    @SerializedName("hair_length") val hairLength: String? = null,
    @SerializedName("hair_color") val hairColor: String? = null
)

data class UserAccountResponse(
    val status: String,
    val email: String,
    val nickname: String? = null,
    val gender: String? = null,
    val job: String? = null,
    @SerializedName("birth_date") val birthDate: String? = null
)

data class UserAccountUpdateRequest(
    val gender: String? = null,
    val job: String? = null,
    @SerializedName("birth_date") val birthDate: String? = null
)

data class UpdatePasswordRequest(
    @SerializedName("current_password") val currentPassword: String,
    @SerializedName("new_password") val newPassword: String
)

data class UpdatePasswordResponse(
    val status: String
)

data class DeleteAccountResponse(
    val status: String
)

data class UserStatsResponse(
    val status: String,
    @SerializedName("days_since_start") val daysSinceStart: Int,
    @SerializedName("emotion_count") val emotionCount: Int
)
