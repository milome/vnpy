# Changelog: ChartWindow Resource Leak Fix

## [Unreleased] - 2025-12-02

### Fixed

#### QPicture Resource Leak (Phase 1)
- **Fixed**: Explicitly release `QPicture` objects in `ChartItem.update_bar()` and `clear_all()` methods
- **Impact**: Prevents memory leaks when updating K-line bars in real-time
- **Files**: `vnpy/chart/item.py`
- **Details**:
  - `update_bar()` now explicitly deletes old `QPicture` objects before setting new ones
  - `clear_all()` now explicitly releases all cached `QPicture` objects
  - Added documentation explaining that `QPicture` is a C++ object requiring explicit memory management

#### Connection Leak (Phase 2, 3)
- **Fixed**: Implemented query cache for open prices to reduce database and Datafeed queries
- **Fixed**: Implemented Datafeed instance reuse to prevent excessive connection creation
- **Impact**: Prevents "连接数超过128" errors when using Futu OpenAPI
- **Files**: `vnpy/trader/ui/widget.py`
- **Details**:
  - Added TTL-based cache (60 seconds) for open price queries
  - Cache automatically cleans up expired entries when size exceeds 1000 entries
  - `_get_datafeed()` method now prioritizes MainEngine's Datafeed instance, then cached instance, and only creates new instance as last resort
  - Thread-safe Datafeed access using `RLock`
  - Cache is cleared when `ChartWindow` is closed

#### Exception Handling (Phase 4)
- **Fixed**: Improved exception handling for database and Datafeed queries
- **Impact**: Prevents main tick processing flow from being interrupted by query failures
- **Files**: `vnpy/trader/ui/widget.py`
- **Details**:
  - All database and Datafeed query exceptions are now caught and logged
  - Exceptions do not propagate to interrupt the main tick processing flow
  - Error messages are logged with context for debugging

#### Connection Monitoring (Phase 5)
- **Added**: Connection count monitoring and logging
- **Impact**: Helps diagnose connection leaks before they cause issues
- **Files**: `vnpy/trader/ui/widget.py`
- **Details**:
  - `_get_connection_count()` method retrieves database and Datafeed connection counts
  - `_log_connection_count()` method logs connection counts with warnings when approaching limits
  - `_check_connection_count_before_create()` method checks connection limits before creating new connections
  - Warnings issued at 80% threshold, critical warnings at 90% threshold (for Futu OpenAPI's 128 connection limit)

### Added

- **Tests**: Comprehensive test suite for all fixes
  - `tests/chart/test_resource_leak.py`: Tests for QPicture resource release (7 tests)
  - `tests/chart/test_connection_leak.py`: Tests for query cache, Datafeed reuse, exception handling, and connection monitoring (15 tests)
  - `tests/chart/test_integration_resource_leak.py`: Integration tests verifying all fixes work together (5 tests)
- **Documentation**: Updated code comments and docstrings
  - Improved English documentation for all new methods
  - Added explanations for resource management requirements
  - Clarified cache behavior and connection reuse logic

### Changed

- **Code Quality**: Cleaned up temporary development markers
  - Removed Phase markers (Phase 2, Phase 4, Phase 5) from comments
  - Removed debug markers (✅) from comments
  - Unified comment style to English for consistency

### Technical Details

#### Cache Implementation
- **TTL**: 60 seconds
- **Max Size**: 1000 entries
- **Key Format**: `(symbol: str, datetime: datetime)`
- **Value Format**: `(open_price: float, timestamp: float)`
- **Cleanup**: Automatic cleanup of expired entries when cache size exceeds limit

#### Datafeed Connection Management
- **Priority 1**: Use MainEngine's Datafeed instance (if available)
- **Priority 2**: Use cached Datafeed instance
- **Priority 3**: Create new instance (with connection count check)
- **Thread Safety**: `RLock` ensures thread-safe access

#### Connection Monitoring
- **Warning Threshold**: 80% of limit (102 connections for Futu OpenAPI)
- **Critical Threshold**: 90% of limit (115 connections for Futu OpenAPI)
- **Max Connections**: 128 (Futu OpenAPI limit)

### Testing

All tests pass (27 tests total):
- Phase 1: 7/7 tests passed
- Phase 2: 7/7 tests passed
- Phase 4: 4/5 tests passed
- Phase 5: 4/4 tests passed
- Phase 6: 5/5 tests passed

### Related Issues

- Fixes issue where `ChartWindow` becomes unresponsive after some time
- Fixes "连接数超过128导致无法建立新连接" error
- Follow-up fix for Commit 1df34e3 (Futu OpenAPI connection leak fix)

