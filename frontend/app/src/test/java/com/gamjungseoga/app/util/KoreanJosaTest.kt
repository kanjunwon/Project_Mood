package com.gamjungseoga.app.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class KoreanJosaTest {
    @Test
    fun hangulWithAndWithoutFinalConsonant() {
        assertEquals("친구는", withJosa("친구", Josa.EUN_NEUN))
        assertEquals("친구와", withJosa("친구", Josa.GWA_WA))
        assertEquals("친구예요", withJosa("친구", Josa.COPULA))
        assertEquals("집이에요", withJosa("집", Josa.COPULA))
        assertEquals("학교 앞 카페는", withJosa("학교 앞 카페", Josa.EUN_NEUN))
        assertEquals("엄마가", withJosa("엄마", Josa.I_GA))
        assertEquals("동생을", withJosa("동생", Josa.EUL_REUL))
        assertEquals("고양이를", withJosa("고양이", Josa.EUL_REUL))
    }

    @Test
    fun digitsUseKoreanReading() {
        assertEquals("1반이에요", withJosa("1반", Josa.COPULA))
        assertEquals("101호는", withJosa("101호", Josa.EUN_NEUN))
        assertEquals("방 1과", withJosa("방 1", Josa.GWA_WA)) // 일
        assertEquals("방 2와", withJosa("방 2", Josa.GWA_WA)) // 이
    }

    @Test
    fun undecidableInputFallsBackToSingleForm() {
        assertEquals("Tom는", withJosa("Tom", Josa.EUN_NEUN))
        assertEquals("🐶예요", withJosa("🐶", Josa.COPULA))
        assertEquals("와", josaFor("", Josa.GWA_WA))
        assertNull(hasFinalConsonant("   "))
    }

    @Test
    fun trailingSpacesAreIgnored() {
        assertEquals("집 이에요", withJosa("집 ", Josa.COPULA))
        assertEquals(true, hasFinalConsonant("집  "))
    }
}
