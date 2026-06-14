"""数据库模块。

本模块负责用户账号管理和分析结果存储，
使用SQLite数据库存储数据。

类:
    Database: 数据库管理类
"""

import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from seek_root.config.settings import settings


@dataclass
class User:
    """用户数据类。

    存储用户的基本信息。

    属性:
        id: 用户ID
        username: 用户名
        email: 邮箱
        password_hash: 密码哈希
        is_pro: 是否为Pro版本
        created_at: 创建时间
        last_login: 最后登录时间
    """

    id: int
    username: str
    email: str
    password_hash: str
    is_pro: bool = False
    created_at: str = ""
    last_login: Optional[str] = None


@dataclass
class AnalysisRecord:
    """分析记录数据类。

    存储用户的分析历史记录。

    属性:
        id: 记录ID
        user_id: 用户ID
        method: 使用的分析方法
        scenario: 分析场景
        config: 分析配置（JSON字符串）
        result_summary: 结果摘要（JSON字符串）
        status: 状态 (pending/completed/failed)
        created_at: 创建时间
        completed_at: 完成时间
    """

    id: int
    user_id: int
    method: str
    scenario: str
    config: str
    result_summary: str
    status: str
    created_at: str
    completed_at: Optional[str] = None


class Database:
    """数据库管理类。

    负责SQLite数据库的初始化、用户管理、分析记录存储等功能。

    参数:
        db_path (str | Path, optional): 数据库文件路径

    示例:
        >>> db = Database()
        >>> user = db.create_user("test", "test@example.com", "password123")
        >>> print(f"创建用户: {user.username}")
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """初始化数据库。

        参数:
            db_path: 数据库文件路径，默认使用配置中的路径
        """
        self.db_path = db_path or settings.get_database_path()
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self) -> None:
        """确保数据库目录存在。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接。

        返回:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """初始化数据库表结构。"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_pro INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            )
        """)

        # 创建分析记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                scenario TEXT,
                config TEXT,
                result_summary TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建用户数据表（存储用户上传的数据）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                data_preview TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        conn.close()

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """哈希密码。

        使用SHA-256对密码进行哈希，带盐。

        参数:
            password: 原始密码
            salt: 盐值，默认自动生成

        返回:
            tuple: (密码哈希, 盐值)
        """
        if salt is None:
            salt = secrets.token_hex(16)

        hash_obj = hashlib.sha256((password + salt).encode())
        password_hash = hash_obj.hexdigest()

        return password_hash, salt

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> User:
        """创建新用户。

        参数:
            username: 用户名
            email: 邮箱
            password: 密码

        返回:
            User: 创建的用户对象

        异常:
            ValueError: 用户名或邮箱已存在
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 检查是否已存在
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            raise ValueError("用户名或邮箱已存在")

        # 创建用户
        password_hash, salt = self._hash_password(password)
        full_hash = f"{salt}${password_hash}"

        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (username, email, full_hash),
        )

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return User(
            id=user_id,
            username=username,
            email=email,
            password_hash=full_hash,
            created_at=datetime.now().isoformat(),
        )

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户登录。

        参数:
            username: 用户名
            password: 密码

        返回:
            User: 验证成功返回用户对象，失败返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        # 验证密码
        stored_hash = row["password_hash"]
        salt, stored_pw_hash = stored_hash.split("$")
        _, input_pw_hash = self._hash_password(password, salt)

        if input_pw_hash != stored_pw_hash:
            conn.close()
            return None

        # 更新最后登录时间
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), row["id"]),
        )
        conn.commit()
        conn.close()

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_pro=bool(row["is_pro"]),
            created_at=row["created_at"],
            last_login=row["last_login"],
        )

    def get_user(self, user_id: int) -> Optional[User]:
        """根据ID获取用户。

        参数:
            user_id: 用户ID

        返回:
            User: 用户对象，不存在返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_pro=bool(row["is_pro"]),
            created_at=row["created_at"],
            last_login=row["last_login"],
        )

    def save_analysis_record(
        self,
        user_id: int,
        method: str,
        scenario: str,
        config: Dict[str, Any],
        result_summary: Optional[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> AnalysisRecord:
        """保存分析记录。

        参数:
            user_id: 用户ID
            method: 分析方法
            scenario: 分析场景
            config: 分析配置
            result_summary: 结果摘要
            status: 状态

        返回:
            AnalysisRecord: 创建的记录对象
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        config_json = json.dumps(config, ensure_ascii=False)
        result_json = json.dumps(result_summary, ensure_ascii=False) if result_summary else ""

        cursor.execute(
            """
            INSERT INTO analysis_records
            (user_id, method, scenario, config, result_summary, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, method, scenario, config_json, result_json, status),
        )

        record_id = cursor.lastrowid
        created_at = datetime.now().isoformat()

        conn.commit()
        conn.close()

        return AnalysisRecord(
            id=record_id,
            user_id=user_id,
            method=method,
            scenario=scenario,
            config=config_json,
            result_summary=result_json,
            status=status,
            created_at=created_at,
        )

    def get_user_analysis_records(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[AnalysisRecord]:
        """获取用户的分析记录。

        参数:
            user_id: 用户ID
            limit: 返回记录数量限制
            offset: 偏移量（分页）

        返回:
            list[AnalysisRecord]: 分析记录列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM analysis_records
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )

        rows = cursor.fetchall()
        conn.close()

        records = []
        for row in rows:
            records.append(AnalysisRecord(
                id=row["id"],
                user_id=row["user_id"],
                method=row["method"],
                scenario=row["scenario"],
                config=row["config"],
                result_summary=row["result_summary"],
                status=row["status"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
            ))

        return records


# 全局数据库实例
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """获取全局数据库实例。

    使用单例模式，确保整个应用使用同一个数据库连接。

    返回:
        Database: 数据库实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
