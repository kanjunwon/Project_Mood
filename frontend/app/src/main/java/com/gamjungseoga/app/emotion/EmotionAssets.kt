package com.gamjungseoga.app.emotion

import android.util.Log
import androidx.annotation.DrawableRes
import androidx.compose.ui.graphics.Color
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
