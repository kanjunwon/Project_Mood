package com.gamjungseoga.app.screens.auth

import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown

@Composable
fun LoginScreen(
    onSignupClick: () -> Unit,
    onLoginSuccess: () -> Unit,
    viewModel: LoginViewModel = viewModel()
) {
    val state = viewModel.state
    val isLoading = state is LoginState.Loading

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        Text(
            "로그인",
            style = MaterialTheme.typography.headlineSmall,
            color = TitleBrown,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 49.dp),
            textAlign = TextAlign.Center
        )

        Spacer(Modifier.height(40.dp))

        AuthFieldLabel("이메일", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = viewModel.draft.email,
            onValueChange = viewModel::setEmail,
            placeholder = "이메일 주소를 입력해주세요",
            keyboardType = KeyboardType.Email,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(20.dp))

        AuthFieldLabel("비밀번호", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = viewModel.draft.password,
            onValueChange = viewModel::setPassword,
            placeholder = "비밀번호를 입력해주세요",
            isPassword = true,
            showPasswordToggle = true,
            keyboardType = KeyboardType.Password,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        if (state is LoginState.Error) {
            Spacer(Modifier.height(8.dp))
            Text(
                state.message,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        AuthPrimaryButton(
            text = "로그인",
            onClick = { viewModel.login(onLoginSuccess) },
            color = SolidGreen,
            enabled = !isLoading,
            loading = isLoading,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(12.dp))
        AuthPrimaryButton(
            text = "회원가입",
            onClick = onSignupClick,
            color = ButtonMint,
            enabled = !isLoading,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
