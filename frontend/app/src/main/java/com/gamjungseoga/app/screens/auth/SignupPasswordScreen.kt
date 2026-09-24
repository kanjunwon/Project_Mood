package com.gamjungseoga.app.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
fun SignupPasswordScreen(
    password: String,
    passwordConfirm: String,
    onPasswordChange: (String) -> Unit,
    onPasswordConfirmChange: (String) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit
) {
    val hasUpperLower = hasUpperAndLowerCase(password)
    val hasNumber = hasDigit(password)
    val hasValidLength = hasValidPasswordLength(password)
    val passwordsMatch = passwordConfirm.isNotEmpty() && password == passwordConfirm
    val canProceed = hasUpperLower && hasNumber && hasValidLength && passwordsMatch

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        AuthTopBar(title = "회원가입", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        AuthFieldLabel("비밀번호", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = password,
            onValueChange = onPasswordChange,
            placeholder = "비밀번호를 입력해주세요",
            isPassword = true,
            showPasswordToggle = true,
            keyboardType = KeyboardType.Password,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(12.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            AuthCheckItem(text = "영문 대/소문자", satisfied = hasUpperLower)
            AuthCheckItem(text = "숫자", satisfied = hasNumber)
            AuthCheckItem(text = "8~64자", satisfied = hasValidLength)
        }

        Spacer(Modifier.height(24.dp))

        AuthFieldLabel("비밀번호 확인", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = passwordConfirm,
            onValueChange = onPasswordConfirmChange,
            placeholder = "비밀번호를 재입력해주세요",
            isPassword = true,
            showPasswordToggle = true,
            keyboardType = KeyboardType.Password,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        if (passwordConfirm.isNotEmpty() && !passwordsMatch) {
            Spacer(Modifier.height(8.dp))
            Text(
                "비밀번호가 일치하지 않아요.",
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        AuthPrimaryButton(
            text = "다음으로",
            onClick = onNext,
            enabled = canProceed,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
