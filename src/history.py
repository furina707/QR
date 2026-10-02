# -*- coding: utf-8 -*-
"""历史记录管理模块 (History Manager with JSON Persistence)

负责存储、检索、导出及清理所有扫描与生成的二维码记录。
持久化存储采用标准 JSON 格式，保存在 data/history.json 中。
"""

from __future__ import annotations

import csv
from datetime import datetime
import json
import os
import uuid
from typing import Dict, List, Optional

from .constants import HISTORY_FILE
from .utils import is_url


class HistoryRecord:
    def __init__(
        self,
        record_id: str,
        timestamp: str,
        source: str,
        content: str,
        engine: str = "",
        is_url_val: Optional[bool] = None,
    ):
        self.record_id = record_id
        self.timestamp = timestamp
        self.source = source
        self.content = content
        self.engine = engine
        self.is_url = is_url(content) if is_url_val is None else is_url_val

    def to_dict(self) -> Dict:
        return {
            "id": self.record_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "content": self.content,
            "engine": self.engine,
            "is_url": self.is_url,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> HistoryRecord:
        return cls(
            record_id=data.get("id", str(uuid.uuid4())[:8]),
            timestamp=data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            source=data.get("source", "未知"),
            content=data.get("content", ""),
            engine=data.get("engine", ""),
            is_url_val=data.get("is_url"),
        )


class HistoryManager:
    def __init__(self, file_path: str = HISTORY_FILE):
        self.file_path = file_path
        self._records: List[HistoryRecord] = []
        self._load()

    def _load(self) -> None:
        """从 JSON 文件加载历史记录"""
        if not os.path.exists(self.file_path):
            self._records = []
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._records = [HistoryRecord.from_dict(item) for item in data]
        except Exception:
            self._records = []

    def _save(self) -> None:
        """保存历史记录到 JSON 文件"""
        try:
            data = [rec.to_dict() for rec in self._records]
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_record(self, source: str, content: str, engine: str = "") -> HistoryRecord:
        """添加一条新记录（去重连续重复记录）"""
        content_clean = content.strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 若最新一条记录内容完全相同且时间在一秒内，则不重复添加
        if self._records:
            last = self._records[0]
            if last.content == content_clean and last.source == source:
                return last

        rec = HistoryRecord(
            record_id=str(uuid.uuid4())[:8],
            timestamp=now_str,
            source=source,
            content=content_clean,
            engine=engine,
        )
        # 最新的插入在最前
        self._records.insert(0, rec)
        # 最多保存 500 条
        if len(self._records) > 500:
            self._records = self._records[:500]
        self._save()
        return rec

    def get_records(self, filter_source: Optional[str] = None) -> List[HistoryRecord]:
        """获取历史记录列表，可按来源分类筛选"""
        if not filter_source or filter_source == "全部":
            return list(self._records)
        return [r for r in self._records if r.source == filter_source]

    def delete_record(self, record_id: str) -> bool:
        """删除指定 ID 的记录"""
        init_len = len(self._records)
        self._records = [r for r in self._records if r.record_id != record_id]
        if len(self._records) < init_len:
            self._save()
            return True
        return False

    def clear(self) -> None:
        """清空所有历史记录"""
        self._records = []
        self._save()

    def export_to_txt(self, target_path: str) -> bool:
        """导出历史记录为纯文本文件"""
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(f"=== QR 智能工作台 - 历史记录导出 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n\n")
                for r in self._records:
                    f.write(f"[{r.timestamp}] [{r.source}] {r.content}\n")
            return True
        except Exception:
            return False

    def export_to_csv(self, target_path: str) -> bool:
        """导出历史记录为 CSV 格式表格"""
        try:
            with open(target_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "时间", "来源", "内容", "是否为链接", "识别引擎"])
                for r in self._records:
                    writer.writerow([r.record_id, r.timestamp, r.source, r.content, "是" if r.is_url else "否", r.engine])
            return True
        except Exception:
            return False

    def export_to_json(self, target_path: str) -> bool:
        """导出历史记录为 JSON 文件"""
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                data = [r.to_dict() for r in self._records]
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


# 全局历史管理器单例
history_manager = HistoryManager()
