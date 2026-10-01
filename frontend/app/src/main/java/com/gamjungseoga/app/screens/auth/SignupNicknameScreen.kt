package com.gamjungseoga.app.screens.auth

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun SignupNicknameScreen(
    nickname: String,
    onNicknameChange: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit
) {
    val hasValidLength = hasValidNicknameLength(nickname)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        AuthTopBar(title = "회원가입", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        AuthFieldLabel("닉네임", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = nickname,
            onValueChange = onNicknameChange,
            placeholder = "닉네임을 입력해주세요",
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(12.dp))

        AuthCheckItem(
            text = "2~20자",
            satisfied = hasValidLength,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.weight(1f))

        AuthPrimaryButton(
            text = "다음으로",
            onClick = onNext,
            enabled = hasValidLength,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
