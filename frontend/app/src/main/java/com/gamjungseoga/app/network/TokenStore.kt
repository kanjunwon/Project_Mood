package com.gamjungseoga.app.network

import android.content.Context
import androidx.core.content.edit
import com.gamjungseoga.app.AppContextProvider

// 로그인/회원가입 응답으로 받은 JWT와 사용자 정보를 기기에 저장해두고, ApiClient의
// AuthInterceptor가 이후 모든 요청의 Authorization 헤더에 실어 보낼 수 있게 하는 저장소.
object TokenStore {
    private const val PREFS_NAME = "auth_prefs"
    private const val KEY_TOKEN = "access_token"
    private const val KEY_USER_ID = "user_id"
    private const val KEY_NICKNAME = "nickname"

    private val prefs by lazy {
        AppContextProvider.appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun saveSession(token: String, userId: String?, nickname: String?) {
        prefs.edit {
            putString(KEY_TOKEN, token)
            putString(KEY_USER_ID, userId)
            putString(KEY_NICKNAME, nickname)
        }
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun getUserId(): String? = prefs.getString(KEY_USER_ID, null)

    fun getNickname(): String? = prefs.getString(KEY_NICKNAME, null)

    fun clearSession() {
        prefs.edit {
            remove(KEY_TOKEN)
            remove(KEY_USER_ID)
            remove(KEY_NICKNAME)
        }
    }
}
