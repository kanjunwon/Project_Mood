package com.gamjungseoga.app.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    // TODO: 백엔드 서버 주소가 정해지면 교체 (에뮬레이터에서 로컬 서버는 10.0.2.2 사용)
    private const val BASE_URL = "http://10.0.2.2:8000/"

    // 로그인이 아직 없어서, 서버에 기록을 쓰고 다시 읽어올 때 전부 이 고정 ID로 통일해서 사용.
    // 로그인 붙으면 실제 로그인한 사용자의 user_id로 교체.
    const val TEST_USER_ID: String = "test-user"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val diaryApi: DiaryApi = retrofit.create(DiaryApi::class.java)
    val personalTestApi: PersonalTestApi = retrofit.create(PersonalTestApi::class.java)
    val statsApi: StatsApi = retrofit.create(StatsApi::class.java)
}
