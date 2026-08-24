package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST

// backend/app/routers/diary.py, backend/app/schemas/diary.py 와 1:1로 맞춘 인터페이스
interface DiaryApi {
    @POST("generate-diary")
    suspend fun generateDiary(@Body request: DiaryGenerateRequest): DiaryGenerateResponse

    @GET("diaries/{userId}")
    suspend fun getDiaries(@Path("userId") userId: String): DiaryListResponse
}

data class DiaryGenerateRequest(
    val what: String,
    val why: String,
    val who: List<String>,
    @SerializedName("when") val whenText: String,
    val where: String,
    @SerializedName("user_id") val userId: String? = null
)

data class DiaryGenerateResponse(
    val status: String,
    @SerializedName("generated_diary") val generatedDiary: String,
    @SerializedName("validation_failed") val validationFailed: Boolean,
    @SerializedName("top_emotion") val topEmotion: String? = null,
    @SerializedName("emotion_scores") val emotionScores: Map<String, Double>? = null,
    @SerializedName("sentiment_score") val sentimentScore: Double? = null
)

data class DiaryListResponse(
    val status: String,
    val diaries: List<DiaryEntry> = emptyList()
)

// backend/supabase_schema.sql의 diary_entries 테이블 컬럼과 1:1 대응 (GET /diaries/{user_id}가
// select("*") 결과를 그대로 반환하므로 테이블 컬럼명 = 응답 필드명)
data class DiaryEntry(
    val id: Long,
    @SerializedName("user_id") val userId: String? = null,
    val what: String,
    val why: String? = null,
    val who: String? = null,
    @SerializedName("when_") val whenText: String? = null,
    @SerializedName("where_") val where: String? = null,
    @SerializedName("generated_diary") val generatedDiary: String? = null,
    @SerializedName("validation_failed") val validationFailed: Boolean = false,
    @SerializedName("top_emotion") val topEmotion: String? = null,
    @SerializedName("emotion_scores") val emotionScores: Map<String, Double>? = null,
    @SerializedName("sentiment_score") val sentimentScore: Double? = null,
    @SerializedName("created_at") val createdAt: String? = null
)
