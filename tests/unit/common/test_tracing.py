"""common.tracing 单元测试"""

from common.tracing import (
    get_logger,
    get_task_id,
    get_tenant_id,
    get_trace_id,
    new_trace_id,
    trace_context,
)


class TestTraceId:
    def test_new_trace_id_format(self):
        """trace_id 格式为 trace-{16位十六进制}"""
        trace_id = new_trace_id()
        assert trace_id.startswith("trace-")
        assert len(trace_id) == 6 + 16  # "trace-" + 16 hex chars

    def test_new_trace_id_uniqueness(self):
        """每次生成的 trace_id 唯一"""
        ids = [new_trace_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_trace_id_starts_empty(self):
        """初始 trace_id 为空"""
        assert get_trace_id() == ""

    def test_trace_context_sets_trace_id(self):
        """trace_context 设置 trace_id"""
        with trace_context(trace_id="trace-test123") as tid:
            assert tid == "trace-test123"
            assert get_trace_id() == "trace-test123"
        # 退出后恢复
        assert get_trace_id() == ""

    def test_trace_context_nested(self):
        """嵌套 trace_context"""
        with trace_context(trace_id="trace-outer") as _outer_id:
            assert get_trace_id() == "trace-outer"
            with trace_context(trace_id="trace-inner") as inner_id:
                assert inner_id == "trace-inner"
                assert get_trace_id() == "trace-inner"  # 内部覆盖
            assert get_trace_id() == "trace-outer"  # 恢复外部
        assert get_trace_id() == ""


class TestTraceContextFields:
    def test_trace_context_sets_all_fields(self):
        """trace_context 设置所有字段"""
        with trace_context(
            trace_id="trace-full",
            task_id="task-001",
            tenant_id="tenant-001",
            module="test-module",
        ):
            assert get_trace_id() == "trace-full"
            assert get_task_id() == "task-001"
            assert get_tenant_id() == "tenant-001"

    def test_trace_context_auto_generates_trace_id(self):
        """trace_context 自动生成 trace_id"""
        with trace_context() as tid:
            assert tid.startswith("trace-")


class TestLogger:
    def test_get_logger_basic(self):
        """获取日志器基本功能"""
        log = get_logger("test")
        assert log is not None

    def test_get_logger_with_bindings(self):
        """日志器绑定额外字段"""
        log = get_logger("test", employee_id="agent-001", action="test")
        assert log is not None

    def test_logger_in_context(self):
        """在 trace_context 中获取日志"""
        with trace_context(trace_id="trace-logtest", task_id="task-001"):
            log = get_logger("test")
            assert log is not None
