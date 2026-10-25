package com.gamjungseoga.app.screens.splash

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.gamjungseoga.app.R
import com.gamjungseoga.app.ui.theme.BackgroundColor
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import kotlinx.coroutines.delay

private const val SPLASH_DURATION_MILLIS = 1500L

// 앱 시작 시 잠깐 보여주는 "감정서가" 로고 화면. 시스템 스플래시(Android 12+)는 가운데 아이콘
// 하나만 보여줄 수 있어서 문구/제목/일러스트 구성은 여기서 그리고, 시스템 스플래시는 같은 배경색의
// 빈 화면으로 둬서(themes.xml) 끊김 없이 이어지게 함. 시간이 지나면 onFinished로 홈/로그인 분기로 넘김.
@Composable
fun SplashScreen(onFinished: () -> Unit) {
    val currentOnFinished by rememberUpdatedState(onFinished)
    LaunchedEffect(Unit) {
        delay(SPLASH_DURATION_MILLIS)
        currentOnFinished()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundColor)
            .padding(horizontal = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            "감정의 페이지를 남겨보세요",
            style = MaterialTheme.typography.titleSmall,
            color = BodyGray
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "감정서가",
            style = MaterialTheme.typography.headlineSmall.copy(fontSize = 44.sp, lineHeight = 52.sp),
            color = TitleBrown
        )
        Spacer(Modifier.height(32.dp))
        // logo.png는 투명 배경의 흰색 선화라 밝은 배경에서는 안 보여서 제목과 같은 색으로 칠함
        Image(
            painter = painterResource(R.drawable.logo),
            contentDescription = null,
            colorFilter = ColorFilter.tint(TitleBrown),
            modifier = Modifier.fillMaxWidth(0.75f)
        )
    }
}
