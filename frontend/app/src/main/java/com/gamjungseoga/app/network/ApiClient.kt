package com.gamjungseoga.app.network

import java.util.concurrent.TimeUnit
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    // TODO: 백엔드 서버 주소가 정해지면 교체 (에뮬레이터에서 로컬 서버는 10.0.2.2 사용)
    const val BASE_URL = "http://10.0.2.2:8000/"

    // 로그인이 아직 없어서, 서버에 기록을 쓰고 다시 읽어올 때 전부 이 고정 ID로 통일해서 사용.
    // 로그인 붙으면 실제 로그인한 사용자의 user_id로 교체.
    const val TEST_USER_ID: String = "test-user"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    // 로그인 전에는 토큰이 없으므로 당연히 헤더를 안 붙이지만, 회원가입/로그인 요청 자체는
    // 토큰이 있어도(재로그인 등) 절대 Authorization을 붙이면 안 됨.
    private val noAuthEndpoints = setOf("signup", "login")

    // 401을 받아도 로그아웃 신호를 보내면 안 되는 엔드포인트. PATCH /users/me/password의 401은
    // "현재 비밀번호 불일치"라는 입력 오류일 뿐 세션 만료가 아니라서, 화면에 에러만 보여주면 됨.
    // (헤더는 정상적으로 붙어야 하니 noAuthEndpoints와는 별도로 관리)
    private val skipLogoutOn401Endpoints = setOf("password")

    // 백엔드가 JWT 인증으로 바뀌면서 개인화 API는 전부 Authorization 헤더가 필요해짐.
    // 1) 저장된 토큰이 있으면 (signup/login 제외) 모든 요청에 자동으로 붙여준다.
    // 2) refresh token이 없어서, 인증이 필요한 요청이 401을 받으면 세션이 만료된 것으로 보고
    //    토큰을 지운 뒤 SessionManager로 신호를 보내 앱이 로그인 화면으로 갈 수 있게 한다.
    //    (단 /login 자체가 401을 주는 건 "비밀번호 틀림"이지 세션 만료가 아니므로 제외,
    //    skipLogoutOn401Endpoints에 있는 엔드포인트도 같은 이유로 제외)
    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val lastSegment = original.url.pathSegments.lastOrNull()
        val isAuthEndpoint = lastSegment in noAuthEndpoints

        val request = if (!isAuthEndpoint) {
            val token = TokenStore.getToken()
            if (token != null) {
                original.newBuilder().addHeader("Authorization", "Bearer $token").build()
            } else {
                original
            }
        } else {
            original
        }

        val response = chain.proceed(request)

        if (response.code == 401 && !isAuthEndpoint && lastSegment !in skipLogoutOn401Endpoints) {
            TokenStore.clearSession()
            SessionManager.notifyUnauthorized()
        }

        response
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        // OkHttp 기본 타임아웃(10초)은 /generate-diary가 KoBERT 감정분석 + SD3 이미지 생성을
        // 끝낼 때까지 기다리기엔 너무 짧아서 개발 중 요청이 SocketTimeoutException으로 끊긴다.
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(150, TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val diaryApi: DiaryApi = retrofit.create(DiaryApi::class.java)
    val personalTestApi: PersonalTestApi = retrofit.create(PersonalTestApi::class.java)
    val statsApi: StatsApi = retrofit.create(StatsApi::class.java)
    val authApi: AuthApi = retrofit.create(AuthApi::class.java)
    val userApi: UserApi = retrofit.create(UserApi::class.java)
}
