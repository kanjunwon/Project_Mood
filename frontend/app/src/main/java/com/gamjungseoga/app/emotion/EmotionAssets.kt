package com.gamjungseoga.app.emotion

import com.gamjungseoga.app.R

// backend/app/emotion_taxonomy.py의 24개 소분류 -> 8개 중분류 매핑과 같은 기준으로,
// SD3 생성 이미지가 아직 없는 동안 기존 8종 아카이브 일러스트 중 가장 가까운 걸로 대체 표시.
private val emotionToDrawable: Map<String, Int> = buildMap {
    listOf("행복한", "기쁜", "기대되는", "설레는").forEach { put(it, R.drawable.archive_happy) }
    listOf("신나는", "열정적인", "즐거운").forEach { put(it, R.drawable.archive_joyful) }
    listOf("상쾌한", "뿌듯한", "후련한").forEach { put(it, R.drawable.archive_relieved) }
    listOf("감사한", "편안한").forEach { put(it, R.drawable.archive_comfortable) }
    listOf("우울한", "실망한", "후회되는", "슬픈").forEach { put(it, R.drawable.archive_depressed) }
    listOf("두려운", "불안한", "막막한").forEach { put(it, R.drawable.archive_anxious) }
    listOf("피곤한", "외로운", "지루한").forEach { put(it, R.drawable.archive_tired) }
    listOf("화나는", "짜증나는").forEach { put(it, R.drawable.archive_angry) }
}

fun drawableForEmotion(emotion: String?): Int =
    emotionToDrawable[emotion] ?: R.drawable.archive_comfortable
