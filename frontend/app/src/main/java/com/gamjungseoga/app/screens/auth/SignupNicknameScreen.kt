package com.gamjungseoga.app.screens.auth

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.MonthLabelGray

@Composable
fun SignupNicknameScreen(
    nickname: String,
    onNicknameChange: (String) -> Unit,
    submitState: SignupSubmitState,
    onBack: () -> Unit,
    onSubmit: () -> Unit
) {
    val hasValidLength = hasValidNicknameLength(nickname)
    val isLoading = submitState is SignupSubmitState.Loading

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

        if (submitState is SignupSubmitState.Error) {
            Spacer(Modifier.height(8.dp))
            Text(
                submitState.message,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        AuthPrimaryButton(
            text = "완료하고 로그인 화면으로 돌아가기",
            onClick = onSubmit,
            enabled = hasValidLength && !isLoading,
            loading = isLoading,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
