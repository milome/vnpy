# API Contract: ChartItem Resource Management

**Feature**: ChartWindow实时显示K线，修正开盘价引起的资源泄漏  
**Date**: 2025-12-02  
**Component**: `vnpy/chart/item.py`

## Overview

定义ChartItem资源管理的API契约，确保QPicture对象正确释放。

## Class: ChartItem

### Method: update_bar

**Signature**:
```python
def update_bar(self, bar: BarData) -> None
```

**Preconditions**:
- `bar` is not None
- `bar.datetime` is valid
- `self._manager` is initialized

**Postconditions**:
- Old QPicture object at index `ix` is explicitly released (if exists)
- `self._bar_picutures[ix]` is set to `None`
- `self.update()` is called to trigger repaint

**Side Effects**:
- Old QPicture object is deleted from memory
- Chart item is marked for update

**Exceptions**:
- None (method should not raise exceptions)

**Contract**:
```python
def update_bar(self, bar: BarData) -> None:
    """
    Update single bar data with explicit resource release.
    
    Contract:
    1. Get index for bar datetime
    2. If index exists:
       a. Get old QPicture object (if exists)
       b. Explicitly delete old object
       c. Set new reference to None
    3. Trigger update
    """
    ix: int | None = self._manager.get_index(bar.datetime)
    if ix is None:
        return
    
    # Contract: Explicitly release old QPicture object
    old_picture = self._bar_picutures.get(ix)
    if old_picture is not None:
        del old_picture  # ✅ Contract: Explicit deletion
    
    self._bar_picutures[ix] = None
    self.update()
```

### Method: clear_all

**Signature**:
```python
def clear_all(self) -> None
```

**Preconditions**:
- None

**Postconditions**:
- All QPicture objects in `self._bar_picutures` are explicitly released
- `self._item_picuture` is explicitly released (if exists)
- All dictionaries are cleared
- `self.update()` is called

**Side Effects**:
- All QPicture objects are deleted from memory
- Chart item is marked for update

**Exceptions**:
- None (method should not raise exceptions)

**Contract**:
```python
def clear_all(self) -> None:
    """
    Clear all data with explicit resource release.
    
    Contract:
    1. Iterate through all QPicture objects in _bar_picutures
    2. Explicitly delete each object
    3. Delete _item_picuture if exists
    4. Clear all dictionaries
    5. Trigger update
    """
    # Contract: Explicitly release all bar pictures
    for ix, picture in self._bar_picutures.items():
        if picture is not None:
            del picture  # ✅ Contract: Explicit deletion
    
    # Contract: Explicitly release item picture
    if self._item_picuture is not None:
        del self._item_picuture  # ✅ Contract: Explicit deletion
    
    self._item_picuture = None
    self._bar_picutures.clear()
    self.update()
```

## Testing Contract

### Test: update_bar_releases_old_picture

**Given**: ChartItem with existing QPicture at index 0  
**When**: update_bar() is called with new bar data  
**Then**: Old QPicture object is deleted, new reference is None

### Test: clear_all_releases_all_pictures

**Given**: ChartItem with multiple QPicture objects  
**When**: clear_all() is called  
**Then**: All QPicture objects are deleted, dictionaries are cleared

### Test: update_bar_handles_nonexistent_index

**Given**: ChartItem and bar with datetime not in manager  
**When**: update_bar() is called  
**Then**: Method returns early without error

## Performance Contract

- **Memory**: Old QPicture objects must be released within 100ms
- **CPU**: Resource release should not block UI thread
- **Stability**: No memory leaks after 24 hours of operation

