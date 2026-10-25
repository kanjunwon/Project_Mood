package com.gamjungseoga.app.emotion

import android.util.Log
import androidx.annotation.DrawableRes
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.luminance
import com.gamjungseoga.app.R
import com.gamjungseoga.app.ui.theme.EmotionActive
import com.gamjungseoga.app.ui.theme.EmotionDrained
import com.gamjungseoga.app.ui.theme.EmotionExplosive
import com.gamjungseoga.app.ui.theme.EmotionRelief
import com.gamjungseoga.app.ui.theme.EmotionRising
import com.gamjungseoga.app.ui.theme.EmotionStable
import com.gamjungseoga.app.ui.theme.EmotionStagnant
import com.gamjungseoga.app.ui.theme.EmotionUnknown
import com.gamjungseoga.app.ui.theme.EmotionWary
import java.util.concurrent.ConcurrentHashMap

// backend/app/emotion_taxonomy.py의 24개 소분류 -> 8개 중분류 매핑과 같은 기준.
// 그룹마다 대표 색(디자이너 확정, 색채심리학 기준)과, SD3 생성 이미지가 아직 없는 동안
// 대신 보여줄 기존 8종 아카이브 일러스트를 같이 들고 있다.
enum class EmotionGroup(val emotions: List<String>, @param:DrawableRes val drawable: Int, val color: Color) {
    RISING(listOf("행복한", "기쁜", "기대되는", "설레는"), R.drawable.archive_happy, EmotionRising),
    ACTIVE(listOf("신나는", "열정적인", "즐거운"), R.drawable.archive_joyful, EmotionActive),
    RELIEF(listOf("상쾌한", "뿌듯한", "후련한"), R.drawable.archive_relieved, EmotionRelief),
    STABLE(listOf("감사한", "편안한"), R.drawable.archive_comfortable, EmotionStable),
    WARY(listOf("우울한", "실망한", "후회되는", "슬픈"), R.drawable.archive_depressed, EmotionWary),
    STAGNANT(listOf("두려운", "불안한", "막막한"), R.drawable.archive_anxious, EmotionStagnant),
    DRAINED(listOf("피곤한", "외로운", "지루한"), R.drawable.archive_tired, EmotionDrained),
    EXPLOSIVE(listOf("화나는", "짜증나는"), R.drawable.archive_angry, EmotionExplosive)
}

private val emotionToGroup: Map<String, EmotionGroup> =
    EmotionGroup.entries.flatMap { group -> group.emotions.map { it to group } }.toMap()

fun emotionGroupOf(emotion: String?): EmotionGroup? = emotionToGroup[emotion]

fun drawableForEmotion(emotion: String?): Int =
    emotionGroupOf(emotion)?.drawable ?: R.drawable.archive_comfortable

private const val TAG = "EmotionAssets"

// 리컴포지션마다 불려서, 같은 라벨은 한 번만 로그를 남긴다.
private val loggedUnknownEmotions = ConcurrentHashMap.newKeySet<String>()

// 감정 색을 흰 배경 위 "글자"로 쓸 때용. 안정형 연두/해소형 민트처럼 연한 색은 글자로는 읽기 어려워서,
// 흰 배경 대비 3:1(굵은 글씨 기준 최소 대비)이 될 때까지 같은 색을 조금씩 어둡게 한다. 원래 진한 색은 그대로.
fun emotionTextColorFor(emotion: String?): Color = readableOnWhite(emotionColorFor(emotion))

// emotionTextColorFor의 색 버전. 감정 이름 대신 이미 고른 감정 색을 받는 카드(EmotionSummaryCard 등)에서 씀.
fun readableOnWhite(base: Color): Color {
    var color = base
    repeat(10) {
        if (contrastOnWhite(color) >= 3f) return color
        color = lerp(color, Color.Black, 0.1f)
    }
    return color
}

private fun contrastOnWhite(color: Color): Float = 1.05f / (color.luminance() + 0.05f)

// 감정 이름 -> 그룹 색. 순위가 아니라 감정 자체로 색이 정해진다.
// 매핑에 없는 라벨이 오면 EmotionUnknown을 돌려주고 경고 로그를 남긴다(백엔드 라벨이 바뀐 걸
// 알아채기 위함). null/빈 문자열은 "감정 없음"이라 로그 없이 기본색만 돌려준다.
fun emotionColorFor(emotion: String?): Color {
    if (emotion.isNullOrBlank()) return EmotionUnknown
    emotionGroupOf(emotion)?.let { return it.color }
    if (loggedUnknownEmotions.add(emotion)) {
        Log.w(TAG, "색상 매핑에 없는 감정 라벨: \"$emotion\" (backend emotion_taxonomy 변경 여부 확인 필요)")
    }
    return EmotionUnknown
}
