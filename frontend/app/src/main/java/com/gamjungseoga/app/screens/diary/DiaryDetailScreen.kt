package com.gamjungseoga.app.screens.diary

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.gamjungseoga.app.R
import com.gamjungseoga.app.components.ConfirmDialog
import com.gamjungseoga.app.components.EmotionBadge
import com.gamjungseoga.app.components.EmotionHeroImage
import com.gamjungseoga.app.components.EmotionSummaryCard
import com.gamjungseoga.app.components.PersonPlaceInfoCard
import com.gamjungseoga.app.components.TopEmotionsBarCard
import com.gamjungseoga.app.components.topEmotionBarsFromScores
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.network.parseServerDateTimeInSeoul
import com.gamjungseoga.app.ui.theme.AccentTerracotta
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.PretendardFontFamily
import com.gamjungseoga.app.ui.theme.SurfaceColor
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val detailDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM.dd")

private fun formatDetailDate(createdAt: String?): String =
    createdAt?.let { parseServerDateTimeInSeoul(it)?.format(detailDateFormatter) } ?: "-"

// who는 "엄마, 친구"처럼 쉼표로 구분된 문자열일 수 있어서, 카드에는 첫 번째 값만 보여준다.
private fun firstWho(who: String?): String? =
    who?.split(",")?.map { it.trim() }?.firstOrNull { it.isNotEmpty() }

@Composable
fun DiaryDetailScreen(
    diaryId: Long,
    onBack: () -> Unit,
    // 확인 다이얼로그에서 "다시 작성하기"를 확정했을 때 호출(이 일기의 날짜를 들고 작성
    // 플로우로 들어가기 위함). 다이얼로그는 이 화면이 직접 띄우고, 실제 네비게이션은
    // 상위(MainActivity)에 맡긴다.
    onRewriteClick: (LocalDate) -> Unit = {},
    diaryListViewModel: DiaryListViewModel = viewModel()
) {
    val listState = diaryListViewModel.state
    val entry = (listState as? DiaryListState.Loaded)?.diaries?.firstOrNull { it.id == diaryId }
    var showRewriteDialog by remember { mutableStateOf(false) }
    // created_at에서 뽑은 날짜(서울 기준) - "다시 작성하기"로 들어갈 때 이 날짜로 고정해야 하므로
    // 미리 파싱해둔다. 파싱 실패 시(거의 없음) null이면 버튼을 숨긴다.
    val rewriteDate = entry?.let { parseServerDateTimeInSeoul(it.createdAt)?.toLocalDate() }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item { DiaryTopBar(onBack = onBack) }
        when {
            listState is DiaryListState.Loading -> item {
                Spacer(Modifier.height(24.dp))
                Text(
                    "불러오는 중...",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MonthLabelGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }
            listState is DiaryListState.Error -> item {
                Spacer(Modifier.height(24.dp))
                Text(
                    "일기를 불러오지 못했어요. (${listState.message})",
                    style = MaterialTheme.typography.bodyMedium,
                    color = BodyGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }
            entry == null -> item {
                Spacer(Modifier.height(24.dp))
                Text(
                    "해당 일기를 찾을 수 없어요.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = BodyGray,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }
            else -> {
                val diaryEntry = entry!!
                val topEmotion = diaryEntry.topEmotion.orEmpty()
                val emotionBars = topEmotionBarsFromScores(diaryEntry.emotionScores)
                val topEmotionPercent = emotionBars.firstOrNull()?.percent ?: 0
                val whoDisplay = firstWho(diaryEntry.who)
                val whereDisplay = diaryEntry.where?.trim()?.ifBlank { null }

                item {
                    Spacer(Modifier.height(8.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            formatDetailDate(diaryEntry.createdAt),
                            style = MaterialTheme.typography.titleMedium,
                            color = TitleBrown
                        )
                        EmotionBadge(topEmotion = topEmotion)
                    }
                }
                item {
                    Spacer(Modifier.height(16.dp))
                    Box(modifier = Modifier.padding(horizontal = 16.dp)) {
                        EmotionHeroImage(
                            topEmotion = topEmotion,
                            imageUrl = ApiClient.resolveImageUrl(diaryEntry.imageUrl),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
                item {
                    Spacer(Modifier.height(20.dp))
                    Text(
                        diaryEntry.generatedDiary.orEmpty(),
                        style = MaterialTheme.typography.bodyMedium.copy(fontFamily = PretendardFontFamily),
                        color = Color.Black,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
                item {
                    Spacer(Modifier.height(24.dp))
                    EmotionSummaryCard(
                        titlePrefix = "오늘 가장 많이 느낀 감정은\n",
                        emotion = topEmotion,
                        percent = topEmotionPercent,
                        fontFamily = PretendardFontFamily
                    )
                }
                item {
                    Spacer(Modifier.height(16.dp))
                    TopEmotionsBarCard(emotionBars, fontFamily = PretendardFontFamily)
                }
                if (whoDisplay != null || whereDisplay != null) {
                    item {
                        Spacer(Modifier.height(16.dp))
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            if (whoDisplay != null) {
                                PersonPlaceInfoCard(
                                    modifier = Modifier.weight(1f),
                                    iconRes = R.drawable.analysis_person_icon,
                                    prefix = "오늘 함께한 사람은",
                                    highlight = whoDisplay,
                                    fontFamily = PretendardFontFamily
                                )
                            }
                            if (whereDisplay != null) {
                                PersonPlaceInfoCard(
                                    modifier = Modifier.weight(1f),
                                    iconRes = R.drawable.analysis_location_icon,
                                    prefix = "오늘 방문한 장소는",
                                    highlight = whereDisplay,
                                    fontFamily = PretendardFontFamily
                                )
                            }
                        }
                    }
                }
                if (rewriteDate != null) {
                    item {
                        Spacer(Modifier.height(24.dp))
                        Surface(
                            onClick = { showRewriteDialog = true },
                            color = SurfaceColor,
                            shape = RoundedCornerShape(50),
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp)
                                .height(48.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                                Text(
                                    "다시 작성하기",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = AccentTerracotta
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    if (showRewriteDialog && rewriteDate != null) {
        ConfirmDialog(
            title = "일기를 다시 작성하시겠어요?",
            message = "새 일기 생성에 성공하면 지금 보고 있는 일기는 삭제돼요.",
            confirmText = "다시 작성하기",
            confirmColor = AccentTerracotta,
            onConfirm = {
                showRewriteDialog = false
                onRewriteClick(rewriteDate)
            },
            onDismiss = { showRewriteDialog = false }
        )
    }
}
