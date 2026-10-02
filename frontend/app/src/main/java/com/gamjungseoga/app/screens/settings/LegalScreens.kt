package com.gamjungseoga.app.screens.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.gamjungseoga.app.ui.theme.BodyGray
import com.gamjungseoga.app.ui.theme.TitleBrown

// TODO(실제 서비스 출시 전 교체 필요): 아래 개인정보처리방침/이용약관 본문은 법무 검토를 거치지
// 않은 임시 초안이다. 졸업 전시(데모) 목적의 플레이스홀더 텍스트이며 법적 효력이 없으니,
// 실제 서비스로 출시하기 전에 반드시 법률 자문을 받은 정식 약관으로 교체해야 한다.

private data class LegalSection(val title: String, val body: String)

@Composable
private fun LegalDocumentScreen(title: String, sections: List<LegalSection>, onBack: () -> Unit) {
    LazyColumn(modifier = Modifier.fillMaxSize()) {
        item { SettingsSubScreenTopBar(title = title, onBack = onBack) }
        items(sections) { section ->
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Text(section.title, style = MaterialTheme.typography.titleSmall, color = TitleBrown)
                Spacer(Modifier.height(8.dp))
                Text(section.body, style = MaterialTheme.typography.bodyMedium, color = BodyGray)
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
fun PrivacyPolicyScreen(onBack: () -> Unit) {
    LegalDocumentScreen(title = "개인정보처리방침", sections = privacyPolicySections, onBack = onBack)
}

@Composable
fun TermsOfServiceScreen(onBack: () -> Unit) {
    LegalDocumentScreen(title = "이용약관", sections = termsOfServiceSections, onBack = onBack)
}

private val privacyPolicySections = listOf(
    LegalSection(
        "1. 수집하는 개인정보 항목",
        "감정서가는 회원가입 및 서비스 제공을 위해 다음과 같은 정보를 수집합니다.\n" +
            "- 필수 정보: 이메일 주소, 닉네임, 비밀번호(암호화되어 저장됨)\n" +
            "- 선택 정보: 성별, 직업, 생년월일\n" +
            "- 서비스 이용 중 생성되는 정보: 작성한 일기 내용, 일기 작성 시 입력한 날짜·장소·함께한 " +
                "사람 등의 메타데이터, 감정 분석 결과(감정 분류, 감정 점수), AI가 생성한 일기 삽화 이미지"
    ),
    LegalSection(
        "2. 개인정보의 수집 및 이용 목적",
        "수집한 정보는 다음 목적을 위해서만 이용합니다.\n" +
            "- 회원 식별 및 로그인 등 계정 관리\n" +
            "- 일기 생성, 감정 분석, 감정 통계·리포트 제공 등 핵심 서비스 운영\n" +
            "- 서비스 품질 개선 및 오류 확인을 위한 통계 분석\n" +
            "수집된 정보는 위 목적 외의 용도로 이용되지 않습니다."
    ),
    LegalSection(
        "3. 개인정보의 보관 및 파기",
        "이용자의 개인정보는 회원 탈퇴 시 지체 없이 파기하는 것을 원칙으로 합니다. 다만 관계 법령에 " +
            "따라 보존할 필요가 있는 경우에는 해당 법령에서 정한 기간 동안 보관할 수 있습니다. 작성한 " +
            "일기와 감정 분석 결과 역시 회원 탈퇴 시 함께 삭제됩니다."
    ),
    LegalSection(
        "4. 이용자의 권리",
        "이용자는 설정 화면을 통해 언제든지 본인의 계정 정보를 조회·수정할 수 있으며, 계정 탈퇴를 " +
            "요청하여 본인의 개인정보와 작성한 일기의 삭제를 요청할 수 있습니다. 계정 탈퇴 외의 " +
            "개인정보 열람·정정·삭제 요청은 아래 문의처를 통해 접수할 수 있습니다."
    ),
    LegalSection(
        "5. 문의처",
        "개인정보 처리와 관련한 문의사항은 서비스 내 문의 채널을 통해 접수해 주시기 바랍니다.\n" +
            "(본 앱은 졸업 전시용 데모이며, 실제 운영 문의처는 서비스 출시 시 등록될 예정입니다.)"
    )
)

private val termsOfServiceSections = listOf(
    LegalSection(
        "1. 목적",
        "이 약관은 감정서가(이하 \"서비스\")가 제공하는 감정 일기 작성 및 감정 분석 서비스의 이용과 " +
            "관련하여 서비스와 이용자 간의 권리, 의무 및 책임 사항을 정하는 것을 목적으로 합니다."
    ),
    LegalSection(
        "2. 서비스의 내용",
        "서비스는 이용자가 입력한 질문(언제·어디서·누구와·무엇을·왜)에 대한 답변을 바탕으로 AI가 " +
            "일기를 생성하고, 생성된 일기의 감정을 분석하여 감정 통계 및 리포트를 제공합니다."
    ),
    LegalSection(
        "3. 이용자의 의무",
        "이용자는 타인의 개인정보를 무단으로 입력하거나 서비스를 본래 목적과 다르게 악용해서는 " +
            "안 됩니다. 이용자가 작성한 일기 내용에 대한 책임은 이용자 본인에게 있습니다."
    ),
    LegalSection(
        "4. 서비스의 변경 및 중단",
        "서비스는 운영상·기술상 필요에 따라 제공하는 서비스의 전부 또는 일부를 변경하거나 중단할 " +
            "수 있으며, 이 경우 사전에 공지합니다. 다만 긴급한 경우에는 사후에 공지할 수 있습니다."
    ),
    LegalSection(
        "5. 면책 조항",
        "서비스가 제공하는 감정 분석 결과는 AI 모델이 제공하는 참고용 정보이며, 전문적인 심리 상담 " +
            "이나 의학적 진단을 대체하지 않습니다. 서비스는 이용자가 감정 분석 결과만을 근거로 내린 " +
            "판단에 대해 책임을 지지 않습니다."
    )
)
