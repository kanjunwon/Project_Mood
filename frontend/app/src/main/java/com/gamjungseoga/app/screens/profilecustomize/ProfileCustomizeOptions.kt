package com.gamjungseoga.app.screens.profilecustomize

// 4단계 선택지를 한 곳에 모아둬서, 단계별 질문 화면과 완료 화면(선택한 코드 -> 라벨 역변환)이
// 같은 라벨/코드를 쓰도록 한다.
val glassesOptions = listOf(
    ProfileCustomizeOption("뿔테 안경", "horn_rimmed"),
    ProfileCustomizeOption("동그란 안경", "round"),
    ProfileCustomizeOption("안경을 쓰지 않아요", "none")
)

val bangsOptions = listOf(
    ProfileCustomizeOption("앞머리가 있어요", "true"),
    ProfileCustomizeOption("앞머리가 없어요", "false")
)

val hairLengthOptions = listOf(
    ProfileCustomizeOption("긴 머리에요", "long"),
    ProfileCustomizeOption("짧은 머리에요", "short")
)

val hairColorOptions = listOf(
    ProfileCustomizeOption("검은색이에요", "black"),
    ProfileCustomizeOption("갈색이에요", "brown")
)

fun profileCustomizeOptionLabel(options: List<ProfileCustomizeOption>, code: String?): String =
    options.firstOrNull { it.code == code }?.label ?: "선택 안 함"
