package com.gamjungseoga.app.screens.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.network.ApiClient
import com.gamjungseoga.app.ui.theme.ButtonMint
import com.gamjungseoga.app.ui.theme.CalendarCellGray
import com.gamjungseoga.app.ui.theme.CountLabelBrown
import com.gamjungseoga.app.ui.theme.MonthLabelGray
import com.gamjungseoga.app.ui.theme.NavInactiveGray
import com.gamjungseoga.app.ui.theme.SolidGreen
import com.gamjungseoga.app.ui.theme.TitleBrown
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeoutException
import retrofit2.HttpException

// 로그인/회원가입 화면 전용 공용 UI 조각들. DiaryTopBar/DiaryNextButton과 같은 톤을 쓰되,
// 일기 작성 플로우 전용 컴포넌트를 재사용하기엔 제목/색상이 화면마다 달라서 별도로 둠.

private val authTopBarTextOffset = 49.dp // DiaryTopBar와 동일한 상단 여백 기준

@Composable
fun AuthTopBar(title: String, onBack: (() -> Unit)? = null) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(authTopBarTextOffset + 24.dp)
            .padding(horizontal = 8.dp)
    ) {
        if (onBack != null) {
            IconButton(
                onClick = onBack,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(top = authTopBarTextOffset - 12.dp)
            ) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "뒤로", tint = TitleBrown)
            }
        }
        Text(
            title,
            style = MaterialTheme.typography.titleMedium,
            color = TitleBrown,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = authTopBarTextOffset)
        )
    }
}

@Composable
fun AuthFieldLabel(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.labelSmall, color = CountLabelBrown, modifier = modifier)
}

@Composable
fun AuthTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
    isPassword: Boolean = false,
    // 비밀번호 입력칸 중에서도 눈 아이콘 토글이 필요한 곳(로그인/회원가입 비밀번호)에서만 켠다.
    showPasswordToggle: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text
) {
    // 비밀번호 확인칸 등 같은 화면에 여러 개가 있어도 서로 독립적으로 토글되도록 각 인스턴스가
    // 자기 상태를 들고 있음.
    var isPasswordVisible by remember { mutableStateOf(false) }
    val maskInput = isPassword && !isPasswordVisible

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(50))
            .background(CalendarCellGray)
            .padding(
                start = 20.dp,
                end = if (isPassword && showPasswordToggle) 12.dp else 20.dp,
                top = 16.dp,
                bottom = 16.dp
            )
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.weight(1f)) {
                BasicTextField(
                    value = value,
                    onValueChange = onValueChange,
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodyMedium.copy(color = Color.Black),
                    cursorBrush = SolidColor(TitleBrown),
                    keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
                    visualTransformation = if (maskInput) PasswordVisualTransformation() else VisualTransformation.None,
                    decorationBox = { innerTextField ->
                        if (value.isEmpty()) {
                            Text(
                                placeholder,
                                style = MaterialTheme.typography.bodyMedium,
                                color = NavInactiveGray
                            )
                        }
                        innerTextField()
                    }
                )
            }
            if (isPassword && showPasswordToggle) {
                // TODO: 디자이너가 전용 눈 아이콘을 준비 중 - 받으면 머티리얼 기본 아이콘 대신 교체
                IconButton(
                    onClick = { isPasswordVisible = !isPasswordVisible },
                    modifier = Modifier.size(24.dp)
                ) {
                    Icon(
                        imageVector = if (isPasswordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                        contentDescription = if (isPasswordVisible) "비밀번호 숨기기" else "비밀번호 보기",
                        tint = MonthLabelGray
                    )
                }
            }
        }
    }
}

@Composable
fun AuthPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    color: Color = ButtonMint,
    enabled: Boolean = true,
    loading: Boolean = false
) {
    Surface(
        onClick = onClick,
        enabled = enabled && !loading,
        color = if (enabled) color else color.copy(alpha = 0.5f),
        shape = RoundedCornerShape(32.dp),
        modifier = modifier
            .fillMaxWidth()
            .height(64.dp)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            if (loading) {
                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(24.dp))
            } else {
                Text(text, style = MaterialTheme.typography.titleMedium, color = Color.White)
            }
        }
    }
}

@Composable
fun AuthCheckItem(text: String, satisfied: Boolean, modifier: Modifier = Modifier) {
    val color = if (satisfied) SolidGreen else MonthLabelGray
    Row(verticalAlignment = Alignment.CenterVertically, modifier = modifier) {
        Box(
            modifier = Modifier
                .size(14.dp)
                .background(color, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Filled.Check, contentDescription = null, tint = Color.White, modifier = Modifier.size(10.dp))
        }
        Spacer(Modifier.width(6.dp))
        Text(text, style = MaterialTheme.typography.labelSmall, color = color)
    }
}

// 이메일/비밀번호/닉네임 형식 검증 (회원가입 화면 전용, 서버 호출 없이 클라이언트에서만 확인)
private val emailRegex = Regex("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

fun isValidEmail(email: String): Boolean = emailRegex.matches(email.trim())

fun hasUpperAndLowerCase(password: String): Boolean =
    password.any { it.isUpperCase() } && password.any { it.isLowerCase() }

fun hasDigit(password: String): Boolean = password.any { it.isDigit() }

fun hasValidPasswordLength(password: String): Boolean = password.length in 8..64

fun hasValidNicknameLength(nickname: String): Boolean = nickname.length in 2..20

// 로그인/회원가입 화면 공용 네트워크 에러 문구 (DiaryViewModel.describeError와 같은 패턴)
fun describeAuthError(e: Exception): String = when (e) {
    is UnknownHostException -> "서버 주소를 찾을 수 없어요 (${ApiClient.BASE_URL}). 백엔드가 켜져 있는지 확인해주세요."
    is ConnectException -> "서버에 연결할 수 없어요 (${ApiClient.BASE_URL}). 백엔드 서버가 실행 중인지 확인해주세요."
    is SocketTimeoutException, is TimeoutException ->
        "서버 응답이 너무 오래 걸려요 (타임아웃). 백엔드가 응답하는지 확인해주세요."
    is HttpException -> {
        if (e.code() == 401) {
            "이메일 또는 비밀번호가 올바르지 않아요."
        } else {
            val body = e.response()?.errorBody()?.string()?.take(300)
            "서버 오류 (HTTP ${e.code()})" + if (!body.isNullOrBlank()) ": $body" else ""
        }
    }
    else -> e.message ?: "요청에 실패했어요 (${e::class.simpleName})."
}
