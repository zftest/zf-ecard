"""数据模型（SQLAlchemy 2.0 类型化声明式写法）。

MVP 共 7 张表：

    books              教材册别（人教版 2024 七年级上册 / 下册）
    units              单元（含 Starter Unit）
    words              词条（拼写唯一，绑定主单元）
    word_senses        义项（一个词多个意思；accepted 存人工维护的同义写法）
    practice_sessions  一次默写会话
    practice_items     会话内的每道题（含题面/答案快照）
    skill_progress     按「义项 × 技能」记录掌握度、盒子等级、下次复习时间

三个刻意的设计取舍，避免以后返工：

1. **判题绑定 sense_id，不绑定单词拼写。**
   「experience」的「经历」和「经验」是两个义项，错词本必须分开记账，
   否则孩子答对「经验」会被当成也掌握了「经历」。

2. **skill_progress 里带 learner_key，默认 'default'。**
   MVP 不做账号体系，但「每个学习者的掌握度」这一维将来一定要加到唯一键里。
   唯一键的变更（(word,sense) -> (learner,word,sense)）是代价最大的那类迁移，
   现在多一列，将来省一次数据搬迁。

3. **错词本是 skill_progress 的查询视图，不是第 8 张表。**
   如果错词单独存一张表，「下次复习时间」就会有两个写入点，
   迟早出现「错词本说今天复习、练习页说不用练」的矛盾。
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> dt.datetime:
    """统一取 UTC 时间（带时区）。

    全库只用一个时区，避免 naive/aware 混用导致「下次复习时间差 8 小时」。
    展示层再转本地时区。
    """
    return dt.datetime.now(dt.timezone.utc)


class UTCDateTime(TypeDecorator):
    """始终按 UTC 存取的时间类型，读出来一定带时区。

    为什么需要它：
        SQLite 的 DATETIME 列**不保存时区**。直接存一个 aware datetime，
        读回来是 naive 的 —— tzinfo 被静默丢弃。之后一旦拿它和
        datetime.now(timezone.utc) 比较，要么抛 TypeError，
        要么被当成两个相差 8 小时的不同时间，而且全程不报错。

    做法：
        写入时统一转成 UTC 的 naive 值存盘；
        读出时补回 UTC 时区标记。
        这样应用层永远拿到 aware datetime，不必到处写 if tzinfo is None。
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)


class Base(DeclarativeBase):
    """所有模型的基类。"""


# ─────────────────────────────────────────────────────────────
# 维度表：教材 / 单元
# ─────────────────────────────────────────────────────────────


