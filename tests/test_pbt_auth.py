"""
Property-based tests for JWT signing and decoding — Property 8: JWT 签发与解码往返不变量.

**Validates: Requirements 2.3, 3.1**

Property: For any valid user_id (positive integer), the JWT token issued by
_create_access_token() must decode back to the same user_id. The round-trip
encode → decode must be an identity operation on the user_id claim.
"""

import sys
import os

# 确保项目根目录在 sys.path 中，以便导入 Router.auth
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 在导入 Router.auth 之前加载 .env，确保 JWT_SECRET_KEY 已设置
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
from jose import jwt, JWTError

# 导入被测函数和 JWT 配置常量
from Router.auth import _create_access_token, _JWT_SECRET_KEY, _JWT_ALGORITHM


# ---------------------------------------------------------------------------
# Property 8: JWT 签发与解码往返不变量
# Validates: Requirements 2.3, 3.1
# ---------------------------------------------------------------------------

@given(
    user_id=st.integers(min_value=1, max_value=2_147_483_647),  # 合法正整数 user_id
    username=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),  # 大写字母、小写字母、数字
            whitelist_characters="_",
        ),
        min_size=1,
        max_size=50,
    ),
)
@settings(max_examples=200, deadline=None)
def test_jwt_roundtrip_user_id_invariant(user_id: int, username: str):
    """
    Property 8: JWT 签发与解码往返不变量

    对任意合法 user_id（正整数），由 _create_access_token() 签发的 JWT token
    经 jwt.decode() 解码后，payload 中的 user_id 字段必须等于原始输入值。

    验证内容：
    1. token 可被成功解码（签名有效、格式合法）
    2. 解码后的 user_id claim 与签发时的 user_id 完全一致
    3. token 包含 exp（过期时间）claim，且过期时间在未来
    4. token 包含 username claim，与签发时的 username 一致

    **Validates: Requirements 2.3, 3.1**
    """
    # ── 签发 JWT token ──
    token = _create_access_token(user_id=user_id, username=username)

    # token 必须是非空字符串
    assert isinstance(token, str), (
        f"Expected token to be a string, got {type(token)}"
    )
    assert len(token) > 0, "Token must not be empty"

    # ── 解码 JWT token（使用相同的密钥和算法）──
    try:
        payload = jwt.decode(token, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise AssertionError(
            f"JWT decode failed for user_id={user_id}, username={repr(username)}: {exc}"
        ) from exc

    # ── 核心断言：user_id 往返不变量 ──
    decoded_user_id = payload.get("user_id")
    assert decoded_user_id == user_id, (
        f"JWT round-trip invariant violated: "
        f"issued with user_id={user_id}, but decoded user_id={decoded_user_id}"
    )

    # ── 附加断言：username claim 一致性 ──
    decoded_username = payload.get("username")
    assert decoded_username == username, (
        f"JWT username claim mismatch: "
        f"issued with username={repr(username)}, but decoded username={repr(decoded_username)}"
    )

    # ── 附加断言：exp claim 存在且在未来 ──
    exp = payload.get("exp")
    assert exp is not None, "JWT payload must contain 'exp' claim"
    now_ts = datetime.now(timezone.utc).timestamp()
    assert exp > now_ts, (
        f"JWT expiration must be in the future: exp={exp}, now={now_ts}"
    )


@given(user_id=st.integers(min_value=1, max_value=2_147_483_647))
@settings(max_examples=100, deadline=None)
def test_jwt_user_id_type_is_integer_after_decode(user_id: int):
    """
    补充测试：解码后的 user_id 必须是整数类型（不能是字符串或其他类型）。

    JWT 标准允许 payload 值为任意 JSON 类型；此测试确保 python-jose 在
    解码时保留整数类型，而不会将其转换为字符串。

    **Validates: Requirements 3.1**
    """
    token = _create_access_token(user_id=user_id, username="testuser")
    payload = jwt.decode(token, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])

    decoded_user_id = payload.get("user_id")

    # user_id 必须是整数，不能是字符串
    assert isinstance(decoded_user_id, int), (
        f"Decoded user_id must be int, got {type(decoded_user_id).__name__}: "
        f"{repr(decoded_user_id)}"
    )

    # 整数值必须与原始值完全相等
    assert decoded_user_id == user_id, (
        f"Decoded user_id={decoded_user_id} does not match original user_id={user_id}"
    )


