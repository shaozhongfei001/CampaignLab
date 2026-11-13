"""领域值类型与业务时区（M0-02 · S3c；design §2 末两条 / §6）。

任务卡「禁止」条与 PYTHON.md 的口径在这里落成类型：

- **金额＝分整数**（``Cents``）：任何位置禁止 ``float``，换算只在展示层做；
- **比率＝十进制字符串**（``RatioStr``）：如 ``"0.1250"``，避免二进制浮点误差进入账目；
- **时区＝``Asia/Shanghai``**：持久层时刻统一 UTC，业务日期／月份按本时区投影。

M0-02 的 5 个 operation **没有**金额／比率字段；本文件先把口径建立起来供 M1+ 复用，
不预建任何转换器，以免与后续里程碑各造一份。
"""

from __future__ import annotations

from typing import Final
from zoneinfo import ZoneInfo

__all__ = ["TZ_SHANGHAI", "Cents", "RatioStr"]

#: 人民币**分**（整数）。design §2：``Cents = int``，禁 float。
Cents = int

#: 十进制字符串比率（如 ``"0.1250"``）。design §2：``RatioStr = str``，禁 float。
RatioStr = str

#: 全项目唯一业务时区（任务卡「时区 Asia/Shanghai」）。
TZ_SHANGHAI: Final = ZoneInfo("Asia/Shanghai")
