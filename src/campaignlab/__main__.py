"""``python -m campaignlab`` 入口（M0-02 · S3c；design §6 ``__main__.py:main``）。

命令契约来自 ``spec/CampaignLab-SDD-v1.0/framework/TOOLCHAIN.md:21``::

    uv run python -m campaignlab serve     # 启动 HTTP 与后台进程
    uv run python -m campaignlab doctor    # 检查绑定、版本、数据目录、数据库和 worker

``backup`` / ``restore`` 也在同一行契约里，但**不属 M0-02**，本文件不预建桩
（预建桩会让人误以为备份已可用）。

本文件的存在同时闭合 ADR-005 §2.4 裁定 4 的 gate 归属：``python -m campaignlab doctor``
在 S3c 之前必然 rc=1（``No module named campaignlab.__main__``），该 gate 的判定归 S3c。
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import Any

from campaignlab.cli import build_parser


def main(argv: Sequence[str] | None = None) -> int:
    """解析 argv 并派发到子命令；返回进程退出码。

    无子命令 → 打印用法并返回 **2**（用法错误），不返回 0：
    「什么都没做」被判成功会让 CI 的 gate 变成假绿。
    """
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    handler: Callable[[Any], int] | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        return 2
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
