package com.gamjungseoga.app.components

import androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.abs

/**
 * 세로 스크롤 휠 피커. 가운데 행(선택된 항목)에 스냅되도록 위아래로
 * itemHeight만큼 여백을 주고, 뷰포트 중앙에 가장 가까운 아이템의 인덱스를
 * 스크롤이 멈췄을 때만 [onSelectedIndexChange]로 알려준다.
 *
 * [infinite]가 true면 실제 항목 목록을 아주 큰 가상 리스트에 반복 배치해
 * 양 끝(예: 59분→0분, 12시→1시)에서 자연스럽게 순환 스크롤되도록 한다.
 */
@Composable
fun <T> WheelPicker(
    items: List<T>,
    selectedIndex: Int,
    onSelectedIndexChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
    itemHeight: Dp = 64.dp,
    visibleCount: Int = 3,
    infinite: Boolean = true,
    itemContent: @Composable (item: T, isSelected: Boolean) -> Unit
) {
    val itemCount = items.size
    val virtualCount = if (infinite) Int.MAX_VALUE else itemCount
    val centerOffset = remember(infinite, itemCount) {
        if (infinite) (Int.MAX_VALUE / 2).let { it - it % itemCount } else 0
    }
    val initialVirtualIndex = centerOffset + selectedIndex

    val listState = rememberLazyListState(initialFirstVisibleItemIndex = initialVirtualIndex)
    val flingBehavior = rememberSnapFlingBehavior(listState)
    val sidePadding = itemHeight * (visibleCount / 2)

    val centeredVirtualIndex by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val visible = layoutInfo.visibleItemsInfo
            if (visible.isEmpty()) return@derivedStateOf initialVirtualIndex
            val viewportCenter = (layoutInfo.viewportStartOffset + layoutInfo.viewportEndOffset) / 2
            visible.minByOrNull { abs((it.offset + it.size / 2) - viewportCenter) }?.index ?: initialVirtualIndex
        }
    }

    LaunchedEffect(listState.isScrollInProgress) {
        if (!listState.isScrollInProgress) {
            val actualIndex = ((centeredVirtualIndex % itemCount) + itemCount) % itemCount
            if (actualIndex != selectedIndex) {
                onSelectedIndexChange(actualIndex)
            }
        }
    }

    LazyColumn(
        state = listState,
        flingBehavior = flingBehavior,
        modifier = modifier.height(itemHeight * visibleCount),
        contentPadding = PaddingValues(vertical = sidePadding)
    ) {
        items(virtualCount) { virtualIndex ->
            val actualIndex = ((virtualIndex % itemCount) + itemCount) % itemCount
            Box(
                modifier = Modifier
                    .fillParentMaxWidth()
                    .height(itemHeight),
                contentAlignment = Alignment.Center
            ) {
                itemContent(items[actualIndex], virtualIndex == centeredVirtualIndex)
            }
        }
    }
}