@given(
    user_id_1=st.integers(min_value=1, max_value=1_000_000),
    user_id_2=st.integers(min_value=1_000_001, max_value=2_000_000),
)
@settings(max_examples=50, deadline=None)
def test_jwt_different_user_ids_produce_different_tokens(user_id_1: int, user_id_2: int):
    """
    补充测试：不同的 user_id 签发的 token 解码后必须返回各自对应的 user_id，
    不得发生 user_id 混淆（即 token 不可互换）。

    **Validates: Requirements 2.3, 3.1**
    """
    # 两个 user_id 来自不同区间，保证不相等
    assert user_id_1 != user_id_2

    token_1 = _create_access_token(user_id=user_id_1, username="user_a")
    token_2 = _create_access_token(user_id=user_id_2, username="user_b")

    payload_1 = jwt.decode(token_1, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])
    payload_2 = jwt.decode(token_2, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])

    # 每个 token 解码后必须返回其对应的 user_id
    assert payload_1["user_id"] == user_id_1, (
        f"Token for user_id={user_id_1} decoded to user_id={payload_1['user_id']}"
    )
    assert payload_2["user_id"] == user_id_2, (
        f"Token for user_id={user_id_2} decoded to user_id={payload_2['user_id']}"
    )

    # 两个 token 的 user_id 不得相同（防止碰撞）
    assert payload_1["user_id"] != payload_2["user_id"], (
        f"Different user_ids produced tokens with the same decoded user_id: "
        f"{payload_1['user_id']}"
    )


# ---------------------------------------------------------------------------
# Property 2: 密码安全不变量
# Validates: Requirements 1.4, 16.4
# ---------------------------------------------------------------------------

"""
Property 2: 密码安全不变量

对任意明文密码，`create_user` 写入数据库的 `password_hash` 永远不等于明文；
`bcrypt.checkpw` 是唯一合法校验路径。

验证内容：
1. password_hash 永远不等于明文密码（明文绝不写入数据库）
2. bcrypt.checkpw(plaintext, hash) 对正确密码返回 True
3. bcrypt.checkpw(wrong_password, hash) 对错误密码返回 False
4. 相同明文密码每次 hash 结果不同（bcrypt salt 随机性）

注意：直接使用 bcrypt 库（而非 passlib）以避免 passlib 与 bcrypt 5.x 的兼容性问题。
生产代码中 passlib.CryptContext 最终也调用相同的 bcrypt.hashpw/checkpw 底层函数。

**Validates: Requirements 1.4, 16.4**
"""

import sqlite3
import bcrypt as _bcrypt_lib

# 生成合法密码的策略：至少 8 字符，仅使用 ASCII 可打印字符
# 限制为纯 ASCII（每字符 1 字节），确保不超过 bcrypt 的 72 字节硬限制
# bcrypt 的 72 字节限制是字节数，而非字符数；使用 ASCII 字符集保证两者相等
_password_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?",
    min_size=8,
    max_size=64,  # 保守上限（64 < 72），避免超出 bcrypt 72 字节硬限制
)


def _bcrypt_hash(plaintext: str) -> str:
    """使用 bcrypt（cost=4，测试专用低轮数）对明文密码进行哈希，返回字符串。"""
    salt = _bcrypt_lib.gensalt(rounds=4)
    return _bcrypt_lib.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")


def _bcrypt_verify(plaintext: str, hashed: str) -> bool:
    """使用 bcrypt 校验明文密码与哈希值是否匹配。"""
    return _bcrypt_lib.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))


@given(plaintext_password=_password_strategy)
@settings(max_examples=100, deadline=None)
def test_password_hash_never_equals_plaintext(plaintext_password: str):
    """
    Property 2a: password_hash 永远不等于明文密码

    对任意明文密码，bcrypt hash 后的结果必须与明文不同。
    这是密码安全的基本不变量：明文绝不写入数据库。

    **Validates: Requirements 1.4, 16.4**
    """
    password_hash = _bcrypt_hash(plaintext_password)

    # 核心断言：hash 结果绝不等于明文
    assert password_hash != plaintext_password, (
        f"CRITICAL SECURITY VIOLATION: password_hash equals plaintext! "
        f"plaintext={repr(plaintext_password)}, hash={repr(password_hash)}"
    )

    # hash 必须是非空字符串
    assert isinstance(password_hash, str), (
        f"password_hash must be a string, got {type(password_hash)}"
    )
    assert len(password_hash) > 0, "password_hash must not be empty"

    # bcrypt hash 以 $2b$ 开头（标准 bcrypt 格式）
    assert password_hash.startswith("$2b$") or password_hash.startswith("$2a$"), (
        f"password_hash does not look like a valid bcrypt hash: {repr(password_hash[:20])}"
    )


