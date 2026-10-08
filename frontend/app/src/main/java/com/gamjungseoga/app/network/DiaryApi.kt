package com.gamjungseoga.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

// backend/app/routers/diary.py, backend/app/schemas/diary.py 와 1:1로 맞춘 인터페이스
interface DiaryApi {
    // 227초가 걸리던 동기 엔드포인트(POST /generate-diary)는 120초 타임아웃에 항상 걸려서
    // job 방식으로 대체됐다. createDiaryJob은 1초 이내에 jobId만 돌려주고, 실제 생성 결과는
    // getDiaryJob을 폴링해서 받는다.
    @POST("generate-diary/jobs")
    suspend fun createDiaryJob(@Body request: DiaryGenerateRequest): DiaryJobCreated

    @GET("generate-diary/jobs/{jobId}")
    suspend fun getDiaryJob(@Path("jobId") jobId: String): DiaryJobStatus

    @GET("diaries/me")
    suspend fun getDiaries(): DiaryListResponse
}

data class DiaryGenerateRequest(
    val what: String,
    val why: String,
    val who: String,
    @SerializedName("when") val whenText: String,
    val where: String,
    // 서버가 날짜를 우선적으로 이 필드에서 읽고, whenText(자유 형식 문장)의 날짜 파싱은 보조
    // 수단으로만 쓴다. "YYYY-MM-DD" 형식.
    val date: String
)

data class DiaryJobCreated(
    @SerializedName("job_id") val jobId: String,
    val status: String
)

data class DiaryJobStatus(
    @SerializedName("job_id") val jobId: String,
    val status: String, // processing | done | error
    val result: DiaryGenerateResponse? = null,
    val error: String? = null
)

data class DiaryGenerateResponse(
    val status: String,
    @SerializedName("generated_diary") val generatedDiary: String,
    @SerializedName("validation_failed") val validationFailed: Boolean,
    @SerializedName("top_emotion") val topEmotion: String? = null,
    @SerializedName("emotion_scores") val emotionScores: Map<String, Double>? = null,
    @SerializedName("sentiment_score") val sentimentScore: Double? = null,
    @SerializedName("image_url") val imageUrl: String? = null,
    val id: Long? = null
)

data class DiaryListResponse(
    val status: String,
    val diaries: List<DiaryEntry> = emptyList()
)

// backend/supabase_schema.sql의 diary_entries 테이블 컬럼과 1:1 대응 (GET /diaries/me가
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
    @SerializedName("created_at") val createdAt: String? = null,
    // SD3가 생성한 일기 이미지 URL로 추정되는 컬럼. 정확한 필드명은 백엔드 Swagger로 아직
    // 확인 못 했으니, diary_entries 테이블에 이 컬럼이 없거나 이름이 다르면 그냥 null로 와서
    // 기존 fallback(감정별 일러스트)이 그대로 쓰인다.
    @SerializedName("image_url") val imageUrl: String? = null
)
