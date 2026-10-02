package com.gamjungseoga.app.network

import java.util.concurrent.TimeUnit
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    // RunPod에 띄운 백엔드 서버 주소. 포드를 재시작하면 주소가 바뀔 수 있으니 그때마다 교체.
    const val BASE_URL = "https://imje0ojskq9una-8000.proxy.runpod.net/"

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
        // /generate-diary 한 요청 안에서 LLaMA 일기 생성 -> KoBERT 감정분석 -> SD3 이미지 생성이
        // 순차 실행되어 2분을 넘기는 경우가 흔해서, readTimeout 120초로는 서버가 아직 응답 중인데
        // 클라이언트가 먼저 끊어버리는 문제가 있었다. 여유를 두고 늘림.
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(240, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(300, TimeUnit.SECONDS)
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

    // 백엔드가 이미지 URL을 전체 URL(예: Supabase Storage의 공개 URL)로 내려줄지, BASE_URL
    // 기준 상대 경로("/storage/...")로 내려줄지 아직 Swagger로 확인하지 못했다. 둘 다
    // 대응하도록, 이미 http(s)://로 시작하면 그대로 쓰고 아니면 BASE_URL을 붙여 절대 URL로
    // 만든다. 실제 형태를 확인하면 이 분기는 필요 없어질 수 있음.
    fun resolveImageUrl(url: String?): String? {
        if (url.isNullOrBlank()) return null
        if (url.startsWith("http://", ignoreCase = true) || url.startsWith("https://", ignoreCase = true)) {
            return url
        }
        return BASE_URL.trimEnd('/') + "/" + url.trimStart('/')
    }
}
