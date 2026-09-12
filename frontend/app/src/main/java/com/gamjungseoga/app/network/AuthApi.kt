package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.POST

// backend/app/routers/auth.py, backend/app/schemas/auth.py 와 1:1로 맞춘 인터페이스
interface AuthApi {
    @POST("signup")
    suspend fun signup(@Body request: SignupRequest): AuthResponse

    @POST("login")
    suspend fun login(@Body request: LoginRequest): AuthResponse
}

data class SignupRequest(
    val email: String,
    val password: String,
    val nickname: String? = null
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class AuthResponse(
    val status: String,
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("user_id") val userId: String? = null,
    val nickname: String? = null
)
