package com.gamjungseoga.app.network

import retrofit2.http.Body
import retrofit2.http.POST

// TODO: sentiment/infer.py 가 서버(FastAPI 등)로 노출되면 실제 엔드포인트로 교체
interface EmotionApi {
    @POST("predict")
    suspend fun predict(@Body request: EmotionRequest): EmotionResponse
}

data class EmotionRequest(
    val text: String
)

// label: 현재는 "긍정"/"부정" 2종, 이후 37종 감정 라벨로 확장 예정
// imageUrl: SD3가 생성한 감정 이미지 URL. 백엔드 API 필드명 확정되면 맞추기
data class EmotionResponse(
    val label: String,
    val confidence: Double,
    val imageUrl: String? = null
)
