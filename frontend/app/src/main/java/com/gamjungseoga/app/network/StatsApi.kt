package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

// backend/app/routers/stats.py, backend/app/schemas/stats.py 와 1:1로 맞춘 인터페이스
interface StatsApi {
    @GET("stats/daily/{userId}")
    suspend fun getDailyStats(
        @Path("userId") userId: String,
        @Query("date") date: String? = null // YYYY-MM-DD, 생략하면 서버가 오늘 날짜로 처리
    ): DailyStatsResponse

    @GET("stats/monthly/{userId}")
    suspend fun getMonthlyStats(
        @Path("userId") userId: String,
        @Query("year") year: Int,
        @Query("month") month: Int
    ): MonthlyStatsResponse
}

data class EmotionScore(
    val emotion: String,
    val score: Double
)

data class DailyStatsResponse(
    val date: String,
    @SerializedName("top_emotion") val topEmotion: String? = null,
    @SerializedName("top3_emotions") val top3Emotions: List<EmotionScore> = emptyList(),
    val companions: List<String> = emptyList(),
    val places: List<String> = emptyList()
)

data class EmotionFlowPoint(
    val date: String,
    @SerializedName("sentiment_score") val sentimentScore: Double,
    @SerializedName("top_emotion") val topEmotion: String? = null
)

data class EmotionDistributionItem(
    val emotion: String,
    val percentage: Double,
    val color: String,
    val valence: String? = null
)

data class TopEntity(
    val name: String,
    val count: Int,
    @SerializedName("top3_emotions") val top3Emotions: List<EmotionScore> = emptyList()
)

data class MonthlyStatsResponse(
    val year: Int,
    val month: Int,
    @SerializedName("top_emotion") val topEmotion: String? = null,
    @SerializedName("top3_emotions") val top3Emotions: List<EmotionScore> = emptyList(),
    @SerializedName("emotion_flow") val emotionFlow: List<EmotionFlowPoint> = emptyList(),
    @SerializedName("emotion_distribution") val emotionDistribution: List<EmotionDistributionItem> = emptyList(),
    @SerializedName("most_positive_day") val mostPositiveDay: String? = null,
    @SerializedName("most_negative_day") val mostNegativeDay: String? = null,
    @SerializedName("top_companion") val topCompanion: TopEntity? = null,
    @SerializedName("top_place") val topPlace: TopEntity? = null
)
