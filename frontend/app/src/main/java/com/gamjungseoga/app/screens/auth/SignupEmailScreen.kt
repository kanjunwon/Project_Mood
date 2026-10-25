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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.MonthLabelGray

@Composable
fun SignupEmailScreen(
    email: String,
    onEmailChange: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        AuthTopBar(title = "회원가입", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        AuthFieldLabel("이메일", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = email,
            onValueChange = onEmailChange,
            placeholder = "이메일 주소를 입력해주세요",
            keyboardType = KeyboardType.Email,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(12.dp))

        // 2단계 비밀번호 조건 체크 항목(AuthCheckItem)과 같은 크기/회색
        Text(
            "로그인에 사용할 이메일 주소를 입력해주세요",
            style = MaterialTheme.typography.labelSmall,
            color = MonthLabelGray,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.weight(1f))

        AuthPrimaryButton(
            text = "다음으로",
            onClick = onNext,
            enabled = isValidEmail(email),
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
