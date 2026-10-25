package com.gamjungseoga.app.screens.splash

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.decode.ImageDecoderDecoder
import com.gamjungseoga.app.R
import com.gamjungseoga.app.ui.theme.BackgroundColor
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.TitleBrown
import kotlinx.coroutines.delay

// res/raw/logo.gif: 4프레임 x 0.25초 = 한 바퀴 1초, 무한 반복. GIF가 실제로 뜬 시점부터 2바퀴(2초)를
// 보여주고 넘어간다. 디코딩이 늦거나 실패해도 3초를 넘기지 않도록 전체 상한을 따로 둠.
private const val GIF_PLAY_MILLIS = 2000L
private const val SPLASH_MAX_MILLIS = 3000L

// 앱 시작 시 잠깐 보여주는 "감정서가" 로고 화면. 시스템 스플래시(Android 12+)는 가운데 아이콘
// 하나만 보여줄 수 있어서 문구/제목/일러스트 구성은 여기서 그리고, 시스템 스플래시는 같은 배경색의
// 빈 화면으로 둬서(themes.xml) 끊김 없이 이어지게 함. 시간이 지나면 onFinished로 홈/로그인 분기로 넘김.
@Composable
fun SplashScreen(onFinished: () -> Unit) {
    val context = LocalContext.current
    val currentOnFinished by rememberUpdatedState(onFinished)
    var gifShown by remember { mutableStateOf(false) }
    var finished by remember { mutableStateOf(false) }
    val finishOnce = {
        if (!finished) {
            finished = true
            currentOnFinished()
        }
    }

    // Coil 기본 로더는 GIF를 첫 프레임만 정지 이미지로 그려서, 애니메이션 디코더를 등록한 로더를 따로 둠.
    // minSdk 33이라 GifDecoder(API 28 미만용) 대신 플랫폼 ImageDecoder 기반 디코더를 씀 (둘 다 coil-gif).
    // 스플래시에서만 쓰므로 앱 전역 로더로 올리지 않고 여기서만 만든다.
    val gifImageLoader = remember(context) {
        ImageLoader.Builder(context)
            .components { add(ImageDecoderDecoder.Factory()) }
            .build()
    }

    LaunchedEffect(Unit) {
        delay(SPLASH_MAX_MILLIS)
        finishOnce()
    }
    LaunchedEffect(gifShown) {
        if (gifShown) {
            delay(GIF_PLAY_MILLIS)
            finishOnce()
        }
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
        // GIF 자체에 선 색(초록)이 들어있어서 PNG 때처럼 tint하지 않고 원본 그대로 보여줌.
        // 로딩 전에도 자리가 흔들리지 않게 원본 비율(1465x1564)로 공간을 잡아둠.
        AsyncImage(
            model = R.raw.logo,
            imageLoader = gifImageLoader,
            contentDescription = null,
            onSuccess = { gifShown = true },
            // 실패해도 화면이 번쩍 넘어가지 않게 성공 때와 같은 시간만큼 문구/제목을 보여주고 넘어감
            onError = { gifShown = true },
            modifier = Modifier
                .fillMaxWidth(0.75f)
                .aspectRatio(1465f / 1564f)
        )
    }
}