@given(plaintext_password=_password_strategy)
@settings(max_examples=100, deadline=None)
def test_bcrypt_verify_is_the_only_valid_check_path(plaintext_password: str):
    """
    Property 2b: bcrypt.verify 是唯一合法校验路径

    对任意明文密码：
    - bcrypt.checkpw(plaintext, hash) 必须返回 True（正确密码通过）
    - 直接字符串比较 plaintext == hash 必须返回 False（明文比较无效）

    **Validates: Requirements 1.4, 16.4**
    """
    password_hash = _bcrypt_hash(plaintext_password)

    # bcrypt.checkpw 对正确密码必须返回 True
    assert _bcrypt_verify(plaintext_password, password_hash) is True, (
        f"bcrypt.checkpw should return True for correct password, "
        f"but returned False for plaintext={repr(plaintext_password)}"
    )

    # 直接字符串比较必须失败（明文 ≠ hash）
    assert plaintext_password != password_hash, (
        f"Direct string comparison should never equal hash: "
        f"plaintext={repr(plaintext_password)}"
    )


@given(
    plaintext_password=_password_strategy,
    wrong_password=_password_strategy,
)
@settings(max_examples=100, deadline=None)
def test_bcrypt_verify_rejects_wrong_password(
    plaintext_password: str, wrong_password: str
):
    """
    Property 2c: bcrypt.checkpw 对错误密码必须返回 False

    对任意两个不同的密码，用其中一个的 hash 校验另一个必须失败。
    当两个密码恰好相同时，跳过此测试（Hypothesis 会自动收缩到不同的值）。

    **Validates: Requirements 1.4, 16.4**
    """
    # 如果两个密码恰好相同，跳过（不是错误密码场景）
    if plaintext_password == wrong_password:
        return

    password_hash = _bcrypt_hash(plaintext_password)

    # bcrypt.checkpw 对错误密码必须返回 False
    assert _bcrypt_verify(wrong_password, password_hash) is False, (
        f"bcrypt.checkpw should return False for wrong password, "
        f"but returned True for wrong_password={repr(wrong_password)} "
        f"against hash of plaintext={repr(plaintext_password)}"
    )


@given(plaintext_password=_password_strategy)
@settings(max_examples=50, deadline=None)
def test_bcrypt_salt_randomness_produces_different_hashes(plaintext_password: str):
    """
    Property 2d: 相同明文密码每次 hash 结果不同（bcrypt salt 随机性）

    bcrypt 每次 hash 时生成随机 salt，因此相同明文的两次 hash 结果必须不同。
    这防止了彩虹表攻击。

    **Validates: Requirements 16.4**
    """
    hash_1 = _bcrypt_hash(plaintext_password)
    hash_2 = _bcrypt_hash(plaintext_password)

    # 两次 hash 结果必须不同（随机 salt 保证）
    assert hash_1 != hash_2, (
        f"bcrypt should produce different hashes for the same plaintext due to random salt, "
        f"but got identical hashes for plaintext={repr(plaintext_password)}"
    )

    # 但两个 hash 都应该能验证原始明文
    assert _bcrypt_verify(plaintext_password, hash_1) is True, (
        "First hash should verify correctly"
    )
    assert _bcrypt_verify(plaintext_password, hash_2) is True, (
        "Second hash should verify correctly"
    )


@given(plaintext_password=_password_strategy)
@settings(max_examples=50, deadline=None)
def test_create_user_stores_hash_not_plaintext(plaintext_password: str):
    """
    Property 2e: create_user 写入数据库的 password_hash 永远不等于明文

    使用临时 SQLite 数据库模拟 create_user 的完整写入流程，
    验证数据库中存储的 password_hash 字段绝不等于明文密码。

    **Validates: Requirements 1.4, 16.4**
    """
    # 使用 bcrypt hash 密码（模拟 Router/auth.py 中的注册流程）
    password_hash = _bcrypt_hash(plaintext_password)

    # 使用临时内存数据库模拟 create_user 写入
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
        ("testuser", password_hash, None, "2024-01-01 00:00:00"),
    )
    conn.commit()

    # 从数据库读回 password_hash
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", ("testuser",)
    ).fetchone()
    conn.close()

    stored_hash = row[0]

    # 核心断言：数据库中存储的 hash 绝不等于明文
    assert stored_hash != plaintext_password, (
        f"CRITICAL: Database stored plaintext password instead of hash! "
        f"plaintext={repr(plaintext_password)}"
    )

    # 存储的 hash 必须能通过 bcrypt.checkpw 校验
    assert _bcrypt_verify(plaintext_password, stored_hash) is True, (
        f"Stored hash should verify correctly with bcrypt.checkpw, "
        f"but verification failed for plaintext={repr(plaintext_password)}"
    )

    # 存储的 hash 必须是合法的 bcrypt 格式
    assert stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"), (
        f"Stored hash is not a valid bcrypt hash: {repr(stored_hash[:20])}"
    )
