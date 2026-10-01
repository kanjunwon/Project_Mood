package com.gamjungseoga.app.screens.diary

import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.R
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown
import kotlinx.coroutines.delay

// 경과 시간(초) 기준으로 바뀌는 안내 문구. 실제 서버 진행 상황을 알 수 없어
// (이미지 생성이 보통 97~98초 소요) 경험적으로 잡은 구간이며, 필요하면 여기만 조정하면 된다.
private data class GeneratingPhrase(val atSeconds: Int, val text: String)

private val generatingPhrases = listOf(
    GeneratingPhrase(0, "작성한 일기를 바탕으로\n감정 일기를 생성하고 있어요"),
    GeneratingPhrase(20, "감정을 분석하고 있어요"),
    GeneratingPhrase(35, "감정에 어울리는 그림을\n그리고 있어요"),
    GeneratingPhrase(90, "거의 다 됐어요\n조금만 기다려주세요")
)

private const val MAX_RETRIES = 2
private const val TICK_MILLIS = 200L

// 100초 동안 0 -> 0.9까지 선형으로 차오르고, 100초가 지나도 응답이 없으면
// 0.9에서 초당 아주 조금씩만(0.97 한도) 움직여 멈춘 것처럼 보이지 않게 한다.
private const val PROGRESS_RAMP_SECONDS = 100f
private const val PROGRESS_RAMP_CAP = 0.9f
private const val PROGRESS_CRAWL_CAP = 0.97f
private const val PROGRESS_CRAWL_RATE_PER_SECOND = 0.0015f

private fun progressForElapsed(elapsedSeconds: Float): Float {
    return if (elapsedSeconds <= PROGRESS_RAMP_SECONDS) {
        (elapsedSeconds / PROGRESS_RAMP_SECONDS) * PROGRESS_RAMP_CAP
    } else {
        val crawl = (elapsedSeconds - PROGRESS_RAMP_SECONDS) * PROGRESS_CRAWL_RATE_PER_SECOND
        (PROGRESS_RAMP_CAP + crawl).coerceAtMost(PROGRESS_CRAWL_CAP)
    }
}

@Composable
fun DiaryGeneratingScreen(
    diaryViewModel: DiaryViewModel,
    onComplete: () -> Unit,
    onExit: () -> Unit
) {
    val generationState = diaryViewModel.generationState

    var attempt by remember { mutableStateOf(0) }
    var retryCount by remember { mutableStateOf(0) }
    var elapsedSeconds by remember { mutableStateOf(0f) }

    // attempt가 바뀔 때마다(최초 진입 + 재시도) 요청을 다시 보내고 경과 시간 측정을 처음부터 시작한다.
    LaunchedEffect(attempt) {
        elapsedSeconds = 0f
        diaryViewModel.submitDiary()
        val startMillis = System.currentTimeMillis()
        while (diaryViewModel.generationState is DiaryGenerationState.Loading) {
            delay(TICK_MILLIS)
            elapsedSeconds = (System.currentTimeMillis() - startMillis) / 1000f
        }
    }

    // 성공한 경우에만 다음 화면으로 자동 진행. 실패는 이 화면에 머물러 에러 상태를 보여준다.
    LaunchedEffect(generationState) {
        if (generationState is DiaryGenerationState.Success) {
            delay(500)
            onComplete()
        }
    }

    val rawProgress = if (generationState is DiaryGenerationState.Success) {
        1f
    } else {
        progressForElapsed(elapsedSeconds)
    }
    val animatedProgress by animateFloatAsState(
        targetValue = rawProgress,
        animationSpec = tween(durationMillis = 300, easing = LinearEasing),
        label = "diaryGeneratingProgress"
    )
    val currentPhraseText = remember(elapsedSeconds) {
        generatingPhrases.last { elapsedSeconds >= it.atSeconds }.text
    }
    val errorState = generationState as? DiaryGenerationState.Error

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        DiaryTopBar()
        Spacer(Modifier.weight(1f))
        Image(
            painter = painterResource(R.drawable.header_illustration),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .padding(horizontal = 32.dp)
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(24.dp))
        )
        Spacer(Modifier.height(32.dp))

        if (errorState != null) {
            DiaryGeneratingErrorContent(
                message = errorState.message,
                canRetry = retryCount < MAX_RETRIES,
                onRetry = {
                    retryCount++
                    attempt++
                },
                onExit = onExit
            )
        } else {
            Crossfade(
                targetState = currentPhraseText,
                animationSpec = tween(durationMillis = 600),
                label = "diaryGeneratingPhrase"
            ) { text ->
                Text(
                    text,
                    style = MaterialTheme.typography.headlineSmall,
                    color = TitleBrown,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(horizontal = 32.dp)
                )
            }
            Spacer(Modifier.height(24.dp))
            LinearProgressIndicator(
                progress = { animatedProgress },
                modifier = Modifier
                    .padding(horizontal = 32.dp)
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(RoundedCornerShape(16.dp)),
                color = SolidGreen
            )
        }
        Spacer(Modifier.weight(1f))
    }
}

@Composable
private fun DiaryGeneratingErrorContent(
    message: String,
    canRetry: Boolean,
    onRetry: () -> Unit,
    onExit: () -> Unit
) {
    Text(
        "일기 생성에 실패했어요",
        style = MaterialTheme.typography.headlineSmall,
        color = TitleBrown,
        textAlign = TextAlign.Center,
        modifier = Modifier.padding(horizontal = 32.dp)
    )
    Spacer(Modifier.height(8.dp))
    Text(
        message,
        style = MaterialTheme.typography.bodyMedium,
        color = BodyGray,
        textAlign = TextAlign.Center,
        modifier = Modifier.padding(horizontal = 32.dp)
    )
    Spacer(Modifier.height(24.dp))
    if (canRetry) {
        DiaryGeneratingActionButton(text = "다시 시도하기", onClick = onRetry, filled = true)
        Spacer(Modifier.height(12.dp))
    }
    DiaryGeneratingActionButton(text = "돌아가기", onClick = onExit, filled = false)
}

@Composable
private fun DiaryGeneratingActionButton(text: String, onClick: () -> Unit, filled: Boolean) {
    Surface(
        onClick = onClick,
        color = if (filled) SolidGreen else SurfaceColor,
        border = if (filled) null else BorderStroke(1.dp, SolidGreen),
        shape = RoundedCornerShape(32.dp),
        modifier = Modifier
            .padding(horizontal = 32.dp)
            .fillMaxWidth()
            .height(56.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Text(
                text,
                style = MaterialTheme.typography.titleMedium,
                color = if (filled) Color.White else SolidGreen
            )
        }
    }
}
