package com.gamjungseoga.app.screens.settings

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
import androidx.lifecycle.viewmodel.compose.viewModel
import com.gamjungseoga.app.screens.auth.AuthCheckItem
import com.gamjungseoga.app.screens.auth.AuthFieldLabel
import com.gamjungseoga.app.screens.auth.AuthTextField
import com.gamjungseoga.app.screens.auth.hasDigit
import com.gamjungseoga.app.screens.auth.hasUpperAndLowerCase
import com.gamjungseoga.app.screens.auth.hasValidPasswordLength
import com.gamjungseoga.app.ui.theme.MonthLabelGray

@Composable
fun PasswordChangeScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    viewModel: PasswordChangeViewModel = viewModel()
) {
    val draft = viewModel.draft
    val hasUpperLower = hasUpperAndLowerCase(draft.newPassword)
    val hasNumber = hasDigit(draft.newPassword)
    val hasValidLength = hasValidPasswordLength(draft.newPassword)
    val passwordsMatch = draft.newPasswordConfirm.isNotEmpty() && draft.newPassword == draft.newPasswordConfirm
    val canSave = draft.currentPassword.isNotEmpty() && hasUpperLower && hasNumber && hasValidLength && passwordsMatch

    val saving = viewModel.saveState is PasswordChangeSaveState.Loading
    val errorMessage = (viewModel.saveState as? PasswordChangeSaveState.Error)?.message

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
    ) {
        SettingsSubScreenTopBar(title = "비밀번호 변경", onBack = onBack)

        Spacer(Modifier.height(24.dp))

        // TODO: 피그마에는 비밀번호/비밀번호 확인 입력칸 두 개뿐인데, PATCH /users/me/password가
        // current_password도 요구해서 임시로 "현재 비밀번호" 칸을 위에 추가함. 디자이너 확인 후
        // 실제 디자인이 나오면 그에 맞게 레이아웃을 교체할 것.
        AuthFieldLabel("현재 비밀번호", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = draft.currentPassword,
            onValueChange = viewModel::setCurrentPassword,
            placeholder = "현재 비밀번호를 입력해주세요",
            isPassword = true,
            showPasswordToggle = true,
            keyboardType = KeyboardType.Password,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(24.dp))

        AuthFieldLabel("비밀번호", modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        AuthTextField(
            value = draft.newPassword,
            onValueChange = viewModel::setNewPassword,
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
            value = draft.newPasswordConfirm,
            onValueChange = viewModel::setNewPasswordConfirm,
            placeholder = "비밀번호를 재입력해주세요",
            isPassword = true,
            showPasswordToggle = true,
            keyboardType = KeyboardType.Password,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        if (draft.newPasswordConfirm.isNotEmpty() && !passwordsMatch) {
            Spacer(Modifier.height(8.dp))
            Text(
                "비밀번호가 일치하지 않아요.",
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        if (errorMessage != null) {
            Spacer(Modifier.height(8.dp))
            Text(
                errorMessage,
                style = MaterialTheme.typography.labelSmall,
                color = MonthLabelGray,
                modifier = Modifier.padding(horizontal = 16.dp)
            )
        }

        Spacer(Modifier.weight(1f))

        SettingsPrimaryButton(
            text = "변경하기",
            onClick = { viewModel.save(onSaved) },
            enabled = canSave,
            loading = saving,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        Spacer(Modifier.height(24.dp))
    }
}
