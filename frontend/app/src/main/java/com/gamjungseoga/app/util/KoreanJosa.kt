package com.gamjungseoga.app.util

// 사람/장소/감정 이름처럼 화면에 끼워 넣는 단어 뒤에 붙일 조사를 받침 유무로 고른다.
// "기타"로 직접 입력한 값(영어, 숫자, 이모지 등)도 들어오므로, 받침을 판별할 수 없으면
// 받침 없는 쪽 단일 형태(예: "Tom는")를 쓴다. 병기형 "은(는)"은 화면에서 더 어색해 보여서 쓰지 않음.
enum class Josa(val withFinal: String, val withoutFinal: String, val unknown: String) {
    EUN_NEUN("은", "는", "는"),
    I_GA("이", "가", "가"),
    GWA_WA("과", "와", "와"),
    EUL_REUL("을", "를", "를"),
    COPULA("이에요", "예요", "예요")
}

// 숫자로 끝나는 경우 한국어로 읽는 소리 기준(0 영, 1 일, 3 삼, 6 육, 7 칠, 8 팔은 받침 있음)
private val digitHasFinal = mapOf(
    '0' to true, '1' to true, '2' to false, '3' to true, '4' to false,
    '5' to false, '6' to true, '7' to true, '8' to true, '9' to false
)

// 마지막 글자에 받침이 있으면 true, 없으면 false, 판별할 수 없으면(영어/이모지/기호 등) null
fun hasFinalConsonant(word: String): Boolean? {
    val last = word.trimEnd().lastOrNull() ?: return null
    return when (last) {
        in '가'..'힣' -> (last - '가') % 28 != 0
        in '0'..'9' -> digitHasFinal.getValue(last)
        else -> null
    }
}

// word 뒤에 붙일 조사만 돌려준다. 단어와 조사를 다른 스타일로 그려야 할 때(강조 색 등) 사용.
fun josaFor(word: String, josa: Josa): String = when (hasFinalConsonant(word)) {
    true -> josa.withFinal
    false -> josa.withoutFinal
    null -> josa.unknown
}

// "친구" + EUN_NEUN -> "친구는", "집" + COPULA -> "집이에요"
fun withJosa(word: String, josa: Josa): String = word + josaFor(word, josa)