class Book(Base):
    """教材册别，例如「人教版 2024 七年级上册」。"""

    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint(
            "publisher", "edition", "grade", "term", name="uq_book_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    publisher: Mapped[str] = mapped_column(String(32), nullable=False)  # 人教版
    edition: Mapped[str] = mapped_column(String(16), nullable=False)  # 2024
    grade: Mapped[str] = mapped_column(String(16), nullable=False)  # 七年级
    term: Mapped[str] = mapped_column(String(8), nullable=False)  # 上册 / 下册
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )

    units: Mapped[list["Unit"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Unit.sort_order",
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Book {self.publisher}-{self.edition} {self.grade}{self.term}>"


class Unit(Base):
    """教材单元。Starter Unit 用 is_starter 区分，unit_no 记 0。"""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("book_id", "unit_code", name="uq_unit_code_per_book"),
        Index("ix_units_book_order", "book_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    # 稳定标识，不随显示名变化：SU01 / U01
    unit_code: Mapped[str] = mapped_column(String(8), nullable=False)
    unit_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unit_name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 计划词数。留空表示「由实际词条数统计」，避免写死一个猜的数字
    word_count_planned: Mapped[int | None] = mapped_column(Integer, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="units")
    words: Mapped[list["Word"]] = relationship(back_populates="unit")

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Unit {self.unit_code} {self.unit_name}>"


# ─────────────────────────────────────────────────────────────
# 词库
# ─────────────────────────────────────────────────────────────


class Word(Base):
    """词条。

    唯一键是 (spelling, pos)：一个单词在同一册里只出现一次，
    unit_id 记「首次出现单元」。跨单元复现做成了将来的 word_units 关联表，
    MVP 不做 —— 因为按单元抽题时，重复词会导致同一词被抽中两次。
    """

    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("spelling", "pos", name="uq_word_spelling_pos"),
        Index("ix_words_unit", "unit_id"),
        Index("ix_words_theme", "theme"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    spelling: Mapped[str] = mapped_column(String(64), nullable=False)
    pos: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    phonetic_uk: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phonetic_us: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )
    theme: Mapped[str | None] = mapped_column(String(32), nullable=True)
    frequency_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 数据来源与许可，用于合规追溯（见 docs/word-source-and-pronunciation-plan.md）
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="PEP2024")
    source_license: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # pending / verified —— 未人工核对的词条不得用于正式练习
    verify_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )

    unit: Mapped["Unit | None"] = relationship(back_populates="words")
    senses: Mapped[list["WordSense"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        order_by="WordSense.sense_order",
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Word {self.spelling}>"


class WordSense(Base):
    """义项。

    accepted 存「除了 meaning_zh 之外还能算对的写法」，由人工维护，
    例：meaning_zh='环境'，accepted=['自然环境', '生态环境']。
    有了它，「经历/阅历」这类判错可以靠配置解决，而不用改判题代码。
    """

    __tablename__ = "word_senses"
    __table_args__ = (
        UniqueConstraint("word_id", "sense_order", name="uq_sense_order_per_word"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    sense_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    meaning_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    pos: Mapped[str | None] = mapped_column(String(16), nullable=True)
    accepted: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    example_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_zh: Mapped[str | None] = mapped_column(Text, nullable=True)

    word: Mapped["Word"] = relationship(back_populates="senses")

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<WordSense {self.meaning_zh}>"


# ─────────────────────────────────────────────────────────────
# 练习
# ─────────────────────────────────────────────────────────────


class PracticeSession(Base):
    """一次默写会话。

    不在会话表里存正确率等汇总字段：汇总一律从 practice_items 聚合，
    避免「会话表和题目表各说一套」的对账问题。
    """

    __tablename__ = "practice_sessions"
    __table_args__ = (
        Index("ix_sessions_learner_started", "learner_key", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_key: Mapped[str] = mapped_column(
        String(32), nullable=False, default="default"
    )
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    range_type: Mapped[str] = mapped_column(String(16), nullable=False)  # unit/theme/wrongbook
    range_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    order_strategy: Mapped[str] = mapped_column(
        String(16), nullable=False, default="random"
    )
    hint_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="running"
    )  # running / finished / abandoned

    items: Mapped[list["PracticeItem"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PracticeItem.seq",
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<PracticeSession {self.id} {self.mode} {self.status}>"


class PracticeItem(Base):
    """会话内的一道题。

    prompt / expected / accepted 三个字段都是**出题时的快照**：
    词库后续被修正（比如把一个错误释义改掉），历史成绩仍然按当时的题面算，
    否则「昨天的 100 分」会随着词库修订被悄悄改写。
    """

    __tablename__ = "practice_items"
    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_item_seq_per_session"),
        Index("ix_items_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="RESTRICT"), nullable=False
    )
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("word_senses.id", ondelete="RESTRICT"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(24), nullable=False)

    prompt_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    expected_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_snapshot: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    first_try_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answered_at: Mapped[dt.datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )

    session: Mapped["PracticeSession"] = relationship(back_populates="items")

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<PracticeItem seq={self.seq} correct={self.is_correct}>"


# ─────────────────────────────────────────────────────────────
# 掌握度（同时充当错词本数据源）
# ─────────────────────────────────────────────────────────────


class SkillProgress(Base):
    """按「义项 × 技能」记录掌握度。

    技能维度与题型对应：
        spelling            ← 汉译英（给中文，写英文）
        listening_spelling  ← 听音写词
        meaning_recall      ← 英译汉（给英文，写中文）
        phonetic_spelling   ← 音标写词

    一个词的「拼写」会了不代表「听音」会了，所以必须分技能记账；
    合成一个总分会让「听音写词」永远被拼写成绩掩盖。

    错词本 = 本表 wrong_count > 0 且 status='active' 的行，按 due_at 排序。
    """

    __tablename__ = "skill_progress"
    __table_args__ = (
        UniqueConstraint(
            "learner_key", "word_id", "sense_id", "skill", name="uq_progress_key"
        ),
        Index("ix_progress_due", "learner_key", "status", "due_at"),
        CheckConstraint("box_level BETWEEN 1 AND 5", name="ck_progress_box_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_key: Mapped[str] = mapped_column(
        String(32), nullable=False, default="default"
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("word_senses.id", ondelete="CASCADE"), nullable=False
    )
    skill: Mapped[str] = mapped_column(String(24), nullable=False)

    box_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    due_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_seen_at: Mapped[dt.datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    # active / mastered / ignored —— ignored 供家长手动把「人名/生僻词」踢出错词本
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active"
    )

    word: Mapped["Word"] = relationship()
    sense: Mapped["WordSense"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<SkillProgress word={self.word_id} {self.skill} box={self.box_level}>"
